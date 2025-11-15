from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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

form_data = {}


def get_step_prompt(current_step, form_data):
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
        return f"""You are a friendly business form assistant helping to collect information. {context}
Current task: {current_task}
After collecting the location, thank them for completing the form and ask if there's anything else they'd like to add.
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
        
        return f"""You are a friendly business form assistant helping to collect information. {context}
Current task: {current_task}{next_hint}
Keep responses concise (1-2 sentences) and conversational. 
Acknowledge their input and naturally move to the next question."""


def get_openai_response(user_message, current_step):
    try:
        system_prompt = get_step_prompt(current_step, form_data)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=150
        )
        
        ai_message = response.choices[0].message.content.strip()
        
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
        return {
            'message': f"I apologize, but I encountered an error. Please try again. Error: {str(e)}",
            'step': current_step
        }


@app.route('/')
def index():
    return render_template('index.html', steps=FORM_STEPS)


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
    
    current_step = None
    for step in FORM_STEPS:
        if not form_data.get(step['id']):
            current_step = step['id']
            break
    
    all_steps_completed = all(form_data.get(step['id']) for step in FORM_STEPS)
    
    if current_step == 'company_name' and len(user_message.strip()) > 1:
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
    elif current_step == 'sphere' and len(user_message.strip()) > 2:
        form_data['sphere'] = user_message
    elif current_step == 'education' and len(user_message.strip()) > 2:
        form_data['education'] = user_message
    elif current_step == 'experience' and len(user_message.strip()) > 0:
        form_data['experience'] = user_message
    elif current_step == 'location' and len(user_message.strip()) > 2:
        form_data['location'] = user_message
    
    if all_steps_completed and not form_data.get('email'):
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, user_message)
        if email_match:
            form_data['email'] = email_match.group()
        elif '@' in user_message and len(user_message.strip()) > 5:
            form_data['email'] = user_message.strip()
    
    if current_step is None:
        current_step = 'complete'
    
    response = get_openai_response(user_message, current_step)
    
    completed_steps = []
    for step in FORM_STEPS:
        if form_data.get(step['id']):
            completed_steps.append(step['id'])
    
    email_collected = form_data.get('email') is not None
    report_sent = False
    
    if email_collected and all_steps_completed and not form_data.get('report_sent'):
        try:
            send_report_email(form_data)
            form_data['report_sent'] = True
            report_sent = True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
    
    return jsonify({
        'response': response['message'],
        'completed_steps': completed_steps,
        'form_data': form_data.copy(),
        'email_collected': email_collected,
        'report_sent': report_sent
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

This report was generated automatically by the Business Form Assistant.
Thank you for providing your information!
"""
    return report


def send_report_email(form_data):
    try:
        email_config = {}
        try:
            from config.config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, FROM_EMAIL
            email_config = {
                'server': SMTP_SERVER,
                'port': SMTP_PORT,
                'username': SMTP_USERNAME,
                'password': SMTP_PASSWORD,
                'from_email': FROM_EMAIL
            }
        except ImportError:
            email_config = {
                'server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
                'port': int(os.environ.get('SMTP_PORT', '587')),
                'username': os.environ.get('SMTP_USERNAME', ''),
                'password': os.environ.get('SMTP_PASSWORD', ''),
                'from_email': os.environ.get('FROM_EMAIL', 'noreply@example.com')
            }
        
        if not email_config['username'] or not email_config['password']:
            print("Warning: Email configuration not found. Report will not be sent.")
            return False
        
        to_email = form_data.get('email')
        if not to_email:
            return False
        
        report_text = generate_report(form_data)
        
        msg = MIMEMultipart()
        msg['From'] = email_config['from_email']
        msg['To'] = to_email
        msg['Subject'] = 'Business Information Form Report'
        
        msg.attach(MIMEText(report_text, 'plain'))
        
        with smtplib.SMTP(email_config['server'], email_config['port']) as server:
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        raise


@app.route('/api/reset', methods=['POST'])
def reset():
    global form_data
    form_data = {}
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
