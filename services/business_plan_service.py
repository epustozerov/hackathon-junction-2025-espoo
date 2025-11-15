import os
import re
from utils.helpers import slugify
from constants import FORM_STEPS


def load_business_plan_from_yaml():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    yaml_path = os.path.join(base_dir, 'config', 'improved_business_plan.yaml')
    
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


def calculate_points(form_data, business_plan_sections):
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
    
    for section in business_plan_sections:
        for question in section['core_questions']:
            question_value = form_data.get(question['id'])
            if question_value and question_value != '':
                points += 3
        for question in section['optional_questions']:
            question_value = form_data.get(question['id'])
            if question_value and question_value != '':
                points += 5
    
    return points


def get_current_tier(points, tiers):
    current_tier = tiers[0]
    for tier in reversed(tiers):
        if points >= tier['points_required']:
            current_tier = tier
            break
    return current_tier


def is_initial_form_complete(form_data):
    return all(form_data.get(step['id']) and form_data.get(step['id']) != '' for step in FORM_STEPS)


def get_current_business_plan_question(form_data, business_plan_sections):
    for section in business_plan_sections:
        for question in section['core_questions']:
            question_value = form_data.get(question['id'])
            if question_value is None:
                return section, question, 'core'
        for question in section['optional_questions']:
            question_value = form_data.get(question['id'])
            if question_value is None:
                return section, question, 'optional'
    return None, None, None


def get_business_plan_progress(form_data, business_plan_sections):
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
    
    for section in business_plan_sections:
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

