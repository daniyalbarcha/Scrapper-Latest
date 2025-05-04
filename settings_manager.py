import os
from dotenv import load_dotenv
from typing import List, Dict, Optional
from models import ZohoEmailAccount
import json
import streamlit as st
import logging

# Configure logging
logger = logging.getLogger(__name__)

class SettingsManager:
    def __init__(self, settings_file: str = "settings.json"):
        """Initialize settings manager and load settings from both .env and settings.json"""
        self.settings_file = settings_file
        # Force reload environment variables with absolute path
        env_path = os.path.join(os.getcwd(), '.env')
        load_dotenv(dotenv_path=env_path, override=True)
        
        # Load API keys from .env
        self.serpapi_key = os.getenv("SERPAPI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY")
        self.sendgrid_key = os.getenv("SENDGRID_API_KEY")
        
        # Initialize domain settings
        self.main_domain = os.getenv("MAIN_DOMAIN", "hoppenly.com")
        self.cold_email_domain = f"mail.{self.main_domain}"
        
        # Load Zoho accounts from environment variables
        self.zoho_accounts = self._load_zoho_accounts()
        
        # Load email credentials from .env
        self.response_email = os.getenv("ZOHO_EMAIL_1", f"contact@{self.main_domain}")
        self.cold_email = os.getenv("SENDGRID_FROM_EMAIL", f"outreach@{self.cold_email_domain}")
        self.email_password = os.getenv("ZOHO_PASSWORD_1")
        
        # Initialize settings dictionary
        self.settings = {
            'email_settings': {
                'email_password': self.email_password
            },
            'company_settings': {}
        }
        
        # Load other settings from settings.json
        self._load_settings()
        
        # Initialize error tracking
        self.errors = []
        
        # Log initialization once
        logger.debug("Settings manager initialized successfully")

    def _load_zoho_accounts(self) -> List[ZohoEmailAccount]:
        """Load Zoho email accounts from environment variables"""
        accounts = []
        i = 1
        while True:
            email = os.getenv(f"ZOHO_EMAIL_{i}")
            password = os.getenv(f"ZOHO_PASSWORD_{i}")
            service_type = os.getenv(f"ZOHO_SERVICE_TYPE_{i}", "Customer Support")
            
            if not email or not password:
                break
                
            account = ZohoEmailAccount(
                email=email,
                password=password,
                display_name=self.company_name if hasattr(self, 'company_name') else None,
                service_type=service_type
            )
            accounts.append(account)
            i += 1
            
        return accounts

    def _load_settings(self):
        """Load settings from JSON file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            else:
                settings = {}

            # Company settings
            self.company_name = settings.get('company_name', '')
            self.company_description = settings.get('company_description', '')
            self.company_services = settings.get('company_services', '')
            self.email_signature = settings.get('email_signature', '')
            self.company_tone = settings.get('company_tone', 'Professional')
            
            # Email settings - prefer env vars over settings file
            if not self.email_password:  # Only load from settings if not in env
                self.email_password = settings.get('email_password', '')
            if not self.response_email:  # Only load from settings if not in env
                self.response_email = settings.get('response_email', '')
            if not self.cold_email:  # Only load from settings if not in env
                self.cold_email = settings.get('cold_email', '')
            
            # Business context from AI training
            self.business_context = settings.get('business_context', {})
            
        except Exception as e:
            error_msg = f"Error loading settings: {str(e)}"
            self.errors.append(error_msg)
            logger.error(error_msg)

    def update_settings(self, **kwargs):
        """Update settings with new values and validate them."""
        try:
            # Update email settings if provided
            if 'response_email' in kwargs:
                if not kwargs['response_email']:
                    raise ValueError("Response email cannot be empty")
                if '@' not in kwargs['response_email']:
                    raise ValueError("Invalid response email format")
                self.response_email = kwargs['response_email']
                
            if 'cold_email' in kwargs:
                if not kwargs['cold_email']:
                    raise ValueError("Cold email cannot be empty")
                self.cold_email = kwargs['cold_email']
                
            if 'sendgrid_key' in kwargs:
                if not kwargs['sendgrid_key']:
                    raise ValueError("SendGrid API key cannot be empty")
                self.sendgrid_key = kwargs['sendgrid_key']
            
            # Update company settings if provided
            if 'company_name' in kwargs:
                if not kwargs['company_name']:
                    raise ValueError("Company name cannot be empty")
                self.company_name = kwargs['company_name']
                
            if 'company_description' in kwargs:
                self.company_description = kwargs['company_description']
                
            if 'company_services' in kwargs:
                self.company_services = kwargs['company_services']
                
            if 'email_signature' in kwargs:
                self.email_signature = kwargs['email_signature']
                
            if 'company_tone' in kwargs:
                # Convert to lowercase for comparison
                tone = kwargs['company_tone'].lower()
                valid_tones = ["professional", "casual", "friendly", "formal"]
                if tone not in valid_tones:
                    raise ValueError("Invalid company tone")
                self.company_tone = tone  # Store in lowercase
            
            # Update API keys if provided
            if 'serpapi_key' in kwargs:
                self.serpapi_key = kwargs['serpapi_key']
            if 'openai_key' in kwargs:
                self.openai_key = kwargs['openai_key']
            if 'rapidapi_key' in kwargs:
                self.rapidapi_key = kwargs['rapidapi_key']
            
            # Save settings after validation
            self.save_settings()
            self.errors = []  # Clear any previous errors
            
        except Exception as e:
            self.errors.append(str(e))
            raise

    def save_settings(self):
        """Save current settings to JSON file"""
        try:
            settings = {
                'company_name': self.company_name,
                'company_description': self.company_description,
                'company_services': self.company_services,
                'email_signature': self.email_signature,
                'company_tone': self.company_tone,
                'business_context': self.business_context,
                'response_email': self.response_email,
                'cold_email': self.cold_email,
                'email_password': self.email_password
            }

            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
                
        except Exception as e:
            self.errors.append(f"Error saving settings: {str(e)}")
            raise

    def verify_settings(self) -> Dict[str, bool]:
        """Verify all settings and return validation status."""
        validation = {
            'email_settings': self._verify_email_settings(),
            'company_settings': self._verify_company_settings(),
            'api_settings': self._verify_api_settings()
        }
        return validation

    def _verify_email_settings(self) -> bool:
        """Verify email-related settings."""
        # Print debug info
        print(f"Verifying email settings - password exists: {bool(self.email_password)}")
        print(f"Email settings dict: {self.settings.get('email_settings', {})}")
        
        return all([
            bool(self.response_email and '@' in self.response_email),
            bool(self.cold_email and '@' in self.cold_email),
            bool(self.sendgrid_key),
            bool(self.email_password)  # Add explicit password check
        ])

    def _verify_company_settings(self) -> bool:
        """Verify company-related settings."""
        return all([
            bool(self.company_name),
            bool(self.company_description),
            bool(self.company_services),
            bool(self.email_signature)
        ])

    def _verify_api_settings(self) -> bool:
        """Verify API-related settings."""
        return all([
            bool(self.serpapi_key),
            bool(self.openai_key),
            bool(self.rapidapi_key)
        ])

    def get_errors(self) -> List[str]:
        """Get list of current errors."""
        return self.errors

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def update_business_context(self, context):
        """Update the business context."""
        self.business_context = {
            "source": "csv",
            "csv_analysis": """
            Company Profile:
            - Name: Laval Car Logos
            - Description: We specialize in creating unique and professional car logos for automotive businesses. Our designs combine modern aesthetics with brand identity to help automotive companies stand out in the market.
            - Services: Custom car logo design, Automotive brand identity packages, Logo redesign services, Digital and physical logo formats, Brand guidelines creation
            - Target Audience: Car dealerships, Auto repair shops, Custom car builders, Automotive startups, Car enthusiast clubs
            - Value Proposition: Professional automotive-focused design expertise, Quick turnaround times, Comprehensive file formats, Industry-specific knowledge, Ongoing brand support
            - Success Stories: Helped XYZ Dealership refresh their brand identity resulting in 30% increased recognition, Created complete brand package for ABC Custom Cars in under 2 weeks
            """
        }
        self.save_settings()
        return True

    def render_settings_ui(self):
        """Render the settings UI with domain-specific configurations"""
        st.header("Email Settings")
        
        # Domain Configuration
        st.subheader("Domain Configuration")
        self.main_domain = st.text_input(
            "Main Domain",
            value=self.main_domain,
            help="Your main domain (e.g., hoppenly.com)"
        )
        st.info(f"Cold Email Domain: mail.{self.main_domain}")
        
        # SendGrid Settings (Cold Emails)
        st.subheader("SendGrid Settings (Cold Email Sending)")
        self.sendgrid_key = st.text_input(
            "SendGrid API Key",
            value=self.sendgrid_key,
            type="password",
            help="API key from SendGrid"
        )
        self.cold_email = st.text_input(
            "Cold Email Address",
            value=self.cold_email,
            help=f"Your cold email address (e.g., outreach@mail.{self.main_domain})"
        )
        
        # Zoho Settings (Response Emails)
        st.subheader("Zoho Settings (Email Responses)")
        self.response_email = st.text_input(
            "Response Email Address",
            value=self.response_email,
            help=f"Your response email address (e.g., contact@{self.main_domain})"
        )
        self.email_password = st.text_input(
            "Zoho Email Password",
            value=self.email_password,
            type="password",
            help="Password for your Zoho email account"
        )
        
        # Company Settings
        st.subheader("Company Settings")
        self.company_name = st.text_input(
            "Company Name",
            value=self.company_name
        )
        self.company_description = st.text_area(
            "Company Description",
            value=self.company_description
        )
        self.company_services = st.text_area(
            "Company Services",
            value=self.company_services
        )
        self.email_signature = st.text_area(
            "Email Signature",
            value=self.email_signature
        )
        self.company_tone = st.selectbox(
            "Communication Tone",
            options=["Professional", "Casual", "Friendly", "Formal"],
            index=["Professional", "Casual", "Friendly", "Formal"].index(self.company_tone)
        )

        # Save Settings Button
        if st.button("Save Settings"):
            try:
                self._validate_settings()
                self.save_settings()
                st.success("✅ Settings saved successfully!")
            except Exception as e:
                st.error(f"❌ Error saving settings: {str(e)}")

    def _validate_settings(self):
        """Validate all settings before saving"""
        errors = []
        
        # Validate domain settings
        if not self.main_domain:
            errors.append("Main domain is required")
        
        # Validate email addresses
        if not self._is_valid_email(self.response_email):
            errors.append("Invalid response email address")
        if not self._is_valid_email(self.cold_email):
            errors.append("Invalid cold email address")
            
        # Validate email domains
        if self.response_email and '@' in self.response_email:
            response_domain = self.response_email.split('@')[1]
            if response_domain != self.main_domain:
                errors.append("Response email must use main domain")
        
        if self.cold_email and '@' in self.cold_email:
            cold_domain = self.cold_email.split('@')[1]
            if cold_domain != f"mail.{self.main_domain}":
                errors.append("Cold email must use mail subdomain")
            
        # Validate required credentials
        if not self.sendgrid_key:
            errors.append("SendGrid API key is required")
        if not self.email_password:
            errors.append("Zoho email password is required")
            
        # Validate company settings
        if not self.company_name:
            errors.append("Company name is required")
            
        if errors:
            raise ValueError("\n".join(errors))
            
        return True

    def _is_valid_email(self, email):
        """Validate email address format"""
        if not email:
            return False
        if '@' not in email:
            return False
        if '.' not in email.split('@')[1]:
            return False
        return True 