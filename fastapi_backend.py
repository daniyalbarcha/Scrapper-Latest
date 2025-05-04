from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime
import json
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from zoho_mail_handler import ZohoMailHandler
from settings_manager import SettingsManager
import logging

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize settings and Zoho handler
settings_manager = SettingsManager()
zoho_handler = ZohoMailHandler(
    openai_api_key=settings_manager.openai_key,
    accounts=settings_manager.zoho_accounts
)

# File to store email replies
REPLIES_FILE = "email_replies.json"

# Configure scheduler with better defaults
jobstores = {
    'default': MemoryJobStore()
}
executors = {
    'default': ThreadPoolExecutor(20)
}
job_defaults = {
    'coalesce': True,  # Combine multiple waiting jobs
    'max_instances': 1,  # Only one instance of the job can run at a time
    'misfire_grace_time': 30  # Allow jobs to fire up to 30 seconds late
}

# Initialize scheduler with configuration
scheduler = BackgroundScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
    timezone='UTC'
)

def load_replies():
    """Load existing replies from file."""
    try:
        with open(REPLIES_FILE, 'r', encoding='utf-8') as f:
            replies = json.load(f)
            # Convert timestamps to proper format
            for reply in replies:
                if 'timestamp' in reply and isinstance(reply['timestamp'], str):
                    try:
                        # Parse timestamp and convert to ISO format
                        dt = datetime.fromisoformat(reply['timestamp'].replace(',', '.'))
                        reply['timestamp'] = dt.isoformat()
                    except ValueError:
                        pass
            return replies
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_replies(replies):
    """Save replies to file."""
    # Ensure all timestamps are in ISO format
    for reply in replies:
        if 'timestamp' in reply and isinstance(reply['timestamp'], str):
            try:
                # Parse timestamp and convert to ISO format
                dt = datetime.fromisoformat(reply['timestamp'].replace(',', '.'))
                reply['timestamp'] = dt.isoformat()
            except ValueError:
                pass
    
    with open(REPLIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(replies, f)

def check_emails():
    """Check for new emails and update storage."""
    try:
        print(f"Running email check at {datetime.now()}")
        logging.info(f"Running email check at {datetime.now()}")
        processed = zoho_handler.process_unread_emails()
        if processed:
            # Format timestamps for new replies
            for reply in processed:
                if 'timestamp' in reply and isinstance(reply['timestamp'], str):
                    try:
                        # Parse timestamp and convert to ISO format
                        dt = datetime.fromisoformat(reply['timestamp'].replace(',', '.'))
                        reply['timestamp'] = dt.isoformat()
                    except ValueError:
                        pass
            
            existing_replies = load_replies()
            existing_replies.extend(processed)
            save_replies(existing_replies)
            print(f"Processed {len(processed)} new emails at {datetime.now()}")
            logging.info(f"Processed {len(processed)} new emails at {datetime.now()}")
        else:
            print("No new emails to process")
            logging.info("No new emails to process")
    except Exception as e:
        print(f"Error checking emails: {e}")
        logging.error(f"Error in check_emails job: {e}")

# Remove the initial scheduler start since we'll handle it in startup event
try:
    scheduler.add_job(
        check_emails,
        'interval',
        minutes=2,
        id='check_emails',
        replace_existing=True
    )
    print("Email check job added to scheduler")
    logging.info("Email check job added to scheduler")
except Exception as e:
    error_msg = f"Error adding email check job: {e}"
    print(error_msg)
    logging.error(error_msg)

@app.on_event("startup")
async def startup_event():
    """Ensure scheduler is running when FastAPI starts"""
    try:
        if not scheduler.running:
            # Make sure the job is added
            if not scheduler.get_job('check_emails'):
                scheduler.add_job(
                    check_emails,
                    'interval',
                    minutes=2,
                    id='check_emails',
                    replace_existing=True
                )
                print("Email check job added during startup")
                logging.info("Email check job added during startup")
            
            # Start the scheduler
            scheduler.start()
            print("Scheduler started during startup")
            logging.info("Scheduler started during startup")
            
            # Run initial check
            check_emails()
            print("Initial email check completed")
            logging.info("Initial email check completed")
    except Exception as e:
        error_msg = f"Error starting scheduler during startup: {e}"
        print(error_msg)
        logging.error(error_msg)

@app.get("/email_replies")
async def get_email_replies():
    """Get all processed email replies."""
    return load_replies()

@app.post("/check_now")
async def check_now(background_tasks: BackgroundTasks):
    """Manually trigger email check."""
    background_tasks.add_task(check_emails)
    return {"message": "Email check initiated"}

@app.get("/scheduler_status")
async def get_scheduler_status():
    """Get the current status of the scheduler."""
    return {
        "running": scheduler.running,
        "next_run": scheduler.get_job('check_emails').next_run_time.isoformat() if scheduler.get_job('check_emails') else None,
        "job_count": len(scheduler.get_jobs())
    }

@app.post("/restart_scheduler")
async def restart_scheduler():
    """Restart the scheduler if it's not running."""
    try:
        if not scheduler.running:
            scheduler.start()
            return {"message": "Scheduler restarted successfully"}
        return {"message": "Scheduler is already running"}
    except Exception as e:
        return {"error": f"Failed to restart scheduler: {str(e)}"}

@app.on_event("shutdown")
async def shutdown_event():
    """Ensure scheduler is properly shut down"""
    try:
        if scheduler.running:
            scheduler.shutdown()
            print("Scheduler shut down successfully")
            logging.info("Scheduler shut down successfully")
    except Exception as e:
        error_msg = f"Error shutting down scheduler: {e}"
        print(error_msg)
        logging.error(error_msg)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 