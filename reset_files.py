import os
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def reset_json_files():
    """Reset all JSON files to empty structures with proper UTF-8 encoding."""
    # 1. Define all JSON files that need to be reset
    files_to_reset = {
        'settings.json': {},
        'session_state.json': {},
        'email_replies.json': [],
        'test_profile.json': {},
        'processed_messages.txt': ''  # Not JSON but needs UTF-8 encoding
    }
    
    # 2. Reset each file
    for filename, default_content in files_to_reset.items():
        try:
            # Delete the file if it exists
            if os.path.exists(filename):
                os.remove(filename)
                logger.info(f"Deleted existing file: {filename}")
            
            # Create a new file with proper UTF-8 encoding
            if filename.endswith('.json'):
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(default_content, f, ensure_ascii=False)
            else:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(default_content)
                    
            logger.info(f"Created new file with proper UTF-8 encoding: {filename}")
        
        except Exception as e:
            logger.error(f"Error resetting file {filename}: {str(e)}")
    
    logger.info("All JSON files have been reset with proper UTF-8 encoding")

if __name__ == "__main__":
    print("Starting file reset utility...")
    reset_json_files()
    print("File reset complete! The application should now run without encoding errors.")
    print("If you continue to experience issues, please report them with the exact error message.") 