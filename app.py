from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import os
import sys
import re
import smtplib
from datetime import datetime

try:
    from config.config import OPENAI_API_KEY
except ImportError:
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not found. Please set it in config/config.py or as an environment variable.")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

FORM_STEPS = [
    {'id': 'company_name', 'label': 'Company Name', 'completed': False},
    {'id': 'language', 'label': 'Language', 'completed': False},
    {'id': 'sphere', 'label': 'Business Sphere', 'completed': False},
    {'id': 'education', 'label': 'Education', 'completed': False},
    {'id': 'experience', 'label': 'Experience', 'completed': False},
    {'id': 'location', 'label': 'Location', 'completed': False},
]


def slugify(text):
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    text = text.strip('_')
    return text


def load_business_plan_from_yaml():
    yaml_path = os.path.join(os.path.dirname(__file__), 'config', 'improved_business_plan.yaml')
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    sections = []
    current_section = None
    current_questions = []
    is_optional = False
    
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        if line == '# ---':
            i += 1
            if i < len(lines):
                next_line = lines[i].strip()
                if next_line.startswith('# Section'):
                    if current_section:
                        sections.append(current_section)
                    
                    title_match = re.search(r'Section (\d+):\s*(.+)', next_line)
                    if title_match:
                        section_num = title_match.group(1)
                        section_title = title_match.group(2).strip()
                        
                        i += 1
                        if i < len(lines) and lines[i].strip() == '# ---':
                            i += 1
                        
                        description = ""
                        if i < len(lines):
                            desc_line = lines[i].strip()
                            if desc_line.startswith('#') and not desc_line.startswith('# ---'):
                                description = desc_line.lstrip('#').strip()
                        
                        current_section = {
                            'id': f'section_{section_num}',
                            'title': f'Section {section_num}: {section_title}',
                            'description': description,
                            'core_questions': [],
                            'optional_questions': []
                        }
                        current_questions = current_section['core_questions']
                        is_optional = False
        
        elif line == '# --- Core Questions ---':
            current_questions = current_section['core_questions'] if current_section else []
            is_optional = False
        
        elif line == '# --- Optional Deeper Dive ---':
            current_questions = current_section['optional_questions'] if current_section else []
            is_optional = True
        
        elif line and not line.startswith('#') and ':' in line:
            question_match = re.match(r'"([^"]+)":', line)
            if question_match:
                question_label = question_match.group(1)
                question_id = slugify(question_label)
                
                i += 1
                fill_text = ""
                while i < len(lines):
                    next_line = lines[i].strip()
                    if not next_line or next_line.startswith('#'):
                        if next_line.startswith('# ---'):
                            i -= 1
                            break
                        i += 1
                        continue
                    
                    if next_line.startswith('fill:'):
                        fill_text = next_line.replace('fill:', '').strip()
                        if fill_text.startswith('"') and fill_text.endswith('"'):
                            fill_text = fill_text[1:-1]
                        elif fill_text.startswith('"'):
                            fill_text = fill_text[1:]
                            i += 1
                            while i < len(lines):
                                cont_line = lines[i].strip()
                                if cont_line.endswith('"'):
                                    fill_text += ' ' + cont_line[:-1]
                                    break
                                fill_text += ' ' + cont_line
                                i += 1
                    elif next_line.startswith('why:') or next_line.startswith('answer:'):
                        break
                    i += 1
                
                if current_section and fill_text:
                    question = {
                        'id': question_id,
                        'label': question_label,
                        'fill': fill_text
                    }
                    current_questions.append(question)
        
        i += 1
    
    if current_section:
        sections.append(current_section)
    
    return sections


BUSINESS_PLAN_SECTIONS = load_business_plan_from_yaml()

form_data = {}
chat_history = []
question_retries = {}

TIERS = [
    {'id': 'beginner', 'name': 'Beginner', 'points_required': 0, 'icon': '🌱'},
    {'id': 'motivated_entrepreneur', 'name': 'Motivated Entrepreneur', 'points_required': 3, 'icon': '🚀'},
    {'id': 'growing_entrepreneur', 'name': 'Growing Entrepreneur', 'points_required': 6, 'icon': '🌟'},
    {'id': 'experienced_business_professional', 'name': 'Experienced Business Professional', 'points_required': 10, 'icon': '💼'},
    {'id': 'master_entrepreneur', 'name': 'Master Entrepreneur', 'points_required': 20, 'icon': '👑'}
]


