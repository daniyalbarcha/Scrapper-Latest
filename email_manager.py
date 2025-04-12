from sendgrid_handler import SendGridHandler
from zoho_mail_handler import ZohoMailHandler
import logging
import streamlit as st
from models import ZohoEmailAccount, EmailServerConfig
import pandas as pd
from datetime import datetime, timedelta

class EmailManager:
    def __init__(self, settings_manager):
        self.error_message = None
        self.initialized = False
        
        # Store settings manager
        self.settings_manager = settings_manager
        
        # Validate email settings
        validation_errors = self._validate_settings(settings_manager)
        if validation_errors:
            self.error_message = "Email Configuration Errors:\n" + "\n".join(validation_errors)
            return
            
        try:
            # Initialize SendGrid for cold emails
            self.sendgrid = SendGridHandler(
                api_key=settings_manager.sendgrid_key,
                from_email=settings_manager.cold_email,
                from_name=settings_manager.company_name,
                reply_to_email=settings_manager.response_email
            )
            
            # Initialize Zoho for responses
            zoho_account = ZohoEmailAccount(
                email=settings_manager.response_email,
                password=settings_manager.email_password,
                display_name=settings_manager.company_name,
                service_type="Customer Support"
            )
            
            self.zoho = ZohoMailHandler(
                openai_api_key=settings_manager.openai_key,
                accounts=[zoho_account],
                settings_manager=settings_manager  # Pass the settings manager instance
            )
            
            self.initialized = True
            
            # Store domains for monitoring
            self.cold_email_domain = settings_manager.cold_email_domain
            self.main_domain = settings_manager.main_domain
            
        except Exception as e:
            self.error_message = f"Failed to initialize email services: {str(e)}"
    
    def _validate_settings(self, settings_manager):
        """Validate email settings"""
        errors = []
        
        # Validate SendGrid settings
        if not settings_manager.sendgrid_key:
            errors.append("SendGrid API key is missing")
        if not settings_manager.cold_email:
            errors.append("Cold email address is missing")
        if not settings_manager.cold_email_domain:
            errors.append("Cold email domain is missing")
            
        # Validate Zoho settings
        if not settings_manager.response_email:
            errors.append("Response email address is missing")
        if not settings_manager.email_password:
            errors.append("Zoho email password is missing")
        if not settings_manager.main_domain:
            errors.append("Main domain is missing")
            
        # Validate company info
        if not settings_manager.company_name:
            errors.append("Company name is missing")
            
        return errors
    
    def monitor_email_health(self):
        """Monitor health of both SendGrid and Zoho email services"""
        if not self.is_initialized():
            return {
                'cold_emails': {'status': 'error', 'issues': ['Email manager not initialized']},
                'responses': {'status': 'error', 'issues': ['Email manager not initialized']}
            }
        
        health_status = {
            'cold_emails': {'status': 'healthy', 'issues': []},
            'responses': {'status': 'healthy', 'issues': []}
        }
        
        # Check SendGrid health
        try:
            # Check API key validity
            if not self.sendgrid.verify_api_key():
                health_status['cold_emails']['issues'].append('Invalid SendGrid API key')
            
            # Get recent delivery stats
            stats = self.sendgrid.get_stats()
            if stats:
                if stats.get('blocks', 0) > 0 or stats.get('bounces', 0) > 0:
                    health_status['cold_emails']['issues'].append(
                        f"Delivery issues detected: {stats.get('blocks', 0)} blocks, {stats.get('bounces', 0)} bounces"
                    )
                
                # Check for low engagement
                if stats.get('delivered', 0) > 0 and stats.get('opened', 0) == 0:
                    health_status['cold_emails']['issues'].append('Low email engagement detected')
            
            # Update status based on issues
            if health_status['cold_emails']['issues']:
                health_status['cold_emails']['status'] = 'warning'
            
        except Exception as e:
            health_status['cold_emails']['status'] = 'error'
            health_status['cold_emails']['issues'].append(str(e))
        
        # Check Zoho health
        try:
            # Check connection status
            conn_status = self.zoho.check_connection()
            
            for email, status in conn_status.items():
                if not status.get('imap_connected'):
                    health_status['responses']['issues'].append(f'IMAP connection failed for {email}')
                if not status.get('smtp_connected'):
                    health_status['responses']['issues'].append(f'SMTP connection failed for {email}')
                if status.get('error'):
                    health_status['responses']['issues'].append(f'Error for {email}: {status["error"]}')
            
            # Check recent activity
            logs = self.zoho.get_email_logs()
            if not logs.empty:
                # Parse timestamps with explicit format
                logs['timestamp'] = pd.to_datetime(logs['timestamp'], format='%Y-%m-%d %H:%M:%S,%f')
                last_response = logs['timestamp'].max()
                if last_response:
                    # Add last response time to status
                    health_status['responses']['last_response'] = last_response.isoformat()
                    health_status['responses']['total_responses'] = len(logs)
                    
                    # Check for long periods of inactivity
                    if (datetime.now() - last_response) > timedelta(hours=24):
                        health_status['responses']['issues'].append('No response activity in last 24 hours')
            
            # Update status based on issues
            if health_status['responses']['issues']:
                health_status['responses']['status'] = 'error'
            
        except Exception as e:
            health_status['responses']['status'] = 'error'
            health_status['responses']['issues'].append(str(e))
        
        return health_status
    
    def is_initialized(self):
        """Check if email manager is properly initialized"""
        return self.initialized
    
    def has_error(self):
        """Check if there was an initialization error"""
        return self.error_message is not None
    
    def get_error(self):
        """Get the initialization error message"""
        return self.error_message
    
    def send_cold_emails(self, leads_df):
        """Send cold emails using SendGrid"""
        if not self.is_initialized():
            raise ValueError("Email manager not properly initialized. Please check settings.")
            
        try:
            # Convert DataFrame to list of dicts
            leads = leads_df.to_dict('records')
            
            # Send emails via SendGrid
            results = self.sendgrid.send_bulk_emails(leads)
            
            # Log results
            if results['success'] > 0:
                st.success(f"✅ Successfully sent {results['success']} emails")
            if results['failed'] > 0:
                st.error(f"❌ Failed to send {results['failed']} emails")
                for error in results['errors']:
                    logging.error(error)
            
            return results
            
        except Exception as e:
            error_msg = f"Failed to send cold emails: {str(e)}"
            logging.error(error_msg)
            st.error(f"❌ {error_msg}")
            raise
    
    def handle_responses(self):
        """Handle email responses using Zoho"""
        if not self.is_initialized():
            raise ValueError("Email manager not properly initialized. Please check settings.")
            
        try:
            # Process new responses using Zoho handler
            processed_emails = self.zoho.process_unread_emails()
            
            # Log results
            if processed_emails:
                st.success(f"✅ Successfully processed {len(processed_emails)} responses")
                for email in processed_emails:
                    logging.info(f"Processed response to: {email['to_email']}")
            
            return processed_emails
            
        except Exception as e:
            error_msg = f"Failed to process responses: {str(e)}"
            logging.error(error_msg)
            st.error(f"❌ {error_msg}")
            raise 