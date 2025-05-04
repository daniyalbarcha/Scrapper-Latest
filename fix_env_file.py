import os
import io
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_env_file():
    """Create a properly encoded .env file."""
    # Check if .env file exists
    if os.path.exists('.env'):
        logger.info("Found existing .env file")
        
        # Try to read it with different encodings
        content = None
        for encoding in ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1']:
            try:
                with open('.env', 'r', encoding=encoding) as f:
                    content = f.read()
                logger.info(f"Successfully read .env file with {encoding} encoding")
                break
            except UnicodeError:
                logger.warning(f"Failed to read with {encoding} encoding")
        
        # Backup old file
        if os.path.exists('.env'):
            os.rename('.env', '.env.bak')
            logger.info("Backed up original .env file to .env.bak")
    else:
        logger.info("No existing .env file found")
        content = """# API Keys
SERPAPI_API_KEY=
OPENAI_API_KEY=
RAPIDAPI_KEY=
SENDGRID_API_KEY=

# Domain Settings
MAIN_DOMAIN=

# Zoho Email Settings
ZOHO_EMAIL_1=
ZOHO_PASSWORD_1=
ZOHO_SERVICE_TYPE_1=

# SendGrid Settings
SENDGRID_FROM_EMAIL=
SENDGRID_FROM_NAME=
"""
    
    # Create new .env file with proper UTF-8 encoding
    with open('.env', 'w', encoding='utf-8') as f:
        if content:
            f.write(content)
        else:
            # Create empty template if we couldn't read the original
            f.write("""# API Keys
SERPAPI_API_KEY=
OPENAI_API_KEY=
RAPIDAPI_KEY=
SENDGRID_API_KEY=

# Domain Settings
MAIN_DOMAIN=

# Zoho Email Settings
ZOHO_EMAIL_1=
ZOHO_PASSWORD_1=
ZOHO_SERVICE_TYPE_1=

# SendGrid Settings
SENDGRID_FROM_EMAIL=
SENDGRID_FROM_NAME=
""")
    
    logger.info("Created new .env file with proper UTF-8 encoding")
    print("You'll need to fill in your API keys and settings in the new .env file")

if __name__ == "__main__":
    print("Fixing .env file encoding issues...")
    fix_env_file()
    print("Done! Your .env file should now have proper UTF-8 encoding.")
    print("If you had an existing .env file, it was backed up to .env.bak")
    print("Please check your .env file and fill in your API keys and settings if needed.") 