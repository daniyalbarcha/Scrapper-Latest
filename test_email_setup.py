from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, From, To, TrackingSettings, 
    ClickTracking, OpenTracking, SubscriptionTracking
)
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_sendgrid_config():
    """Get SendGrid configuration from environment variables."""
    return {
        'api_key': os.getenv('SENDGRID_API_KEY'),
        'from_email': os.getenv('SENDGRID_FROM_EMAIL'),
        'to_email': os.getenv('SENDGRID_TO_EMAIL'),
        'from_name': os.getenv('SENDGRID_FROM_NAME')
    }

def verify_sendgrid_setup():
    """Verify SendGrid setup and authentication."""
    config = get_sendgrid_config()
    
    if not config['api_key']:
        print("Error: Missing SENDGRID_API_KEY in environment variables")
        return False

    try:
        sg = SendGridAPIClient(config['api_key'])
        
        print("\nChecking SendGrid Setup...")
        
        # Check API key validity
        try:
            key_check = sg.client.api_keys.get()
            print("✅ API Key is valid")
        except Exception as e:
            print(f"❌ API Key error: {str(e)}")
            return False
            
        # Check domain authentication
        try:
            domains = sg.client.whitelabel.domains.get()
            print("\nDomain Authentication Status:")
            domains_data = json.loads(domains.body)
            
            if not domains_data:
                print("❌ No authenticated domains found")
                return False
                
            for domain in domains_data:
                print(f"\nDomain: {domain.get('domain')}")
                print(f"Verified: {'✅' if domain.get('valid') else '❌'}")
                print(f"DNS Records:")
                for record in domain.get('dns', {}).values():
                    print(f"- {record.get('type')} record for {record.get('host')}")
                    print(f"  Valid: {'✅' if record.get('valid') else '❌'}")
        except Exception as e:
            print(f"❌ Domain authentication error: {str(e)}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ SendGrid setup verification failed: {str(e)}")
        return False

def test_sendgrid():
    """Test SendGrid email sending with tracking enabled."""
    config = get_sendgrid_config()
    
    if not all(config.values()):
        print("Error: Missing required environment variables. Please check your .env file.")
        return False

    try:
        if not verify_sendgrid_setup():
            return False
            
        # Initialize SendGrid client
        sg = SendGridAPIClient(config['api_key'])
        
        # Create test message
        message = Mail(
            from_email=From(config['from_email'], config['from_name']),
            to_emails=To(config['to_email']),
            subject='SendGrid Integration Test with Tracking',
            html_content=f'''
            <h2>SendGrid Integration Test</h2>
            <p>This is a test email to verify the SendGrid integration is working properly.</p>
            <p>If you receive this email, please check:</p>
            <ul>
                <li>SPF Authentication: Should pass</li>
                <li>DKIM Authentication: Should pass</li>
                <li>DMARC Status: Should pass</li>
                <li>Sender: Should show as "{config['from_name']}"</li>
                <li>Reply-To: Should go to {config['to_email']}</li>
            </ul>
            <p>Please reply to this email to test the mail setup.</p>
            <p>Click this <a href="http://example.com">test link</a> to verify tracking.</p>
            '''
        )

        # Add tracking settings
        tracking_settings = TrackingSettings()
        tracking_settings.click_tracking = ClickTracking(True, True)
        tracking_settings.open_tracking = OpenTracking(True)
        message.tracking_settings = tracking_settings
        
        # Send the email
        print("\nSending test email...")
        response = sg.send(message)
        print(f"\nSendGrid Test Results:")
        print(f"Status Code: {response.status_code}")
        print(f"Message ID: {response.headers.get('X-Message-Id', 'Not found')}")
        
        return response.status_code in [200, 201, 202]
        
    except Exception as e:
        print(f"\n❌ SendGrid Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("\nTesting Email Setup...")
    if test_sendgrid():
        print("\n✅ SendGrid test email sent successfully!")
        print("\nNext steps:")
        config = get_sendgrid_config()
        print(f"1. Check {config['to_email']} for the test email")
        print("2. Verify the email authentication headers")
        print("3. Reply to the email to test mail setup")
        print("4. Click the test link to verify tracking")
    else:
        print("\n❌ SendGrid test failed!")
        print("\nTroubleshooting steps:")
        print("1. Verify API key permissions in SendGrid dashboard")
        print("2. Check domain authentication status")
        print("3. Verify DNS records are properly set up")
        print("4. Ensure sender email is verified") 