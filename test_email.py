import streamlit as st
import logging
from settings_manager import SettingsManager
from email_manager import EmailManager
from ai_responder import AIResponder
import pandas as pd
from datetime import datetime, timedelta
from sendgrid_handler import SendGridHandler
from zoho_mail_handler import ZohoMailHandler, ZohoEmailAccount

def test_email():
    """Test email functionality"""
    try:
        print("Initializing settings...")
        settings = SettingsManager()
        
        print(f"SendGrid Key: {bool(settings.sendgrid_key)}")
        print(f"Cold Email: {settings.cold_email}")
        print(f"Response Email: {settings.response_email}")
        print(f"Email Password: {bool(settings.email_password)}")
        
        # Open output file with UTF-8 encoding
        with open('test_output.txt', 'w', encoding='utf-8') as f:
            try:
                print("Testing SendGrid...")
                # Test SendGrid cold email
                sendgrid = SendGridHandler(
                    api_key=settings.sendgrid_key,
                    from_email=settings.cold_email,
                    from_name=settings.company_name,
                    reply_to_email=settings.response_email
                )
                
                # Test email data
                test_email = {
                    'email': settings.response_email,  # Send to our own email for testing
                    'name': 'Test User',
                    'subject': 'Test Email from ' + settings.company_name,
                    'body': f'''
                    <div style="font-family: Arial, sans-serif; padding: 20px;">
                        <p>Hello Test User,</p>
                        
                        <p>This is a test email to verify our email system configuration.</p>
                        
                        <p>If you receive this email, it means:</p>
                        <ul>
                            <li>SendGrid is properly configured for sending cold emails</li>
                            <li>The email formatting is working correctly</li>
                        </ul>
                        
                        <p>Please reply to this email to test the Zoho response system.</p>
                        
                        <p>Best regards,<br>
                        {settings.company_name}</p>
                    </div>
                    '''
                }
                
                # Send test email
                print("Sending test email...")
                result = sendgrid.send_bulk_emails([test_email])
                if result['success'] > 0:
                    f.write("✓ SendGrid test email sent successfully\n")
                else:
                    f.write("✗ SendGrid test failed\n")
                    if result.get('errors'):
                        f.write(f"Errors: {', '.join(result['errors'])}\n")
                
                # Test Zoho response handling
                try:
                    print("Testing Zoho...")
                    # Initialize Zoho handler
                    zoho = ZohoMailHandler(
                        openai_api_key=settings.openai_key,
                        accounts=[
                            ZohoEmailAccount(
                                email=settings.response_email,
                                password=settings.email_password,
                                display_name=settings.company_name,
                                service_type="Test"
                            )
                        ]
                    )
                    
                    # Check connection
                    print("Checking Zoho connection...")
                    status = zoho.check_connection()
                    print(f"Connection status: {status}")
                    if status[settings.response_email]['imap_connected'] and status[settings.response_email]['smtp_connected']:
                        f.write("✓ Zoho connection test successful\n")
                    else:
                        error = status[settings.response_email].get('error', 'Unknown error')
                        f.write(f"✗ Zoho connection test failed: {error}\n")
                    
                except Exception as e:
                    print(f"Zoho error: {str(e)}")
                    f.write(f"✗ Zoho handler initialization failed: {str(e)}\n")
                
            except Exception as e:
                print(f"Test error: {str(e)}")
                f.write(f"✗ Test failed: {str(e)}\n")
    
    except Exception as e:
        print(f"Error during test: {str(e)}")

if __name__ == "__main__":
    test_email() 