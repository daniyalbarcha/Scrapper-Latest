import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from zoho_mail_handler import ZohoMailHandler, ZohoEmailAccount
import os
from dotenv import load_dotenv
import requests
from settings_manager import SettingsManager

def load_zoho_accounts():
    """Load Zoho email accounts from environment variables."""
    accounts = []
    for i in range(1, 4):  # For 3 accounts
        email = os.getenv(f"ZOHO_EMAIL_{i}")
        password = os.getenv(f"ZOHO_PASSWORD_{i}")
        if email and password:
            accounts.append(
                ZohoEmailAccount(
                    email=email,
                    password=password,
                    display_name=f"Service Account {i}",
                    service_type=os.getenv(f"ZOHO_SERVICE_TYPE_{i}", "General")
                )
            )
    return accounts

def initialize_zoho_handler():
    """Initialize Zoho mail handler with settings."""
    try:
        settings = SettingsManager()
        handler = ZohoMailHandler(
            openai_api_key=settings.openai_key,
            accounts=settings.zoho_accounts
        )
        return handler
    except Exception as e:
        st.error(f"Failed to initialize Zoho handler: {str(e)}")
        return None

def get_email_replies():
    """Get email replies from the backend API."""
    try:
        response = requests.get("http://localhost:8002/email_replies", verify=False)
        return response.json()
    except Exception as e:
        print(f"Error getting email replies: {e}")
        return []

def get_scheduler_status():
    """Get scheduler status from the backend API."""
    try:
        response = requests.get("http://localhost:8002/scheduler_status", verify=False)
        status = response.json()
        # Add last check time if available
        if 'next_run' in status:
            status['last_check'] = (
                datetime.fromisoformat(status['next_run']) - timedelta(minutes=2)
            ).isoformat()
        return status
    except Exception as e:
        print(f"Error getting scheduler status: {e}")
        return None

def restart_scheduler():
    """Restart the scheduler via backend API."""
    try:
        response = requests.post("http://localhost:8002/restart_scheduler", verify=False)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def trigger_email_check():
    """Trigger an immediate email check."""
    try:
        response = requests.post("http://localhost:8002/check_now", verify=False)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def main():
    st.set_page_config(page_title="Zoho Mail Monitor", page_icon="📧", layout="wide")
    
    # Load environment variables
    load_dotenv()
    
    # Initialize session state
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = False
    if 'last_check_time' not in st.session_state:
        st.session_state.last_check_time = None
    if 'error_count' not in st.session_state:
        st.session_state.error_count = 0

    # Header
    st.title("📧 Zoho Mail Monitor")
    st.markdown("---")

    # Initialize Zoho handler
    handler = initialize_zoho_handler()
    if not handler:
        st.stop()

    # Create two columns for the main content
    col1, col2 = st.columns([2, 1])

    with col2:
        st.header("System Status")
        
        # Show scheduler status
        scheduler_status = get_scheduler_status()
        if scheduler_status:
            status_color = "🟢" if scheduler_status['running'] else "🔴"
            st.write(f"Scheduler Status: {status_color}")
            
            if scheduler_status.get('next_run'):
                next_run = datetime.fromisoformat(scheduler_status['next_run'])
                st.write(f"Next Check: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                
                if scheduler_status.get('last_check'):
                    last_check = datetime.fromisoformat(scheduler_status['last_check'])
                    st.write(f"Last Check: {last_check.strftime('%Y-%m-%d %H:%M:%S')}")
            
            st.write(f"Active Jobs: {scheduler_status.get('job_count', 0)}")
            
            if not scheduler_status['running']:
                if st.button("🔄 Restart Scheduler"):
                    result = restart_scheduler()
                    if 'error' not in result:
                        st.success("Scheduler restarted successfully")
                        time.sleep(2)  # Wait for scheduler to start
                        st.rerun()  # Refresh the page
                    else:
                        st.error(f"Failed to restart scheduler: {result['error']}")
        
        # Show account status
        st.markdown("---")
        st.subheader("Account Status")
        for email in handler.accounts:
            status = handler.connect_imap(email)
            status_color = "🟢" if status else "🔴"
            st.text(f"{email}: {status_color}")
            
            # Show detailed connection info
            if status:
                try:
                    conn_status = handler.check_connection()
                    account_status = conn_status[email]
                    st.markdown(
                        f"""
                        - IMAP: {"✓" if account_status['imap_connected'] else "✗"}
                        - SMTP: {"✓" if account_status['smtp_connected'] else "✗"}
                        """
                    )
                except Exception as e:
                    st.warning(f"Could not fetch detailed status: {str(e)}")

    with col1:
        # Controls
        st.header("Controls")
        
        # Auto-refresh toggle
        auto_refresh = st.toggle("Enable Auto-Refresh", value=st.session_state.auto_refresh)
        if auto_refresh != st.session_state.auto_refresh:
            st.session_state.auto_refresh = auto_refresh
        
        if auto_refresh:
            refresh_interval = st.slider(
                "Refresh Interval (seconds)",
                min_value=30,
                max_value=300,
                value=60
            )
        
        # Manual refresh button
        if st.button("🔄 Check Emails Now"):
            with st.spinner("Checking for new emails..."):
                result = trigger_email_check()
                if 'error' not in result:
                    st.success("Email check initiated!")
                    time.sleep(2)  # Wait for check to complete
                    st.rerun()  # Refresh the page
                else:
                    st.error(f"Failed to check emails: {result['error']}")
                    st.session_state.error_count += 1

        # Show email processing history
        st.header("Email Processing History")
        
        # Add filters
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            filter_status = st.selectbox(
                "Filter by Status",
                ["All", "Success", "Failed"]
            )
        with col_filter2:
            time_range = st.selectbox(
                "Time Range",
                ["Last Hour", "Last 24 Hours", "All Time"]
            )

        # Fetch email replies from backend
        email_replies = get_email_replies()
        
        if email_replies:
            df = pd.DataFrame(email_replies)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Apply filters
            if filter_status != "All":
                df = df[df['response_sent'] == (filter_status == "Success")]
            
            if time_range != "All Time":
                cutoff = datetime.now() - timedelta(
                    hours=1 if time_range == "Last Hour" else 24
                )
                df = df[df['timestamp'] >= cutoff]
            
            # Sort by timestamp
            df = df.sort_values('timestamp', ascending=False)
            
            # Display stats
            st.markdown("### Statistics")
            col_stats1, col_stats2, col_stats3 = st.columns(3)
            with col_stats1:
                st.metric("Total Emails", len(df))
            with col_stats2:
                success_rate = (df['response_sent'].sum() / len(df)) * 100 if len(df) > 0 else 0
                st.metric("Success Rate", f"{success_rate:.1f}%")
            with col_stats3:
                st.metric("Errors", st.session_state.error_count)
            
            # Display the dataframe
            st.dataframe(
                df,
                column_config={
                    "timestamp": st.column_config.DatetimeColumn("Time"),
                    "from_email": "From",
                    "to_email": "To",
                    "subject": "Subject",
                    "response_sent": st.column_config.CheckboxColumn("Success")
                },
                hide_index=True
            )
            
            # Export option
            if st.button("Export History"):
                csv = df.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    csv,
                    "zoho_mail_history.csv",
                    "text/csv"
                )
        else:
            st.info("No emails processed yet.")

    # Auto-refresh logic
    if st.session_state.auto_refresh:
        if (not st.session_state.last_check_time or 
            (datetime.now() - st.session_state.last_check_time).total_seconds() >= refresh_interval):
            time.sleep(1)  # Prevent too frequent refreshes
            st.rerun()

if __name__ == "__main__":
    main() 