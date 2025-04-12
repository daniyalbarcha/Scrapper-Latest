import streamlit as st
from settings_manager import SettingsManager
from email_manager import EmailManager
from ai_responder import AIResponder
import pandas as pd
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_cold_emails.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_cold_emails():
    # Initialize settings manager
    settings_manager = SettingsManager()
    
    # Initialize email manager
    email_manager = EmailManager(settings_manager)
    
    # Check if email manager initialized properly
    if not email_manager.is_initialized():
        error = email_manager.get_error()
        logger.error(f"Email manager initialization failed: {error}")
        return False
    
    logger.info("Email manager initialized successfully")
    
    # Create test data
    test_profiles = [
        {
            'email': 'test@lavalcarlogos.com',
            'name': 'John Designer',
            'subject': 'Collaboration on Automotive Logo Design',
            'body': '''
            <p>Hi John,</p>
            <p>I noticed your impressive work in automotive logo design, especially your recent project for the premium car dealership.</p>
            <p>At Laval Car Logos, we specialize in creating unique and memorable car logos for automotive businesses. I'd love to explore potential collaboration opportunities.</p>
            <p>Would you be open to a brief discussion about how we might work together?</p>
            <p>Best regards,<br>Laval Car Logos Team</p>
            '''
        },
        {
            'email': 'test2@lavalcarlogos.com',
            'name': 'Sarah Brand',
            'subject': 'Partnership in Automotive Branding',
            'body': '''
            <p>Hi Sarah,</p>
            <p>Your work in automotive branding caught my attention, particularly your recent success with luxury car dealers.</p>
            <p>As a company focused on creating distinctive car logos, we see great potential in combining our expertise with your branding prowess.</p>
            <p>Would you be interested in discussing how we could create value together?</p>
            <p>Best regards,<br>Laval Car Logos Team</p>
            '''
        }
    ]
    
    logger.info(f"Testing with {len(test_profiles)} test profiles")
    
    # Test email sending
    try:
        # Send emails via SendGrid
        results = email_manager.sendgrid.send_bulk_emails(test_profiles)
        
        # Log results
        success_count = results['success']
        failed_count = results['failed']
        
        logger.info(f"Email sending results - Success: {success_count}, Failed: {failed_count}")
        
        # Write results to file
        with open('test_cold_emails_results.txt', 'w') as f:
            f.write("Cold Email Test Results\n")
            f.write("======================\n\n")
            f.write(f"Total Profiles: {len(test_profiles)}\n")
            f.write(f"Emails Sent Successfully: {success_count}\n")
            f.write(f"Failed Emails: {failed_count}\n\n")
            
            if results['errors']:
                f.write("\nErrors:\n")
                for error in results['errors']:
                    f.write(f"- {error}\n")
        
        return success_count > 0
        
    except Exception as e:
        logger.error(f"Error during email sending test: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing cold email functionality...")
    success = test_cold_emails()
    if success:
        print("✅ Cold email test completed successfully!")
        print("Check test_cold_emails_results.txt for detailed results")
    else:
        print("❌ Cold email test failed!")
        print("Check test_cold_emails.log for error details") 