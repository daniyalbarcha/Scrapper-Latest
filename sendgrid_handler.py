from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, From, ReplyTo, TrackingSettings, ClickTracking, OpenTracking
import logging
import json
from datetime import datetime, timedelta
import openai
from typing import Dict

class SendGridHandler:
    def __init__(self, api_key, from_email, from_name, reply_to_email):
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name
        self.reply_to_email = reply_to_email
        self.sg = SendGridAPIClient(api_key)
        
        # Validate domain setup
        self._validate_domain_setup()
    
    def _validate_domain_setup(self):
        """Validate SendGrid domain authentication"""
        try:
            # Get domain authentication info
            response = self.sg.client.whitelabel.domains.get()
            domains = json.loads(response.body)
            
            # Check if our domain is authenticated
            our_domain = self.from_email.split('@')[1]
            domain_valid = False
            
            for domain in domains:
                if domain['domain'] == our_domain:
                    if domain['valid']:
                        domain_valid = True
                        break
                    else:
                        logging.warning(f"Domain {our_domain} is not fully validated in SendGrid")
            
            if not domain_valid:
                logging.error(f"Domain {our_domain} not found or not authenticated in SendGrid")
                
        except Exception as e:
            logging.error(f"Failed to validate SendGrid domain: {str(e)}")
    
    def verify_api_key(self) -> bool:
        """Verify SendGrid API key is valid by making a test API call"""
        try:
            # Try to get API key info - this will fail if key is invalid
            response = self.sg.client.api_keys._(self.api_key).get()
            return response.status_code == 200
        except Exception as e:
            logging.error(f"SendGrid API key verification failed: {str(e)}")
            return False

    def get_stats(self) -> Dict:
        """Get recent email statistics"""
        try:
            # Get stats for last 24 hours
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)
            
            response = self.sg.client.stats.get(
                query_params={
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'aggregated_by': 'day'
                }
            )
            
            if response.status_code == 200:
                stats = json.loads(response.body)[0]
                return {
                    'sent': stats.get('requests', 0),
                    'delivered': stats.get('delivered', 0),
                    'opened': stats.get('opens', 0),
                    'clicked': stats.get('clicks', 0),
                    'bounces': stats.get('bounces', 0),
                    'blocks': stats.get('blocks', 0)
                }
            return {}
            
        except Exception as e:
            logging.error(f"Error getting SendGrid stats: {str(e)}")
            return {}
    
    def send_bulk_emails(self, leads):
        """Send bulk emails with proper tracking"""
        results = {
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for lead in leads:
            try:
                # Create personalized message
                message = Mail(
                    from_email=From(self.from_email, self.from_name),
                    to_emails=To(lead['email'], lead.get('name', '')),
                    subject=lead['subject'],
                    html_content=lead['body']
                )
                
                # Add reply-to header
                message.reply_to = ReplyTo(
                    self.reply_to_email,
                    self.from_name
                )
                
                # Add tracking settings
                tracking_settings = TrackingSettings()
                tracking_settings.click_tracking = ClickTracking(True, True)
                tracking_settings.open_tracking = OpenTracking(True)
                message.tracking_settings = tracking_settings
                
                # Send with error handling
                response = self.sg.send(message)
                if response.status_code in [200, 201, 202]:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(
                        f"Failed to send to {lead['email']}: Status {response.status_code}"
                    )
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(
                    f"Error sending to {lead['email']}: {str(e)}"
                )
                
        return results
        
    def _generate_email_content(self, lead):
        """Generate personalized email content"""
        return f"""
        <p>Hi {lead.get('first_name', '')},</p>
        
        <p>I noticed your recent post about {lead.get('recent_post', '')} and was really impressed with your content.</p>
        
        <p>{lead.get('custom_message', '')}</p>
        
        <p>Would love to connect and discuss potential collaboration opportunities.</p>
        
        <p>Best regards,<br>
        {self.from_name}</p>
        """

    def handle_inbound_email(self, email_data):
        """Handle inbound email from SendGrid's parse webhook"""
        try:
            # Extract email data
            from_email = email_data.get('from')
            subject = email_data.get('subject')
            text = email_data.get('text', '')
            html = email_data.get('html', '')
            
            # Generate AI response
            response = self.generate_response(text or html)
            
            if response:
                # Create response email
                message = Mail(
                    from_email=From(self.from_email, self.from_name),
                    to_emails=To(from_email),
                    subject=f"Re: {subject}",
                    html_content=response
                )
                
                # Add reply-to header
                message.reply_to = ReplyTo(
                    self.reply_to_email,
                    self.from_name
                )
                
                # Send response
                response = self.sg.send(message)
                return response.status_code in [200, 201, 202]
                
            return False
            
        except Exception as e:
            logging.error(f"Error handling inbound email: {str(e)}")
            return False

    def generate_response(self, email_content):
        """Generate AI response to email"""
        try:
            # Use OpenAI to generate response
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": """You are an experienced professional writing email responses.
                    - Write naturally as a human
                    - Never use AI-like language
                    - Never mention being an AI
                    - Never use placeholders
                    - Be direct and professional
                    - Don't explain your process
                    - Don't use phrases like "I understand" or "I appreciate"
                    - Don't preface your response with explanations"""},
                    {"role": "user", "content": f"Generate a professional response to this email:\n\n{email_content}"}
                ],
                temperature=0.7
            )
            
            response_text = response.choices[0].message['content']
            
            # Clean up AI-like patterns
            response_text = response_text.replace("AI", "")
            response_text = response_text.replace("artificial intelligence", "")
            response_text = response_text.replace("I understand", "")
            response_text = response_text.replace("I appreciate", "")
            response_text = response_text.replace("I would be happy to", "")
            response_text = response_text.replace("I am here to", "")
            response_text = response_text.replace("Let me", "I'll")
            response_text = response_text.replace("As requested", "")
            response_text = response_text.replace("As mentioned", "")
            
            # Format as HTML
            return f"<div style='font-family: Arial, sans-serif;'>{response_text}</div>"
            
        except Exception as e:
            logging.error(f"Error generating response: {str(e)}")
            return None 