def calculate_points(form_data):
    points = 0
    
    if form_data.get('company_name') and form_data.get('company_name') != '':
        points += 1
    if form_data.get('language') and form_data.get('language') != '':
        points += 1
    if form_data.get('sphere') and form_data.get('sphere') != '':
        points += 1
    if form_data.get('education') and form_data.get('education') != '':
        points += 1
    if form_data.get('experience') and form_data.get('experience') != '':
        points += 1
    if form_data.get('location') and form_data.get('location') != '':
        points += 1
    
    for section in BUSINESS_PLAN_SECTIONS:
        for question in section['core_questions']:
            question_value = form_data.get(question['id'])
            if question_value and question_value != '':
                points += 3
        for question in section['optional_questions']:
            question_value = form_data.get(question['id'])
            if question_value and question_value != '':
                points += 5
    
    return points


def get_current_tier(points):
    current_tier = TIERS[0]
    for tier in reversed(TIERS):
        if points >= tier['points_required']:
            current_tier = tier
            break
    return current_tier


def is_initial_form_complete(form_data):
    return all(form_data.get(step['id']) and form_data.get(step['id']) != '' for step in FORM_STEPS)


def get_current_business_plan_question(form_data):
    for section in BUSINESS_PLAN_SECTIONS:
        for question in section['core_questions']:
            question_value = form_data.get(question['id'])
            if question_value is None:
                return section, question, 'core'
        for question in section['optional_questions']:
            question_value = form_data.get(question['id'])
            if question_value is None:
                return section, question, 'optional'
    return None, None, None


def get_business_plan_progress(form_data):
    progress = []
    
    preliminary_progress = {
        'section_id': 'section_0',
        'title': 'Section 0: Basic Information',
        'description': 'Your company and background details',
        'core_completed': [],
        'core_total': len(FORM_STEPS),
        'optional_completed': [],
        'optional_total': 0,
        'core_questions': [],
        'optional_questions': [],
        'core_skipped': [],
        'optional_skipped': []
    }
    for step in FORM_STEPS:
        step_value = form_data.get(step['id'])
        if step_value and step_value != '':
            preliminary_progress['core_completed'].append(step['id'])
    progress.append(preliminary_progress)
    
    for section in BUSINESS_PLAN_SECTIONS:
        section_progress = {
            'section_id': section['id'],
            'title': section['title'],
            'description': section['description'],
            'core_completed': [],
            'core_total': len(section['core_questions']),
            'optional_completed': [],
            'optional_total': len(section['optional_questions']),
            'core_questions': section['core_questions'],
            'optional_questions': section['optional_questions'],
            'core_skipped': [],
            'optional_skipped': []
        }
        for question in section['core_questions']:
            question_value = form_data.get(question['id'])
            if question_value == '':
                section_progress['core_skipped'].append(question['id'])
            elif question_value and question_value != '':
                section_progress['core_completed'].append(question['id'])
        for question in section['optional_questions']:
            question_value = form_data.get(question['id'])
            if question_value == '':
                section_progress['optional_skipped'].append(question['id'])
            elif question_value and question_value != '':
                section_progress['optional_completed'].append(question['id'])
        progress.append(section_progress)
    return progress


