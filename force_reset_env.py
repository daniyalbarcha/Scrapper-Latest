"""
Emergency fix for corrupted .env files
This script will completely REPLACE your existing .env file with a new one
"""

import os
import sys
import shutil
from datetime import datetime

def main():
    """Forcefully replace corrupted .env file"""
    print("=" * 60)
    print("EMERGENCY .ENV FILE RESET TOOL")
    print("=" * 60)
    print("\nWARNING: This will REPLACE your existing .env file!")
    print("Your old file will be backed up with a timestamp.\n")
    
    # Check if .env exists
    if os.path.exists('.env'):
        # Create backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_path = f".env.bak.{timestamp}"
        try:
            shutil.copy2('.env', backup_path)
            print(f"✅ Backup created: {backup_path}")
        except Exception as e:
            print(f"⚠️ Could not create backup: {e}")
    
    # Get API keys
    print("\nPlease enter your API keys:")
    openai_key = input("OpenAI API Key: ").strip()
    serpapi_key = input("SerpAPI Key: ").strip()
    rapidapi_key = input("RapidAPI Key: ").strip()
    
    # Create new .env file from scratch
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write("# API Keys\n")
            f.write(f"OPENAI_API_KEY={openai_key}\n")
            f.write(f"SERPAPI_API_KEY={serpapi_key}\n")
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
        
        print("\n✅ New .env file created successfully with UTF-8 encoding.")
        
        # Verify the file was created correctly
        try:
            with open('.env', 'r', encoding='utf-8') as f:
                content = f.read()
                if "OPENAI_API_KEY" in content and openai_key in content:
                    print("✅ File verification successful.")
                else:
                    print("⚠️ File verification failed. Keys may not be properly set.")
        except Exception as e:
            print(f"⚠️ Could not verify new file: {e}")
        
        # Set environment variables for current session
        os.environ["OPENAI_API_KEY"] = openai_key
        os.environ["SERPAPI_API_KEY"] = serpapi_key
        os.environ["RAPIDAPI_KEY"] = rapidapi_key
        
        print("\n✅ Environment variables set for current session.")
        print("\nYou should now be able to run the application without encoding issues.")
        print("If you still experience problems, please restart your system.")
        
    except Exception as e:
        print(f"\n❌ Error creating new .env file: {e}")
        print("Please try running this script with administrator privileges.")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main() 