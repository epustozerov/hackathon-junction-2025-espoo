from flask import render_template, request, jsonify, send_file
import re
import base64
import os
from constants import FORM_STEPS, TIERS
from models.state import form_data, chat_history, question_retries, business_plan_sections, reset_state
from services.business_plan_service import (
    is_initial_form_complete,
    get_current_business_plan_question,
    get_business_plan_progress,
    calculate_points,
    get_current_tier
)
from services.validation_service import validate_answer
from services.chat_service import get_openai_response, get_tts_audio, transcribe_audio
from services.email_service import send_report_email
from services.yaml_service import update_yaml_with_answer, get_yaml_path
from services.docx_service import create_docx_from_form_data


def register_routes(app):
    @app.route('/')
    def index():
        return render_template('index.html', steps=FORM_STEPS)

    @app.route('/api/business-plan-structure', methods=['GET'])
    def get_business_plan_structure():
        empty_form_data = {}
        business_plan_progress = get_business_plan_progress(empty_form_data, business_plan_sections)
        return jsonify({
            'business_plan_progress': business_plan_progress
        })

    @app.route('/api/chat', methods=['POST'])
    def chat():
        data = request.json
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        initial_form_complete = is_initial_form_complete(form_data)
        current_step = None
        answer_valid = True
        question_info = None
        is_retry = False
        is_skipping = False
        
        if not initial_form_complete:
            for step in FORM_STEPS:
                if not form_data.get(step['id']):
                    current_step = step['id']
                    break
            
            user_message_clean = user_message.strip()
            
            is_nonsensical = False
            if len(user_message_clean) > 3:
                if user_message_clean.isdigit() or user_message_clean.replace(' ', '').isdigit():
                    is_nonsensical = True
                elif len(set(user_message_clean.replace(' ', ''))) < 3 and len(user_message_clean) > 5:
                    is_nonsensical = True
            
            if is_nonsensical:
                is_retry = True
            elif current_step == 'company_name' and len(user_message_clean) > 1:
                form_data['company_name'] = user_message
            elif current_step == 'language':
                lang_map = {
                    'english': 'English',
                    'spanish': 'Spanish',
                    'french': 'French',
                    'german': 'German'
                }
                user_lower = user_message.lower()
                for key, value in lang_map.items():
                    if key in user_lower:
                        form_data['language'] = value
                        break
                if not form_data.get('language'):
                    form_data['language'] = user_message
            elif current_step == 'sphere' and len(user_message_clean) > 2:
                form_data['sphere'] = user_message
            elif current_step == 'education' and len(user_message_clean) > 2:
                form_data['education'] = user_message
            elif current_step == 'experience' and len(user_message_clean) > 0:
                form_data['experience'] = user_message
            elif current_step == 'location' and len(user_message_clean) > 2:
                form_data['location'] = user_message
        else:
            section, question, question_type = get_current_business_plan_question(form_data, business_plan_sections)
            if section and question:
                current_step = f"bp_{question['id']}"
                question_info = question
                
                if len(user_message.strip()) > 2:
                    answer_valid = validate_answer(user_message, current_step, question_info)
                    
                    if answer_valid:
                        form_data[question['id']] = user_message
                        yaml_path = get_yaml_path()
                        update_yaml_with_answer(yaml_path, question['label'], user_message)
                        if current_step in question_retries:
                            del question_retries[current_step]
                    else:
                        retry_count = question_retries.get(current_step, 0)
                        if retry_count < 1:
                            question_retries[current_step] = retry_count + 1
                            is_retry = True
                        else:
                            if current_step in question_retries:
                                del question_retries[current_step]
                            form_data[question['id']] = ''
                            section, next_question, _ = get_current_business_plan_question(form_data, business_plan_sections)
                            if next_question:
                                current_step = f"bp_{next_question['id']}"
                                is_skipping = True
            else:
                current_step = 'bp_complete'
        
        if not form_data.get('email'):
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_match = re.search(email_pattern, user_message)
            if email_match:
                form_data['email'] = email_match.group()
            elif '@' in user_message and len(user_message.strip()) > 5:
                potential_email = user_message.strip()
                if '.' in potential_email.split('@')[1] if '@' in potential_email else False:
                    form_data['email'] = potential_email
        
        if current_step is None:
            current_step = 'complete' if not initial_form_complete else 'bp_complete'
        
        response = get_openai_response(
            user_message, 
            current_step, 
            form_data, 
            chat_history, 
            business_plan_sections,
            is_retry=is_retry, 
            is_skipping=is_skipping
        )
        
        completed_steps = []
        for step in FORM_STEPS:
            if form_data.get(step['id']):
                completed_steps.append(step['id'])
        
        business_plan_progress = get_business_plan_progress(form_data, business_plan_sections)
        
        email_collected = form_data.get('email') is not None
        report_sent = False
        
        if email_collected and initial_form_complete and not form_data.get('report_sent'):
            section, question, _ = get_current_business_plan_question(form_data, business_plan_sections)
            if not section:
                try:
                    send_report_email(form_data, business_plan_sections)
                    form_data['report_sent'] = True
                    report_sent = True
                except Exception as e:
                    print(f"Error sending email: {str(e)}")
        
        points = calculate_points(form_data, business_plan_sections)
        current_tier = get_current_tier(points, TIERS)
        
        return jsonify({
            'response': response['message'],
            'completed_steps': completed_steps,
            'business_plan_progress': business_plan_progress,
            'initial_form_complete': initial_form_complete,
            'form_data': form_data.copy(),
            'email_collected': email_collected,
            'report_sent': report_sent,
            'points': points,
            'current_tier': current_tier['id'],
            'tiers': TIERS
        })

    @app.route('/api/tts', methods=['POST'])
    def text_to_speech():
        data = request.json
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        try:
            audio_data = get_tts_audio(text)
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            return jsonify({
                'audio': audio_base64,
                'format': 'mp3'
            })
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"TTS error: {error_details}")
            return jsonify({'error': f'TTS failed: {str(e)}'}), 500

    @app.route('/api/transcribe', methods=['POST'])
    def transcribe():
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'No audio file selected'}), 400
        
        try:
            transcription = transcribe_audio(audio_file)
            return jsonify({'text': transcription})
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Transcription error: {error_details}")
            return jsonify({'error': f'Transcription failed: {str(e)}'}), 500

    @app.route('/api/send-report', methods=['POST'])
    def send_report_manual():
        data = request.json
        email = data.get('email', '').strip() if data else ''
        
        if not email:
            if form_data.get('email'):
                email = form_data['email']
            else:
                return jsonify({'error': 'Email address is required. Please provide your email first.'}), 400
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if not re.match(email_pattern, email):
            return jsonify({'error': 'Invalid email address format.'}), 400
        
        report_data = form_data.copy()
        report_data['email'] = email
        
        try:
            send_report_email(report_data, business_plan_sections)
            if not form_data.get('email'):
                form_data['email'] = email
            return jsonify({'success': True, 'message': 'Report sent successfully!'})
        except Exception as e:
            return jsonify({'error': f'Failed to send report: {str(e)}'}), 500

    @app.route('/api/download-report', methods=['GET'])
    def download_report():
        docx_path = None
        try:
            print(f"DEBUG ROUTE: form_data id: {id(form_data)}, type: {type(form_data)}")
            print(f"DEBUG ROUTE: form_data contents: {form_data}")
            print(f"DEBUG ROUTE: form_data keys: {list(form_data.keys())}")
            docx_path = create_docx_from_form_data(form_data, business_plan_sections)
            
            if docx_path and os.path.exists(docx_path):
                def remove_file():
                    try:
                        if docx_path and os.path.exists(docx_path):
                            os.remove(docx_path)
                    except Exception as e:
                        print(f"Error removing temporary DOCX file: {str(e)}")
                
                response = send_file(
                    docx_path,
                    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    as_attachment=True,
                    download_name='business_plan.docx'
                )
                
                try:
                    if hasattr(response, 'call_on_close'):
                        response.call_on_close(remove_file)
                except:
                    import threading
                    threading.Timer(30.0, remove_file).start()
                
                return response
            else:
                return jsonify({'error': 'Failed to generate document'}), 500
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Document download error: {error_details}")
            if docx_path and os.path.exists(docx_path):
                try:
                    os.remove(docx_path)
                except:
                    pass
            return jsonify({'error': f'Failed to generate document: {str(e)}'}), 500

    @app.route('/api/reset', methods=['POST'])
    def reset():
        reset_state()
        return jsonify({'success': True})