def validate_answer(user_message, current_step, question_info=None):
    if not question_info:
        return True
    
    user_message_clean = user_message.strip()
    
    if len(user_message_clean) < 2:
        return False
    
    if user_message_clean.isdigit() and len(user_message_clean) > 3:
        return False
    
    if user_message_clean.replace(' ', '').isdigit() and len(user_message_clean.replace(' ', '')) > 3:
        return False
    
    if len(set(user_message_clean.replace(' ', ''))) < 3 and len(user_message_clean) > 5:
        return False
    
    question_label = question_info.get('label', '')
    question_fill = question_info.get('fill', '')
    
    validation_prompt = f"""You are validating if a user's answer appropriately addresses a business plan question.

Question: "{question_label}"
Question context: {question_fill}

User's answer: "{user_message}"

Determine if the user's answer:
1. Actually addresses the question being asked
2. Provides meaningful information relevant to the question
3. Is not just random numbers, gibberish, or meaningless text
4. Is not just a generic response, question, or unrelated comment
5. Contains actual words or meaningful content (not just digits or symbols)

Examples of INVALID answers:
- Random numbers like "5645646" or "123456"
- Gibberish like "asdfgh" or "qwerty"
- Single words that don't answer the question
- Unrelated comments or questions

Respond with ONLY "YES" if the answer is appropriate and addresses the question, or "NO" if it does not address the question properly or is nonsensical."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {'role': 'system', 'content': validation_prompt},
                {'role': 'user', 'content': 'Validate this answer.'}
            ],
            temperature=0.3,
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip().upper()
        return result.startswith('YES')
    except Exception as e:
        print(f"Validation error: {str(e)}")
        return True


def get_step_prompt(current_step, form_data, is_retry=False, is_skipping=False):
    if current_step and current_step.startswith('bp_'):
        section, question, question_type = get_current_business_plan_question(form_data)
        if section and question:
            context_parts = []
            if form_data.get('company_name'):
                context_parts.append(f"Company: {form_data['company_name']}")
            if form_data.get('sphere'):
                context_parts.append(f"Business Sphere: {form_data['sphere']}")
            
            context = f"Context: {', '.join(context_parts)}. " if context_parts else ""
            
            section_info = f"We're working on {section['title']} - {section['description']}."
            question_instruction = f"Ask about: {question['label']}. {question['fill']}"
            
            if question_type == 'optional':
                question_instruction += " (This is an optional deeper dive question - they can skip if they prefer.)"
            
            retry_note = ""
            if is_retry:
                retry_note = " The user's previous answer didn't seem to address the question properly or was unclear (it might have been random numbers, gibberish, or unrelated text). Please politely let them know you didn't understand their answer and ask the same question again. Be encouraging and supportive. If they don't answer properly this time, we'll move on to the next question."
            elif is_skipping:
                retry_note = " The user didn't provide a clear answer to the previous question after two attempts, so we're moving on. Please ask the next question naturally and encouragingly."
            
            return f"""You are a friendly business advisor assistant helping create a comprehensive business plan. {context}
{section_info}
Now ask them: "{question['label']}" - {question['fill']}{retry_note}
Keep responses concise (1-2 sentences) and conversational. Be encouraging and supportive. Make sure to actually ask the question directly."""
        else:
            return """You are a friendly business advisor assistant. All business plan questions have been completed.
Thank them for their thorough responses and let them know their business plan information has been collected."""
    
    step_descriptions = {
        'company_name': "Ask for the company name. Be friendly and welcoming.",
        'language': "Ask for the preferred language (e.g., English, Spanish, French, German).",
        'sphere': "Ask what industry or business sphere the company operates in.",
        'education': "Ask about the educational background (e.g., Bachelor's in Business, MBA, etc.).",
        'experience': "Ask how many years of business experience they have.",
        'location': "Ask where the business is located."
    }
    
    collected_info = []
    if form_data.get('company_name'):
        collected_info.append(f"Company Name: {form_data['company_name']}")
    if form_data.get('language'):
        collected_info.append(f"Language: {form_data['language']}")
    if form_data.get('sphere'):
        collected_info.append(f"Business Sphere: {form_data['sphere']}")
    if form_data.get('education'):
        collected_info.append(f"Education: {form_data['education']}")
    if form_data.get('experience'):
        collected_info.append(f"Experience: {form_data['experience']}")
    if form_data.get('location'):
        collected_info.append(f"Location: {form_data['location']}")
    
    context = ""
    if collected_info:
        context = f"Information collected so far: {', '.join(collected_info)}. "
    
    current_task = step_descriptions.get(current_step, "Continue the conversation naturally.")
    
    if current_step == 'location':
        section, question, _ = get_current_business_plan_question(form_data)
        if section and question:
            return f"""You are a friendly business form assistant helping to collect information. {context}
Current task: {current_task}
After collecting the location, congratulate them on completing the initial form. Then immediately ask them the first business plan question: "{question['label']}". {question['fill']}
Keep responses concise (1-2 sentences) and conversational."""
        else:
            return f"""You are a friendly business form assistant helping to collect information. {context}
