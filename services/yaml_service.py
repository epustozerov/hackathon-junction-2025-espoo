import os
import re
from utils.helpers import slugify


def update_yaml_with_answer(yaml_path, question_label, answer):
    if not answer or answer.strip() == '':
        return False
    
    answer_escaped = answer.replace('"', '\\"').replace('\n', '\\n')
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    question_id = slugify(question_label)
    updated = False
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        question_match = re.match(r'"([^"]+)":', stripped)
        if question_match:
            current_question_label = question_match.group(1)
            current_question_id = slugify(current_question_label)
            
            if current_question_id == question_id:
                j = i + 1
                answer_found = False
                while j < len(lines):
                    stripped_line = lines[j].strip()
                    if stripped_line.startswith('answer:'):
                        indent = len(lines[j]) - len(lines[j].lstrip())
                        lines[j] = ' ' * indent + f'answer: "{answer_escaped}"\n'
                        updated = True
                        answer_found = True
                        break
                    elif stripped_line and not stripped_line.startswith('#') and ':' in stripped_line and not stripped_line.startswith('answer:'):
                        indent = len(lines[j]) - len(lines[j].lstrip())
                        lines.insert(j, ' ' * indent + f'answer: "{answer_escaped}"\n')
                        updated = True
                        answer_found = True
                        break
                    elif stripped_line.startswith('# ---'):
                        if not answer_found:
                            indent = len(lines[i]) - len(lines[i].lstrip())
                            lines.insert(j, ' ' * indent + f'answer: "{answer_escaped}"\n')
                            updated = True
                        break
                    j += 1
                
                if not answer_found and j >= len(lines):
                    indent = len(lines[i]) - len(lines[i].lstrip())
                    lines.insert(j, ' ' * indent + f'answer: "{answer_escaped}"\n')
                    updated = True
                break
        
        i += 1
    
    if updated:
        with open(yaml_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    
    return updated


def get_yaml_path():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, 'config', 'improved_business_plan.yaml')

