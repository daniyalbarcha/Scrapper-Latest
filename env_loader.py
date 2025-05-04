"""
Simple environment variable loader that doesn't rely on python-dotenv
This is a fallback solution for systems with encoding issues
"""

import os
import re
from typing import Dict

def load_environment_vars(env_path: str = '.env') -> Dict[str, str]:
    """
    Load environment variables from file without using dotenv
    This is a very simple implementation that is robust against encoding issues
    """
    # Default environment variables if file can't be loaded
    default_vars = {
        'SERPAPI_API_KEY': '',
        'OPENAI_API_KEY': '',
        'RAPIDAPI_KEY': '',
        'SENDGRID_API_KEY': '',
        'MAIN_DOMAIN': '',
        'ZOHO_EMAIL_1': '',
        'ZOHO_PASSWORD_1': '',
        'ZOHO_SERVICE_TYPE_1': '',
        'SENDGRID_FROM_EMAIL': '',
        'SENDGRID_FROM_NAME': ''
    }
    
    loaded_vars = {}
    
    # Try to load from file
    try:
        # 1. Try UTF-8 encoding first
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 2. If UTF-8 fails, try with latin-1 (which should always work, but might misinterpret characters)
            with open(env_path, 'r', encoding='latin-1') as f:
                content = f.read()
                
        # Parse content line by line
        for line in content.splitlines():
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
                
            # Parse key=value format
            match = re.match(r'^([A-Za-z0-9_]+)=(.*)$', line)
            if match:
                key, value = match.groups()
                # Remove quotes if present
                value = value.strip('"\'')
                # Set environment variable and add to loaded vars
                os.environ[key] = value
                loaded_vars[key] = value
                
    except Exception as e:
        print(f"Warning: Could not load environment variables from {env_path}: {e}")
        print("Using default empty values")
    
    # Fill in any missing variables with defaults
    for key, value in default_vars.items():
        if key not in loaded_vars:
            os.environ[key] = value
            loaded_vars[key] = value
    
    return loaded_vars

def ensure_env_file_exists(env_path: str = '.env'):
    """Ensure an .env file exists with template values"""
    if not os.path.exists(env_path):
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write("# API Keys\n")
            f.write("SERPAPI_API_KEY=\n")
            f.write("OPENAI_API_KEY=\n")
            f.write("RAPIDAPI_KEY=\n")
            f.write("SENDGRID_API_KEY=\n\n")
            f.write("# Domain Settings\n")
            f.write("MAIN_DOMAIN=\n\n")
            f.write("# Zoho Email Settings\n")
            f.write("ZOHO_EMAIL_1=\n")
            f.write("ZOHO_PASSWORD_1=\n")
            f.write("ZOHO_SERVICE_TYPE_1=\n\n")
            f.write("# SendGrid Settings\n")
            f.write("SENDGRID_FROM_EMAIL=\n")
            f.write("SENDGRID_FROM_NAME=\n") 