Current task: {current_task}
After collecting the location, congratulate them on completing the initial form and introduce the business plan checklist.
Keep responses concise (1-2 sentences) and conversational."""
    elif current_step == 'complete':
        if not form_data.get('email'):
            return f"""You are a friendly business form assistant. All required information has been collected:
{', '.join(collected_info)}
Now, please ask for their email address so we can send them a summary report of the information they provided.
Keep responses concise and conversational."""
        else:
            return f"""You are a friendly business form assistant. All information including email has been collected.
Thank them for completing the form and let them know that a report will be sent to their email address shortly.
Keep responses concise and conversational."""
    else:
        next_steps = []
        for step in FORM_STEPS:
            if step['id'] == current_step:
                idx = FORM_STEPS.index(step)
                if idx + 1 < len(FORM_STEPS):
                    next_steps.append(step_descriptions[FORM_STEPS[idx + 1]['id']])
                break
        
        next_hint = (f" After collecting this information, you'll ask about:"
                     f" {next_steps[0] if next_steps else 'completion'}.") if next_steps else ""
        
        retry_note_initial = ""
        if is_retry:
            retry_note_initial = " The user's previous answer was unclear or didn't make sense (it might have been random numbers, gibberish, or unrelated text). Please politely let them know you didn't understand their answer and ask the same question again. Be encouraging and supportive."
        
        return f"""You are a friendly business form assistant helping to collect information. {context}
Current task: {current_task}{retry_note_initial}{next_hint}
Keep responses concise (1-2 sentences) and conversational. 
Acknowledge their input and naturally move to the next question."""


def get_openai_response(user_message, current_step, is_retry=False, is_skipping=False):
    global chat_history
    
    try:
        context_message = get_step_prompt(current_step, form_data, is_retry=is_retry, is_skipping=is_skipping)
        
        system_message = {
            'role': 'system',
            'content': context_message
        }
        
        messages = [system_message]
        
        if chat_history:
            messages.extend(chat_history[-10:])
        
        messages.append({
            'role': 'user',
            'content': user_message
        })
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=200
        )
        
        ai_message = response.choices[0].message.content.strip()
        
        chat_history.append({
            'role': 'user',
            'content': user_message
        })
        chat_history.append({
            'role': 'assistant',
            'content': ai_message
        })
        
        should_advance = False
        if current_step == 'company_name' and len(user_message.strip()) > 1:
            should_advance = True
        elif current_step == 'language' and len(user_message.strip()) > 1:
            should_advance = True
        elif current_step == 'sphere' and len(user_message.strip()) > 2:
            should_advance = True
        elif current_step == 'education' and len(user_message.strip()) > 2:
            should_advance = True
        elif current_step == 'experience' and len(user_message.strip()) > 0:
            should_advance = True
        elif current_step == 'location' and len(user_message.strip()) > 2:
            should_advance = True
        
        if should_advance and current_step != 'complete':
            next_step_idx = None
            for idx, step in enumerate(FORM_STEPS):
                if step['id'] == current_step:
                    if idx + 1 < len(FORM_STEPS):
                        next_step_idx = idx + 1
                    else:
                        next_step_idx = 'complete'
                    break
            
            if next_step_idx == 'complete':
                return {'message': ai_message, 'step': 'complete'}
            elif next_step_idx is not None:
                return {'message': ai_message, 'step': FORM_STEPS[next_step_idx]['id']}
        
        return {'message': ai_message, 'step': current_step}
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Chat API error: {error_details}")
        return {
            'message': f"I apologize, but I encountered an error. Please try again. Error: {str(e)}",
            'step': current_step
        }


@app.route('/')
def index():
    return render_template('index.html', steps=FORM_STEPS)


@app.route('/api/business-plan-structure', methods=['GET'])
def get_business_plan_structure():
    empty_form_data = {}
    business_plan_progress = get_business_plan_progress(empty_form_data)
    return jsonify({
        'business_plan_progress': business_plan_progress
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    global question_retries
    
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
        section, question, question_type = get_current_business_plan_question(form_data)
        if section and question:
            current_step = f"bp_{question['id']}"
            question_info = question
            
            if len(user_message.strip()) > 2:
                answer_valid = validate_answer(user_message, current_step, question_info)
                
                if answer_valid:
                    form_data[question['id']] = user_message
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
                        section, next_question, _ = get_current_business_plan_question(form_data)
                        if next_question:
                            current_step = f"bp_{next_question['id']}"
                            is_skipping = True
        else:
            current_step = 'bp_complete'
    
    if not form_data.get('email'):
        import re
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
    
    response = get_openai_response(user_message, current_step, is_retry=is_retry, is_skipping=is_skipping)
    
    completed_steps = []
    for step in FORM_STEPS:
        if form_data.get(step['id']):
            completed_steps.append(step['id'])
    
    business_plan_progress = get_business_plan_progress(form_data)
    
    email_collected = form_data.get('email') is not None
    report_sent = False
    
    if email_collected and initial_form_complete and not form_data.get('report_sent'):
        section, question, _ = get_current_business_plan_question(form_data)
        if not section:
            try:
                send_report_email(form_data)
                form_data['report_sent'] = True
                report_sent = True
            except Exception as e:
                print(f"Error sending email: {str(e)}")
    
    points = calculate_points(form_data)
    current_tier = get_current_tier(points)
    
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
        audio_response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        
        import base64
        audio_data = audio_response.read()
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
        audio_file.seek(0)
        file_content = audio_file.read()
        audio_file.seek(0)
        
        filename = audio_file.filename or 'audio.webm'
        content_type = audio_file.content_type or 'audio/webm'
        
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, file_content, content_type)
        )
        return jsonify({'text': transcription.text})
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Transcription error: {error_details}")
        return jsonify({'error': f'Transcription failed: {str(e)}'}), 500


def generate_report(form_data):
    report = f"""
