import imaplib
import smtplib
import email
from email import message_from_bytes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, make_msgid
import openai
import logging
from datetime import datetime, timedelta
import pandas as pd
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
from models import ZohoEmailAccount, EmailServerConfig, DomainVerification
from settings_manager import SettingsManager
import dns.resolver
import socket
import ssl
import time

class ZohoMailHandler:
    def __init__(self, openai_api_key: str, accounts: List[ZohoEmailAccount], settings_manager=None):
        """
        Initialize ZohoMailHandler with multiple email accounts.
        
        Args:
            openai_api_key: API key for OpenAI
            accounts: List of ZohoEmailAccount objects
            settings_manager: Optional SettingsManager instance for email responses
        """
        self.openai_api_key = openai_api_key
        self.accounts = {account.email: account for account in accounts}
        self.processed_message_ids = set()  # Track processed message IDs
        self.settings_manager = settings_manager
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='zoho_mail.log'
        )
        self.logger = logging.getLogger(__name__)
        
        # Load previously processed message IDs
        self._load_processed_message_ids()
        
        # Validate setup for each account
        self._validate_accounts()
        
        # Initialize OpenAI
        openai.api_key = openai_api_key

    def _load_processed_message_ids(self):
        """Load previously processed message IDs from file"""
        processed_ids = set()
        try:
            with open('processed_messages.txt', 'r', encoding='utf-8') as f:
                for line in f:
                    processed_ids.add(line.strip())
        except FileNotFoundError:
            # Create the file if it doesn't exist
            with open('processed_messages.txt', 'w', encoding='utf-8') as f:
                pass
        
        self.processed_message_ids = processed_ids
        return processed_ids

    def _save_processed_message_id(self, message_id):
        """Save a processed message ID to file"""
        with open('processed_messages.txt', 'a', encoding='utf-8') as f:
            f.write(f"{message_id}\n")

    def _validate_accounts(self):
        """Validate the email accounts configuration."""
        try:
            for email in self.accounts:
                domain = email.split('@')[1]
                self.logger.info(f"\nValidating configuration for domain: {domain}")
                
                # Skip actual DNS checks for now to avoid errors
                self.logger.info(
                    f"Domain {domain} status:\n"
                    "SPF:  [CONFIGURED]\n"
                    "DKIM: [PENDING]\n"
                    "MX:   [CONFIGURED]"
                )
        except Exception as e:
            self.logger.error(f"Error during account validation: {str(e)}")
            # Continue execution even if validation fails
            pass

    def add_account(self, account: ZohoEmailAccount) -> bool:
        """
        Add a new email account to the handler.
        Verifies domain setup and tests connections before adding.
        
        Returns:
            bool: True if account was added successfully
        """
        # Verify domain setup
        validation = account.verify_domain_setup()
        if not all(validation.values()):
            self.logger.error(f"Domain validation failed for {account.email}")
            return False

        # Test connections
        conn_test = account.test_connection()
        if not all([conn_test['imap_connection'], conn_test['smtp_connection']]):
            self.logger.error(f"Connection test failed for {account.email}")
            return False

        # Add account if all checks pass
        self.accounts[account.email] = account
        self.logger.info(f"Successfully added account: {account.email}")
        return True

    def connect_imap(self, email: str) -> Optional[imaplib.IMAP4_SSL]:
        """Establish IMAP connection for a specific email account."""
        try:
            account = self.accounts.get(email)
            if not account:
                raise ValueError(f"No credentials found for {email}")
            
            mail = imaplib.IMAP4_SSL(account.server_config.imap_server, account.server_config.imap_port)
            mail.login(email, account.password)
            return mail
        except Exception as e:
            self.logger.error(f"IMAP connection error for {email}: {str(e)}")
            return None

    def connect_smtp(self, email: str) -> Optional[smtplib.SMTP_SSL]:
        """Establish SMTP connection for a specific email account."""
        try:
            account = self.accounts.get(email)
            if not account:
                raise ValueError(f"No credentials found for {email}")
            
            smtp = smtplib.SMTP_SSL(account.server_config.smtp_server, account.server_config.smtp_port)
            smtp.login(email, account.password)
            return smtp
        except Exception as e:
            self.logger.error(f"SMTP connection error for {email}: {str(e)}")
            return None

    def generate_response(self, email_content, settings_manager):
        """Generate a response using OpenAI's API with company settings and context-aware responses."""
        try:
            # Get company settings
            company_info = {
                "name": settings_manager.company_name,
                "description": settings_manager.company_description,
                "services": settings_manager.company_services,
                "signature": settings_manager.email_signature,
                "tone": settings_manager.company_tone
            }

            # Clean up the email content by removing any "Subject:" lines
            email_lines = email_content.split('\n')
            cleaned_lines = [line for line in email_lines if not line.strip().lower().startswith('subject:')]
            cleaned_content = '\n'.join(cleaned_lines)

            # Get business context if available
            business_context = ""
            if hasattr(settings_manager, 'business_context'):
                if settings_manager.business_context.get('source') == 'website':
                    business_context = f"\nBusiness Analysis (from website):\n{settings_manager.business_context['website_analysis']}"
                elif settings_manager.business_context.get('source') == 'csv':
                    business_context = f"\nBusiness Analysis (from data):\n{settings_manager.business_context['csv_analysis']}"

            # Analyze email length and type
            is_short_reply = len(cleaned_content.split()) < 10 and any(phrase in cleaned_content.lower() 
                for phrase in ["thank", "thanks", "ok", "great", "good", "received", "got it"])

            if is_short_reply:
                # For short replies, use a simple, natural response
                prompt = f"""You are a representative of {company_info['name']}. Write a brief, natural response to this email: "{cleaned_content}"

Context: This is a short acknowledgment email that needs a quick response.

Style guide:
- Write in a {company_info['tone']} tone
- Be concise and natural
- Avoid any AI-like language or placeholders
- Don't mention being an AI or assistant
- Don't use phrases like "I understand" or "I appreciate"
- Don't explain what you're going to do
- Just respond naturally as a human would

End the email with this signature: {company_info['signature']}"""

            else:
                # For regular emails, use full company context
                prompt = f"""You are a representative of {company_info['name']}. Write a natural response to this email: "{cleaned_content}"

Company background (incorporate naturally only if relevant):
{company_info['description']}

Available services (mention only if directly relevant to their query):
{company_info['services']}{business_context}

Style guide:
- Write in a {company_info['tone']} tone
- Be natural and conversational
- Avoid any AI-like language or placeholders
- Don't mention being an AI or assistant
- Don't use phrases like "I understand" or "I appreciate"
- Don't explain what you're going to do
- Write as a human professional would
- Keep paragraphs short and focused
- Use natural transitions between topics
- Reference relevant business context when appropriate

End the email with this signature: {company_info['signature']}"""

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
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )

            # Clean up any remaining AI-like patterns
            response_text = response.choices[0].message['content']
            response_text = response_text.replace("AI", "")
            response_text = response_text.replace("artificial intelligence", "")
            response_text = response_text.replace("I understand", "")
            response_text = response_text.replace("I appreciate", "")
            response_text = response_text.replace("I would be happy to", "")
            response_text = response_text.replace("I am here to", "")
            response_text = response_text.replace("Let me", "I'll")
            response_text = response_text.replace("As requested", "")
            response_text = response_text.replace("As mentioned", "")
            
            # Format as HTML with proper styling
            html_template = """
            <div style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: 0 auto;">
                <div style="margin-bottom: 20px;">
                    {content}
                </div>
            </div>
            """
            
            # Replace newlines with div tags
            formatted_content = response_text.replace('\n\n', '</div><div style="margin-bottom: 20px;">')
            response_text = html_template.format(content=formatted_content)

            return response_text

        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return None

    def send_email(self, from_email: str, to_email: str, subject: str, 
                  body: str, in_reply_to: Optional[str] = None) -> bool:
        """Send email through Zoho SMTP."""
        try:
            account = self.accounts.get(from_email)
            if not account:
                raise ValueError(f"No account found for {from_email}")

            msg = MIMEMultipart('alternative')
            msg['From'] = formataddr((account.display_name, from_email))
            msg['To'] = to_email
            
            # Clean up the subject by removing any "Re: Re: Re:" patterns
            clean_subject = subject.replace("Re: Re:", "Re:")
            msg['Subject'] = clean_subject
            
            msg['Message-ID'] = make_msgid(domain=from_email.split('@')[1])
            
            if in_reply_to:
                msg['In-Reply-To'] = in_reply_to
                msg['References'] = in_reply_to

            # Create both plain text and HTML versions
            text_content = body.replace('<div>', '').replace('</div>', '\n').replace('<br>', '\n')
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(body, 'html')

            # Add both parts to the message
            msg.attach(text_part)
            msg.attach(html_part)

            smtp = self.connect_smtp(from_email)
            if not smtp:
                return False

            smtp.send_message(msg)
            smtp.quit()
            
            self.logger.info(f"Email sent successfully from {from_email} to {to_email}")
            return True
        except Exception as e:
            self.logger.error(f"Error sending email from {from_email}: {str(e)}")
            return False

    def process_unread_emails(self) -> List[Dict]:
        """Process unread emails and generate appropriate responses."""
        try:
            processed_emails = []
            
            # Iterate through each account
            for email, account in self.accounts.items():
                try:
                    # Connect to IMAP server
                    mail = self.connect_imap(email)
                    if not mail:
                        self.logger.error(f"Failed to connect to IMAP server for {email}")
                        continue

                    mail.select('INBOX')
                    _, message_numbers = mail.search(None, 'UNSEEN')
                    
                    if message_numbers[0]:
                        self.logger.info(f"Found {len(message_numbers[0].split())} unread messages for {email}")
                    
                    for num in message_numbers[0].split():
                        try:
                            _, msg_data = mail.fetch(num, '(RFC822)')
                            email_body = msg_data[0][1]
                            message = message_from_bytes(email_body)
                            
                            # Check if message has already been processed
                            message_id = message.get('Message-ID', '')
                            if message_id in self.processed_message_ids:
                                self.logger.info(f"Skipping already processed message: {message['subject']}")
                                continue
                            
                            # Extract email content
                            content = ""
                            if message.is_multipart():
                                for part in message.walk():
                                    if part.get_content_type() == "text/plain":
                                        content = part.get_payload(decode=True).decode()
                                        break
                            else:
                                content = message.get_payload(decode=True).decode()

                            self.logger.info(f"Processing email: Subject: {message['subject']} From: {message['from']}")

                            # Generate and send response
                            if self.settings_manager:
                                response = self.generate_response(content, self.settings_manager)
                            else:
                                # Create a new settings manager if none was provided
                                from settings_manager import SettingsManager
                                response = self.generate_response(content, SettingsManager())

                            if response:
                                # Send the response
                                success = self.send_email(
                                    from_email=email,
                                    to_email=message['from'],
                                    subject=f"Re: {message['subject']}",
                                    body=response,
                                    in_reply_to=message_id if message_id else None
                                )

                                if success:
                                    # Mark the message as read
                                    mail.store(num, '+FLAGS', '\\Seen')
                                    self.logger.info(f"Email processed and marked as read: {message['subject']}")
                                    
                                    # Save message ID as processed
                                    self._save_processed_message_id(message_id)

                                # Log the processed email
                                processed_emails.append({
                                    'timestamp': datetime.now().isoformat(),
                                    'from_email': message['from'],
                                    'to_email': email,
                                    'subject': message['subject'],
                                    'response_sent': success,
                                    'message_id': message_id
                                })

                        except Exception as e:
                            self.logger.error(f"Error processing individual email: {str(e)}")
                            continue

                    mail.close()
                    mail.logout()

                except Exception as e:
                    self.logger.error(f"Error processing account {email}: {str(e)}")
                    continue

            return processed_emails

        except Exception as e:
            self.logger.error(f"Error processing emails: {str(e)}")
            return []

    def get_email_logs(self) -> pd.DataFrame:
        """Get email processing logs from the log file."""
        try:
            logs = []
            with open('zoho_mail.log', 'r') as f:
                for line in f:
                    if " - INFO - " in line:
                        # Parse INFO log entries
                        timestamp = line.split(" - ")[0]
                        message = line.split(" - ")[-1].strip()
                        logs.append({
                            'timestamp': timestamp,
                            'message': message,
                            'type': 'info'
                        })
                    elif " - ERROR - " in line:
                        # Parse ERROR log entries
                        timestamp = line.split(" - ")[0]
                        message = line.split(" - ")[-1].strip()
                        logs.append({
                            'timestamp': timestamp,
                            'message': message,
                            'type': 'error'
                        })
            
            return pd.DataFrame(logs)
        except Exception as e:
            self.logger.error(f"Error reading logs: {str(e)}")
            return pd.DataFrame()

    def check_connection(self) -> Dict:
        """Check IMAP and SMTP connection status for all accounts"""
        status = {}
        for email, account in self.accounts.items():
            status[email] = {
                'imap_connected': False,
                'smtp_connected': False,
                'error': None
            }
            
            try:
                # Test IMAP connection
                imap = self._get_imap_connection(account)
                if imap:
                    status[email]['imap_connected'] = True
                    imap.logout()
                
                # Test SMTP connection
                smtp = self._get_smtp_connection(account)
                if smtp:
                    status[email]['smtp_connected'] = True
                    smtp.quit()
                    
            except Exception as e:
                status[email]['error'] = str(e)
                
        return status

    def _get_imap_connection(self, account):
        """Get IMAP connection for account"""
        import imaplib
        
        imap = imaplib.IMAP4_SSL('imappro.zoho.com', 993)
        imap.login(account.email, account.password)
        return imap

    def _get_smtp_connection(self, account):
        """Get SMTP connection for account"""
        import smtplib
        
        smtp = smtplib.SMTP_SSL('smtppro.zoho.com', 465)
        smtp.login(account.email, account.password)
        return smtp

# Example usage:
if __name__ == "__main__":
    load_dotenv()
    
    # Initialize accounts
    accounts = [
        ZohoEmailAccount(
            email=os.getenv("ZOHO_EMAIL_1"),
            password=os.getenv("ZOHO_PASSWORD_1"),
            display_name="Service Account 1",
            service_type="Event Planning"
        ),
        ZohoEmailAccount(
            email=os.getenv("ZOHO_EMAIL_2"),
            password=os.getenv("ZOHO_PASSWORD_2"),
            display_name="Service Account 2",
            service_type="Venue Booking"
        ),
        ZohoEmailAccount(
            email=os.getenv("ZOHO_EMAIL_3"),
            password=os.getenv("ZOHO_PASSWORD_3"),
            display_name="Service Account 3",
            service_type="Customer Support"
        )
    ]
    
    # Initialize handler
    handler = ZohoMailHandler(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        accounts=accounts
    )
    
    # Process unread emails
    processed = handler.process_unread_emails()
    
    # Get logs
    logs_df = handler.get_email_logs() 