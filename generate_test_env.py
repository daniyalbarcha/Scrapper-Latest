"""
Test script to check environment variables and manually set API keys
Run this script on the problematic system to diagnose and fix issues
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('env_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check environment variables and SSL settings"""
    logger.info("=" * 60)
    logger.info("ENVIRONMENT DIAGNOSTIC TOOL")
    logger.info("=" * 60)
    
    # Check Python version
    logger.info(f"Python version: {sys.version}")
    
    # Check SSL settings
    try:
        import ssl
        logger.info(f"SSL version: {ssl.OPENSSL_VERSION}")
        logger.info(f"SSL default context verify mode: {ssl._create_default_https_context().verify_mode}")
    except Exception as e:
        logger.error(f"Error checking SSL: {e}")
    
    # Check critical environment variables
    critical_keys = ['OPENAI_API_KEY', 'SERPAPI_API_KEY', 'RAPIDAPI_KEY']
    for key in critical_keys:
        value = os.environ.get(key, '')
        if value:
            logger.info(f"{key}: Found ({len(value)} chars)")
        else:
            logger.warning(f"{key}: NOT FOUND")
    
    # Try importing and using our custom env_loader
    try:
        import env_loader
        logger.info("Successfully imported env_loader")
        
        # Check if .env file exists
        if os.path.exists('.env'):
            logger.info(".env file exists")
            try:
                with open('.env', 'r', encoding='utf-8') as f:
                    content = f.read()
                    logger.info(f".env file size: {len(content)} chars")
                    for key in critical_keys:
                        if key in content:
                            logger.info(f"{key} found in .env file")
                        else:
                            logger.warning(f"{key} NOT found in .env file")
            except Exception as e:
                logger.error(f"Error reading .env file: {e}")
        else:
            logger.warning(".env file does not exist")
            
        # Load environment variables
        loaded_vars = env_loader.load_environment_vars()
        logger.info(f"Loaded {len(loaded_vars)} environment variables")
        
    except Exception as e:
        logger.error(f"Error with env_loader: {e}")
    
    logger.info("=" * 60)
    logger.info("DIAGNOSTIC COMPLETE")
    logger.info("=" * 60)

def set_api_keys():
    """Manually set API keys in the .env file"""
    logger.info("=" * 60)
    logger.info("MANUAL API KEY SETUP")
    logger.info("=" * 60)
    
    # Prompt for API keys
    openai_key = input("Enter your OpenAI API key: ").strip()
    serpapi_key = input("Enter your SerpAPI key: ").strip()
    rapidapi_key = input("Enter your RapidAPI key: ").strip()
    
    keys_dict = {
        "OPENAI_API_KEY": openai_key,
        "SERPAPI_API_KEY": serpapi_key,
        "RAPIDAPI_KEY": rapidapi_key
    }
    
    # Read existing .env file
    env_content = ""
    if os.path.exists('.env'):
        try:
            with open('.env', 'r', encoding='utf-8') as f:
                env_content = f.read()
        except UnicodeDecodeError:
            try:
                with open('.env', 'r', encoding='latin-1') as f:
                    env_content = f.read()
            except Exception:
                logger.warning("Could not read existing .env file, creating new one")
    
    # Update or create .env file
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            # Write existing content first if any
            if env_content:
                # Update existing keys
                for key, value in keys_dict.items():
                    if value:  # Only update if a value was provided
                        # Check if key exists in file
                        if f"{key}=" in env_content:
                            # Replace existing key
                            lines = []
                            for line in env_content.splitlines():
                                if line.strip().startswith(f"{key}="):
                                    lines.append(f"{key}={value}")
                                else:
                                    lines.append(line)
                            env_content = "\n".join(lines)
                        else:
                            # Add key if it doesn't exist
                            env_content += f"\n{key}={value}"
                
                f.write(env_content)
                
            else:
                # Create new .env file with template
                f.write("# API Keys\n")
                f.write(f"SERPAPI_API_KEY={serpapi_key}\n")
                f.write(f"OPENAI_API_KEY={openai_key}\n")
                f.write(f"RAPIDAPI_KEY={rapidapi_key}\n")
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
        
        logger.info("API keys have been set successfully")
        
        # Set the keys in the current environment as well
        for key, value in keys_dict.items():
            if value:
                os.environ[key] = value
                logger.info(f"Set {key} in current environment")
                
    except Exception as e:
        logger.error(f"Error setting API keys: {e}")
    
    logger.info("=" * 60)
    logger.info("API KEY SETUP COMPLETE")
    logger.info("=" * 60)

def main():
    """Main function to run the diagnostic and setup tool"""
    print("=" * 60)
    print("INSTAGRAM PRO SCRAPPER - ENVIRONMENT DIAGNOSTIC")
    print("=" * 60)
    print("\nThis tool will help diagnose and fix environment issues.")
    print("Results will be logged to 'env_test.log'.\n")
    
    while True:
        print("\nChoose an option:")
        print("1. Check environment & diagnose issues")
        print("2. Set API keys manually")
        print("3. Exit\n")
        
        choice = input("Enter your choice (1-3): ").strip()
        
        if choice == '1':
            check_environment()
        elif choice == '2':
            set_api_keys()
        elif choice == '3':
            print("\nExiting. Check 'env_test.log' for detailed results.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main() 