BUSINESS INFORMATION FORM REPORT
{'=' * 50}

Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

COMPANY INFORMATION
{'-' * 50}
Company Name: {form_data.get('company_name', 'N/A')}
Business Sphere: {form_data.get('sphere', 'N/A')}
Location: {form_data.get('location', 'N/A')}

PERSONAL INFORMATION
{'-' * 50}
Preferred Language: {form_data.get('language', 'N/A')}
Education: {form_data.get('education', 'N/A')}
Experience: {form_data.get('experience', 'N/A')}

CONTACT INFORMATION
{'-' * 50}
Email: {form_data.get('email', 'N/A')}

{'=' * 50}

This report was generated automatically by Aino: Business Advisory Service 2.0.
Thank you for providing your information!
"""
    return report


def send_report_email(form_data):
    try:
        from config.config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, FROM_EMAIL
    except ImportError:
        SMTP_SERVER = os.environ.get('SMTP_SERVER', 'live.smtp.mailtrap.io')
        SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
        SMTP_USERNAME = os.environ.get('SMTP_USERNAME', 'api')
        SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
        FROM_EMAIL = os.environ.get('FROM_EMAIL', 'hello@ainoespoo.com')
    
    if not SMTP_PASSWORD:
        print("Warning: SMTP password not found. Report will not be sent.")
        return False
    
    sender = FROM_EMAIL
    receiver = form_data.get('email')
    
    if not receiver:
        return False
    
    report_text = generate_report(form_data)
    
    message = f"""\
Subject: Business Information Form Report
To: {receiver}
From: {sender}

{report_text}"""
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(sender, receiver, message)
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        raise


@app.route('/api/send-report', methods=['POST'])
def send_report_manual():
    data = request.json
    email = data.get('email', '').strip() if data else ''
    
    if not email:
        if form_data.get('email'):
            email = form_data['email']
        else:
            return jsonify({'error': 'Email address is required. Please provide your email first.'}), 400
    
    import re
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if not re.match(email_pattern, email):
        return jsonify({'error': 'Invalid email address format.'}), 400
    
    report_data = form_data.copy()
    report_data['email'] = email
    
    try:
        send_report_email(report_data)
        if not form_data.get('email'):
            form_data['email'] = email
        return jsonify({'success': True, 'message': 'Report sent successfully!'})
    except Exception as e:
        return jsonify({'error': f'Failed to send report: {str(e)}'}), 500


@app.route('/api/reset', methods=['POST'])
def reset():
    global form_data, chat_history, question_retries
    form_data = {}
    chat_history = []
    question_retries = {}
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
