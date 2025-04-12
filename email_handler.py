from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import imaplib
from email.header import decode_header
import openai
import streamlit as st

class EmailHandler:
    def __init__(self, email_address, email_password, sendgrid_api_key):
        self.email_address = email_address
        self.email_password = email_password
        self.sendgrid_api_key = sendgrid_api_key

    def send_email_via_sendgrid(self, to_email, subject, html_content, from_email="info@hoppenlyevents.com"):
        if not self.sendgrid_api_key:
            st.warning("No SENDGRID_API_KEY found. Cannot send emails.")
            return None

        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        try:
            sg = SendGridAPIClient(self.sendgrid_api_key)
            response = sg.send(message)
            return response.status_code
        except Exception as e:
            st.warning(f"SendGrid Error: {str(e)}")
            return None

    def check_email_replies(self):
        # Connect to the email server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(self.email_address, self.email_password)
        mail.select("inbox")

        # Search for all emails
        status, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()

        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    if "your_unique_identifier" in subject:
                        self.process_email_reply(msg)

    def process_email_reply(self, msg):
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()

        # Generate a reply using OpenAI
        openai.api_key = OPENAI_API_KEY
        response = openai.Completion.create(
            engine="gpt-4",
            prompt=f"Reply to this email: {body}",
            max_tokens=150
        )
        reply = response.choices[0].text.strip()
        print("Generated reply:", reply) 