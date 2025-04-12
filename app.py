from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import logging
from settings_manager import SettingsManager
from sendgrid_handler import SendGridHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_responses.log'),
        logging.StreamHandler()
    ]
)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize settings and email handler
settings = SettingsManager()
email_handler = SendGridHandler(
    api_key=settings.get_setting('sendgrid_api_key'),
    from_email=settings.get_setting('sendgrid_from_email'),
    from_name=settings.get_setting('sendgrid_from_name'),
    reply_to_email=settings.get_setting('reply_to_email')
)

@app.post("/inbound")
async def handle_inbound_email(request: Request):
    """Handle inbound emails from SendGrid's parse webhook"""
    try:
        # Get form data from request
        form_data = await request.form()
        email_data = dict(form_data)
        
        # Log received email
        logging.info(f"Received inbound email from: {email_data.get('from')}")
        
        # Handle email and generate response
        success = email_handler.handle_inbound_email(email_data)
        
        if success:
            logging.info("Successfully sent response email")
            return {"status": "success"}
        else:
            logging.error("Failed to send response email")
            return {"status": "error", "message": "Failed to send response"}
            
    except Exception as e:
        logging.error(f"Error processing inbound email: {str(e)}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 