import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from services.docx_service import create_docx_from_form_data
from services.yaml_service import get_yaml_path


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


def send_report_email(form_data, business_plan_sections, yaml_path=None):
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
    
    if yaml_path is None:
        yaml_path = get_yaml_path()
    
    report_text = generate_report(form_data)
    
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = 'Business Information Form Report'
    
    msg.attach(MIMEText(report_text, 'plain'))
    
    docx_path = None
    try:
        docx_path = create_docx_from_form_data(form_data, business_plan_sections)
        if docx_path and os.path.exists(docx_path):
            with open(docx_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename=business_plan.docx',
            )
            msg.attach(part)
    except Exception as e:
        print(f"Warning: Could not create or attach DOCX: {str(e)}")
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(sender, receiver, msg.as_string())
        
        if docx_path and os.path.exists(docx_path):
            try:
                os.remove(docx_path)
            except:
                pass
        
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        if docx_path and os.path.exists(docx_path):
            try:
                os.remove(docx_path)
            except:
                pass
        raise

