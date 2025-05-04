#!/usr/bin/env python3
"""
Emergency .env file fixer for Instagram Pro Scrapper
Run this script directly before running the main application if you're experiencing encoding issues
"""

import os
import sys
import shutil
from datetime import datetime

# Utility function to create a clean template .env file
def create_clean_env_file(file_path):
    try:
        print(f"Creating clean .env template at {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
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
        print("✅ Clean .env file created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")
        return False

def fix_json_files():
    """Fix any JSON files that might be corrupted"""
    json_files = [
        "session_state.json", 
        "settings.json",
        "email_replies.json"
    ]
    
    for json_file in json_files:
        if os.path.exists(json_file):
            try:
                # Try to read the file
                with open(json_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Test successful read
                print(f"✅ {json_file} is already valid UTF-8")
            except UnicodeDecodeError:
                # Backup the file
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                backup_path = f"{json_file}.corrupted.{timestamp}"
                try:
                    shutil.copy2(json_file, backup_path)
                    print(f"📁 Backed up corrupted {json_file} to {backup_path}")
                except Exception as e:
                    print(f"❌ Could not backup {json_file}: {e}")
                
                # Create a new empty JSON file
                try:
                    if json_file == "session_state.json" or json_file == "settings.json":
                        with open(json_file, 'w', encoding='utf-8') as f:
                            f.write("{}\n")
                    else:  # email_replies.json
                        with open(json_file, 'w', encoding='utf-8') as f:
                            f.write("[]\n")
                    print(f"✅ Created new empty {json_file}")
                except Exception as e:
                    print(f"❌ Error creating new {json_file}: {e}")

def main():
    """Main function to fix environment issues"""
    print("=" * 60)
    print("Instagram Pro Scrapper - Emergency Environment Fix Tool")
    print("=" * 60)
    print("\nThis tool will fix encoding issues with your configuration files.")
    
    # Check if .env file exists
    env_path = '.env'
    if os.path.exists(env_path):
        print(f"\nFound existing .env file")
        
        try:
            # Try to read with UTF-8 to check if valid
            with open(env_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if '=' in content:
                    print("✅ .env file appears to be valid UTF-8 and contains configuration")
                    should_replace = input("\nWould you like to replace it with a clean template anyway? (y/N): ").lower().strip() == 'y'
                else:
                    print("⚠️ .env file doesn't contain any configuration")
                    should_replace = True
        except UnicodeDecodeError:
            print("❌ .env file is corrupted (encoding issues)")
            should_replace = True
        except Exception as e:
            print(f"❌ Error reading .env file: {e}")
            should_replace = True
            
        if should_replace:
            # Backup the existing file
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            backup_path = f"{env_path}.bak.{timestamp}"
            try:
                shutil.copy2(env_path, backup_path)
                print(f"📁 Backed up existing .env file to {backup_path}")
            except Exception as e:
                print(f"❌ Could not backup .env file: {e}")
                
            # Remove the old file
            try:
                os.remove(env_path)
            except Exception as e:
                print(f"❌ Could not remove old .env file: {e}")
                
            # Create a fresh file
            create_clean_env_file(env_path)
    else:
        print("\nNo .env file found, creating a new one")
        create_clean_env_file(env_path)
    
    # Fix other potential problematic files
    print("\nChecking other configuration files...")
    fix_json_files()
    
    print("\n" + "=" * 60)
    print("✅ Environment fix completed!")
    print("=" * 60)
    print("\nYou can now run the Instagram Pro Scrapper application")
    print("Remember to add your API keys to the .env file before starting")
    
if __name__ == "__main__":
    main() 