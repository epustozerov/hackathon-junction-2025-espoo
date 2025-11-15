from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

FORM_STEPS = [
    {'id': 'company_name', 'label': 'Company Name', 'completed': False},
    {'id': 'language', 'label': 'Language', 'completed': False},
    {'id': 'sphere', 'label': 'Business Sphere', 'completed': False},
    {'id': 'education', 'label': 'Education', 'completed': False},
    {'id': 'experience', 'label': 'Experience', 'completed': False},
    {'id': 'location', 'label': 'Location', 'completed': False},
]

form_data = {}


def get_mock_response(user_message, current_step):
    user_lower = user_message.lower()
    
    if current_step == 'company_name':
        if len(user_message.strip()) > 1:
            return {
                'message': f"Great! I've noted your company name: {user_message}. What's your preferred language? ("
                           f"e.g., English, Spanish, French, German)",
                'step': 'language'
            }
        return {
            'message': "Please provide your company name.",
            'step': 'company_name'
        }
    
    if current_step == 'language':
        lang_map = {
            'english': 'English',
            'spanish': 'Spanish',
            'french': 'French',
            'german': 'German'
        }
        detected_lang = None
        for key, value in lang_map.items():
            if key in user_lower:
                detected_lang = value
                break
        
        if detected_lang:
            return {
                'message': f"Perfect! I've set your language to {detected_lang}. Now, what sphere or industry does "
                           f"your business operate in?",
                'step': 'sphere'
            }
        return {
            'message': "What's your preferred language? (e.g., English, Spanish, French, German)",
            'step': 'language'
        }
    
    if current_step == 'sphere':
        if len(user_message.strip()) > 2:
            return {
                'message': f"Got it! Your business is in {user_message}. What's your educational background?",
                'step': 'education'
            }
        return {
            'message': "Please tell me what industry or business sphere you're in.",
            'step': 'sphere'
        }
    
    if current_step == 'education':
        if len(user_message.strip()) > 2:
            return {
                'message': f"Thanks! I've noted your education: {user_message}. How many years of experience do you "
                           f"have in business?",
                'step': 'experience'
            }
        return {
            'message': "What's your educational background? (e.g., Bachelor's in Business, MBA, etc.)",
            'step': 'education'
        }
    
    if current_step == 'experience':
        if len(user_message.strip()) > 0:
            return {
                'message': f"Excellent! {user_message} years of experience. Finally, where is your business located?",
                'step': 'location'
            }
        return {
            'message': "How many years of business experience do you have?",
            'step': 'experience'
        }
    
    if current_step == 'location':
        if len(user_message.strip()) > 2:
            return {
                'message': f"Perfect! Your business is located in {user_message}. Thank you for completing the form! "
                           f"Is there anything else you'd like to add?",
                'step': 'complete'
            }
        return {
            'message': "Where is your business located?",
            'step': 'location'
        }
    
    return {
        'message': "Thank you for providing all the information! Your form is complete. Is there anything else you'd "
                   "like to discuss?",
        'step': 'complete'
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
    
    response = get_mock_response(user_message, current_step)
    
    completed_steps = []
    for step in FORM_STEPS:
        if form_data.get(step['id']):
            completed_steps.append(step['id'])
    
    return jsonify({
        'response': response['message'],
        'completed_steps': completed_steps,
        'form_data': form_data.copy()
    })


@app.route('/api/reset', methods=['POST'])
def reset():
    global form_data
    form_data = {}
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
