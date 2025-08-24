from flask import Blueprint, request, jsonify
import csv
import io
import json
import requests
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import openai
import os

email_outreach_bp = Blueprint('email_outreach', __name__)

# Email templates
REAL_ESTATE_TEMPLATE = """
Subject: Boost Your Property Listings & Social Media with AI (No Face-to-Face Needed!)

Dear {name},

Are you looking to make your property listings stand out and supercharge your social media presence, all while saving valuable time? Our AI-powered services are designed to do just that, efficiently and without any need for face-to-face meetings.

We specialize in:

• AI-Powered Property Listing Descriptions: Transform property videos and details into compelling, professional listings that attract more buyers.
• Engaging Social Media Content Packages: Get ready-to-use images, captivating captions, and short videos to keep your audience hooked.
• Stunning AI-Generated Marketing Materials: From brochures to flyers and web pages, we create visually appealing materials that convert.

Imagine having all your marketing content handled swiftly and professionally, allowing you to focus on closing deals. Our service is completely remote and optimized for quick delivery, ensuring you see results fast.

Ready to elevate your real estate marketing? Reply to this email with your availability for a quick chat, or simply tell us which service you're most interested in, and we'll send you a tailored proposal.

Best regards,
AI Marketing Solutions
"""

LAW_FIRM_TEMPLATE = """
Subject: Streamline Your Legal Operations with AI: Efficient & Confidential Support

Dear {name},

In today's fast-paced legal environment, efficiency and accuracy are paramount. Our AI-powered services offer a confidential and highly efficient way to streamline your firm's operations, without requiring any in-person interaction.

We provide specialized support in:

• AI-Powered Audio Transcription & Summarization: Convert voice messages, meetings, and dictations into accurate transcripts and concise summaries, saving hours of manual work.
• Advanced PDF Analysis & Data Extraction: Quickly transform complex contracts and legal documents into structured spreadsheets for easy analysis and management.
• Legal Document Processing & Analysis: Leverage AI for efficient contract review, analysis, and generation, enhancing accuracy and reducing turnaround times.

Our remote service ensures your sensitive legal work is handled with utmost professionalism and discretion, allowing your team to focus on critical legal matters. We deliver rapid results, helping you meet tight deadlines and improve overall productivity.

Interested in discovering how AI can transform your firm's efficiency? Reply to this email to schedule a brief discussion, or let us know which service would benefit your firm most, and we'll provide a detailed overview.

Sincerely,
AI Legal Solutions
"""

@email_outreach_bp.route('/upload-leads', methods=['POST'])
def upload_leads():
    """Upload and process leads from CSV file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read CSV content
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        leads = []
        
        for row in csv_input:
            if row.get('email') and row.get('name'):
                leads.append({
                    'name': row.get('name', ''),
                    'email': row.get('email', ''),
                    'company': row.get('company', ''),
                    'industry': row.get('industry', ''),
                    'location': row.get('location', ''),
                    'phone': row.get('phone', ''),
                    'contacted': row.get('contacted', 'false').lower() == 'true'
                })
        
        return jsonify({
            'message': f'Successfully processed {len(leads)} leads',
            'leads': leads
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@email_outreach_bp.route('/send-emails', methods=['POST'])
def send_emails():
    """Send personalized emails to leads"""
    try:
        data = request.get_json()
        leads = data.get('leads', [])
        smtp_config = data.get('smtp_config', {})
        
        if not leads:
            return jsonify({'error': 'No leads provided'}), 400
        
        if not smtp_config:
            return jsonify({'error': 'SMTP configuration required'}), 400
        
        results = []
        
        for lead in leads:
            if lead.get('contacted', False):
                continue
                
            try:
                # Generate personalized email content
                template = REAL_ESTATE_TEMPLATE if lead.get('industry') == 'real_estate' else LAW_FIRM_TEMPLATE
                email_content = template.format(
                    name=lead.get('name', 'there'),
                    company=lead.get('company', ''),
                    location=lead.get('location', '')
                )
                
                # Send email
                success = send_email(
                    smtp_config,
                    lead.get('email'),
                    email_content,
                    lead.get('industry', 'general')
                )
                
                if success:
                    results.append({
                        'email': lead.get('email'),
                        'name': lead.get('name'),
                        'status': 'sent'
                    })
                    # Add delay between emails
                    time.sleep(30)
                else:
                    results.append({
                        'email': lead.get('email'),
                        'name': lead.get('name'),
                        'status': 'failed'
                    })
                    
            except Exception as e:
                results.append({
                    'email': lead.get('email'),
                    'name': lead.get('name'),
                    'status': 'error',
                    'error': str(e)
                })
        
        return jsonify({
            'message': f'Email campaign completed',
            'results': results
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def send_email(smtp_config, to_email, content, industry):
    """Send individual email using SMTP"""
    try:
        # Extract subject and body from content
        lines = content.strip().split('\n')
        subject_line = next((line for line in lines if line.startswith('Subject:')), 'AI Services Inquiry')
        subject = subject_line.replace('Subject:', '').strip()
        
        # Remove subject line from content
        body_lines = [line for line in lines if not line.startswith('Subject:')]
        body = '\n'.join(body_lines).strip()
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_config.get('from_email')
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to SMTP server and send
        server = smtplib.SMTP(smtp_config.get('smtp_server'), smtp_config.get('smtp_port', 587))
        server.starttls()
        server.login(smtp_config.get('username'), smtp_config.get('password'))
        
        text = msg.as_string()
        server.sendmail(smtp_config.get('from_email'), to_email, text)
        server.quit()
        
        return True
        
    except Exception as e:
        print(f"Error sending email to {to_email}: {str(e)}")
        return False

@email_outreach_bp.route('/test-smtp', methods=['POST'])
def test_smtp():
    """Test SMTP configuration"""
    try:
        data = request.get_json()
        smtp_config = data.get('smtp_config', {})
        
        # Test connection
        server = smtplib.SMTP(smtp_config.get('smtp_server'), smtp_config.get('smtp_port', 587))
        server.starttls()
        server.login(smtp_config.get('username'), smtp_config.get('password'))
        server.quit()
        
        return jsonify({'message': 'SMTP configuration is valid'}), 200
        
    except Exception as e:
        return jsonify({'error': f'SMTP test failed: {str(e)}'}), 400

@email_outreach_bp.route('/preview-email', methods=['POST'])
def preview_email():
    """Preview email content for a lead"""
    try:
        data = request.get_json()
        lead = data.get('lead', {})
        
        template = REAL_ESTATE_TEMPLATE if lead.get('industry') == 'real_estate' else LAW_FIRM_TEMPLATE
        email_content = template.format(
            name=lead.get('name', 'there'),
            company=lead.get('company', ''),
            location=lead.get('location', '')
        )
        
        return jsonify({'email_content': email_content}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

