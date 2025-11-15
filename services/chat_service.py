from openai import OpenAI
import os
import sys
from constants import FORM_STEPS
from services.business_plan_service import get_current_business_plan_question

try:
    from config.config import OPENAI_API_KEY
except ImportError:
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not found. Please set it in config/config.py or as an environment variable.")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)


def get_step_prompt(current_step, form_data, business_plan_sections, is_retry=False, is_skipping=False):
    if current_step and current_step.startswith('bp_'):
        section, question, question_type = get_current_business_plan_question(form_data, business_plan_sections)
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
        section, question, _ = get_current_business_plan_question(form_data, business_plan_sections)
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


def get_openai_response(user_message, current_step, form_data, chat_history, business_plan_sections, is_retry=False, is_skipping=False):
    try:
        context_message = get_step_prompt(current_step, form_data, business_plan_sections, is_retry=is_retry, is_skipping=is_skipping)
        
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


def get_tts_audio(text):
    audio_response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text
    )
    return audio_response.read()


def transcribe_audio(audio_file):
    audio_file.seek(0)
    file_content = audio_file.read()
    audio_file.seek(0)
    
    filename = audio_file.filename or 'audio.webm'
    content_type = audio_file.content_type or 'audio/webm'
    
    transcription = client.audio.transcriptions.create(
        model="whisper-1",
        file=(filename, file_content, content_type)
    )
    return transcription.text

