"""
Simple environment variable loader that doesn't rely on python-dotenv
This is a fallback solution for systems with encoding issues
"""

import os
import re
from typing import Dict
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('env_loader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_environment_vars(env_path: str = '.env', debug: bool = True) -> Dict[str, str]:
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
    
    # Check if any of these keys already exist in the environment
    for key in default_vars.keys():
        env_value = os.getenv(key)
        if env_value:
            if debug:
                logger.info(f"Using existing environment variable: {key}")
            loaded_vars[key] = env_value
    
    # Try to load from file
    try:
        # 1. Try UTF-8 encoding first
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if debug:
                    logger.info(f"Successfully read {env_path} with UTF-8 encoding")
        except UnicodeDecodeError:
            # 2. If UTF-8 fails, try with latin-1 (which should always work, but might misinterpret characters)
            with open(env_path, 'r', encoding='latin-1') as f:
                content = f.read()
                if debug:
                    logger.info(f"Read {env_path} with latin-1 encoding (fallback)")
        
        # Get file contents for debugging
        if debug:
            logger.info(f"Contents: {len(content)} characters, contains '=' sign: {'=' in content}")
                
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
                
                # Skip empty values
                if not value:
                    continue
                    
                # Set environment variable and add to loaded vars
                os.environ[key] = value
                loaded_vars[key] = value
                if debug:
                    logger.info(f"Loaded environment variable: {key} with {len(value)} characters")
                
    except Exception as e:
        logger.warning(f"Warning: Could not load environment variables from {env_path}: {e}")
        logger.info("Using default empty values or existing environment variables")
    
    # Fill in any missing variables with defaults
    for key, value in default_vars.items():
        if key not in loaded_vars:
            os.environ[key] = value
            loaded_vars[key] = value
            
    # Special handling for critical API keys
    critical_keys = ['OPENAI_API_KEY', 'SERPAPI_API_KEY', 'RAPIDAPI_KEY']
    for key in critical_keys:
        if not loaded_vars.get(key):
            logger.warning(f"CRITICAL: No value found for {key}")
        else:
            logger.info(f"API key found for {key}")
    
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
        logger.info(f"Created new .env template at {env_path}")
    else:
        logger.info(f".env file already exists at {env_path}") 