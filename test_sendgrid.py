from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_sendgrid_connection():
    """Test SendGrid connection using environment variables."""
    # Get configuration from environment variables
    api_key = os.getenv('SENDGRID_API_KEY')
    from_email = os.getenv('SENDGRID_FROM_EMAIL')
    to_email = os.getenv('SENDGRID_TO_EMAIL')
    from_name = os.getenv('SENDGRID_FROM_NAME')

    if not all([api_key, from_email, to_email, from_name]):
        print("Error: Missing required environment variables. Please check your .env file.")
        return None

    try:
        # Initialize SendGrid client
        sg = SendGridAPIClient(api_key)
        
        # Create test message
        message = Mail(
            from_email=From(from_email, from_name),
            to_emails=To(to_email),
            subject='SendGrid Test Email',
            html_content='This is a test email to verify SendGrid integration is working properly.'
        )
        
        # Send the email
        response = sg.send(message)
        
        # Print response
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        return response.status_code
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    print("Testing SendGrid Connection...")
    status_code = test_sendgrid_connection()
    if status_code in [200, 201, 202]:
        print("✅ SendGrid test successful!")
    else:
        print("❌ SendGrid test failed!") 