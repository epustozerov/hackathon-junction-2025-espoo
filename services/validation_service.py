from openai import OpenAI
import os
import sys

try:
    from config.config import OPENAI_API_KEY
except ImportError:
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not found. Please set it in config/config.py or as an environment variable.")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)


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

