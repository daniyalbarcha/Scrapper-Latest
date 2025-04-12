from dataclasses import dataclass
import logging
import imaplib
import smtplib
import dns.resolver
from typing import Dict, Optional
from datetime import datetime

@dataclass
class ZohoEmailAccount:
    email: str
    password: str
    display_name: str
    service_type: str

class EmailServerConfig:
    """Configuration class for email server settings"""
    def __init__(self, 
                 imap_server: str = "imappro.zoho.com",
                 smtp_server: str = "smtppro.zoho.com",
                 smtp_port: int = 465,
                 imap_port: int = 993,
                 use_ssl: bool = True):
        self.imap_server = imap_server
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.imap_port = imap_port
        self.use_ssl = use_ssl

class DomainVerification:
    """Handles domain verification and DNS checks"""
    @staticmethod
    def verify_spf_record(domain: str) -> bool:
        try:
            answers = dns.resolver.resolve(domain, 'TXT')
            for rdata in answers:
                for txt_string in rdata.strings:
                    if txt_string.startswith(b'v=spf1'):
                        return b'include:zohomail.com' in txt_string or b'include:one.zoho.com' in txt_string
            return False
        except Exception as e:
            logging.error(f"SPF verification failed for {domain}: {str(e)}")
            return False

    @staticmethod
    def verify_dkim_record(domain: str, selector: str) -> bool:
        try:
            dkim_domain = f"{selector}._domainkey.{domain}"
            answers = dns.resolver.resolve(dkim_domain, 'TXT')
            return len(answers) > 0
        except Exception as e:
            logging.error(f"DKIM verification failed for {domain}: {str(e)}")
            return False

    @staticmethod
    def verify_mx_records(domain: str) -> bool:
        try:
            answers = dns.resolver.resolve(domain, 'MX')
            return any('zoho' in str(rdata.exchange).lower() for rdata in answers)
        except Exception as e:
            logging.error(f"MX verification failed for {domain}: {str(e)}")
            return False

class ZohoEmailAccount:
    def __init__(self, 
                 email: str, 
                 password: str, 
                 display_name: str, 
                 service_type: str,
                 server_config: Optional[EmailServerConfig] = None,
                 domain_settings: Optional[Dict] = None):
        """
        Initialize a Zoho email account with domain-specific settings.
        
        Args:
            email: Email address
            password: Email password
            display_name: Display name for the email
            service_type: Type of service this account handles
            server_config: Custom email server configuration
            domain_settings: Domain-specific settings including:
                           - dkim_selector: DKIM selector name
                           - spf_record: SPF record verification status
                           - dkim_verified: DKIM verification status
                           - mx_verified: MX record verification status
        """
        self.email = email
        self.password = password
        self.display_name = display_name
        self.service_type = service_type
        self.domain = email.split('@')[1]
        self.server_config = server_config or EmailServerConfig()
        self.domain_settings = domain_settings or {}
        self._initialize_domain_settings()

    def _initialize_domain_settings(self):
        """Initialize and verify domain settings if not provided"""
        if 'dkim_selector' not in self.domain_settings:
            self.domain_settings['dkim_selector'] = 'zoho'
        
        # Perform verification if not already done
        if not self.domain_settings.get('verified', False):
            self.verify_domain_setup()

    def verify_domain_setup(self) -> Dict[str, bool]:
        """
        Verify domain setup including SPF, DKIM, and MX records.
        Returns dict with verification status.
        """
        spf_valid = DomainVerification.verify_spf_record(self.domain)
        dkim_valid = DomainVerification.verify_dkim_record(
            self.domain, 
            self.domain_settings['dkim_selector']
        )
        mx_valid = DomainVerification.verify_mx_records(self.domain)

        self.domain_settings.update({
            'spf_valid': spf_valid,
            'dkim_valid': dkim_valid,
            'mx_valid': mx_valid,
            'verified': True,
            'last_verified': datetime.now().isoformat()
        })

        return {
            'spf_valid': spf_valid,
            'dkim_valid': dkim_valid,
            'mx_valid': mx_valid,
            'domain': self.domain
        }

    def test_connection(self) -> Dict[str, bool]:
        """
        Test IMAP and SMTP connections for the account.
        Returns dict with connection test results.
        """
        results = {
            'imap_connection': False,
            'smtp_connection': False,
            'errors': []
        }

        # Test IMAP connection
        try:
            if self.server_config.use_ssl:
                imap = imaplib.IMAP4_SSL(
                    self.server_config.imap_server,
                    self.server_config.imap_port
                )
            else:
                imap = imaplib.IMAP4(
                    self.server_config.imap_server,
                    self.server_config.imap_port
                )
            imap.login(self.email, self.password)
            imap.logout()
            results['imap_connection'] = True
        except Exception as e:
            results['errors'].append(f"IMAP Error: {str(e)}")

        # Test SMTP connection
        try:
            if self.server_config.use_ssl:
                smtp = smtplib.SMTP_SSL(
                    self.server_config.smtp_server,
                    self.server_config.smtp_port
                )
            else:
                smtp = smtplib.SMTP(
                    self.server_config.smtp_server,
                    self.server_config.smtp_port
                )
            smtp.login(self.email, self.password)
            smtp.quit()
            results['smtp_connection'] = True
        except Exception as e:
            results['errors'].append(f"SMTP Error: {str(e)}")

        return results 