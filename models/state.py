from services.business_plan_service import load_business_plan_from_yaml

form_data = {}
chat_history = []
question_retries = {}
business_plan_sections = load_business_plan_from_yaml()


def reset_state():
    global form_data, chat_history, question_retries
    form_data = {}
    chat_history = []
    question_retries = {}

