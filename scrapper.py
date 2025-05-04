import streamlit as st
st.set_page_config(page_title="Instagram Scraper Pro", page_icon="📸", layout="wide")

import pandas as pd
import time
import random
import os
import json
import requests
import openai  # For ChatGPT usage
from serpapi import GoogleSearch
from dotenv import load_dotenv
from urllib.parse import urlparse
from typing import Optional
import imaplib
from email.header import decode_header
from datetime import datetime, timedelta
from streamlit_quill import st_quill
import logging
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.exc import GeocoderTimedOut
import us  # for state validation
import re

def safe_rerun():
    """Safely rerun the Streamlit app."""
    try:
        st.rerun()
    except:
        st.rerun()  # Try again with the same method as fallback

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Email related imports
from email_handler import EmailHandler
from profile_scraper import ProfileScraper
from ai_responder import AIResponder
from settings_manager import SettingsManager
from zoho_mail_handler import ZohoMailHandler
from email_manager import EmailManager

# Auto-fix .env file encoding before loading
def fix_env_file_encoding():
    """Fix .env file encoding to UTF-8 if it exists and has encoding issues."""
    env_path = '.env'
    if os.path.exists(env_path):
        # Try to detect encoding and fix issues
        content = None
        tried_encodings = []
        
        # Try multiple encodings
        for encoding in ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1']:
            tried_encodings.append(encoding)
            try:
                with open(env_path, 'r', encoding=encoding) as f:
                    content = f.read()
                logger.info(f"Successfully read .env with {encoding} encoding")
                break
            except UnicodeError:
                continue
        
        # If we successfully read the file and it wasn't UTF-8
        if content is not None and 'utf-8' not in tried_encodings[:tried_encodings.index(encoding)+1]:
            # Backup original
            backup_path = f"{env_path}.bak"
            os.rename(env_path, backup_path)
            logger.info(f"Backed up original .env file to {backup_path}")
            
            # Write with UTF-8 encoding
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info("Fixed .env file encoding to UTF-8")

# Fix .env encoding before loading environment variables
try:
    fix_env_file_encoding()
except Exception as e:
    logger.warning(f"Error fixing .env file encoding: {e}")
    # Continue with program even if fix fails

# Load environment variables
load_dotenv()

# Initialize settings manager at the module level
settings_manager = SettingsManager()

# Initialize the classes with the necessary keys and credentials
profile_scraper = ProfileScraper(
    serpapi_key=settings_manager.serpapi_key,
    rapidapi_key=settings_manager.rapidapi_key
)
ai_responder = AIResponder(openai_api_key=settings_manager.openai_key)

# Initialize email manager without showing error
if 'email_manager' not in st.session_state:
    st.session_state.email_manager = EmailManager(settings_manager)

# ------------------ INITIAL SETUP ------------------

# API Keys and Email Credentials
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Using ChatGPT
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

openai.api_key = OPENAI_API_KEY

# API Endpoints
PROFILE_API_URL = "https://social-api4.p.rapidapi.com/v1/info"
POST_API_URL = "https://social-api4.p.rapidapi.com/v1/post"
HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": "social-api4.p.rapidapi.com"
}

# Define the path for the session state file
SESSION_STATE_FILE = "session_state.json"

class LocationValidator:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="my_scraper")
        self.location_cache = {}  # Cache for geocoding results
        
    def validate_and_normalize_location(self, location_str):
        """Validate and normalize location strings."""
        try:
            # Return None for empty locations
            if not location_str or not isinstance(location_str, str):
                print(f"Empty or invalid location: {location_str}")
                return self._create_fallback_location(location_str)
                
            # Check cache first
            if location_str in self.location_cache:
                return self.location_cache[location_str]
            
            # Try geocoding with timeout
            try:
                location = self.geolocator.geocode(location_str, language='en', timeout=5)
            except:
                # If geocoding fails, use fallback
                print(f"Geocoding failed for: {location_str}")
                return self._create_fallback_location(location_str)
                
            if location:
                # Parse address components
                address_parts = location.raw.get('address', {})
                country = address_parts.get('country', '')
                state = address_parts.get('state', '')
                city = address_parts.get('city', '') or address_parts.get('town', '') or address_parts.get('village', '')
                
                result = {
                    'type': 'location',
                    'name': location.address,
                    'coords': (location.latitude, location.longitude),
                    'country': country,
                    'state': state,
                    'city': city,
                    'raw': location.raw
                }
                
                # Cache the result
                self.location_cache[location_str] = result
                return result
            else:
                # Geocoding returned no results
                print(f"No geocoding results for: {location_str}")
                return self._create_fallback_location(location_str)
            
        except Exception as e:
            print(f"Error validating location {location_str}: {e}")
            return self._create_fallback_location(location_str)
    
    def _create_fallback_location(self, location_str):
        """Create a fallback location dictionary when geocoding fails."""
        # If location_str is a valid string, parse it manually
        if location_str and isinstance(location_str, str):
            parts = [p.strip() for p in location_str.split(',')]
            
            # Create a simple structure based on parts count
            if len(parts) >= 3:
                # Likely city, state, country format
                return {
                    'type': 'location',
                    'name': location_str,
                    'coords': None,
                    'city': parts[0],
                    'state': parts[1],
                    'country': parts[2],
                    'raw': {}
                }
            elif len(parts) == 2:
                # Likely city, state or state, country
                return {
                    'type': 'location',
                    'name': location_str,
                    'coords': None,
                    'city': parts[0],
                    'state': parts[1],
                    'country': '',
                    'raw': {}
                }
            elif len(parts) == 1:
                # Just one element, could be city, state, or country
                return {
                    'type': 'location',
                    'name': location_str,
                    'coords': None, 
                    'city': '',
                    'state': '',
                    'country': parts[0],
                    'raw': {}
                }
        
        # Empty fallback for completely invalid locations
        return {
            'type': 'location',
            'name': location_str if isinstance(location_str, str) else '',
            'coords': None,
            'city': '',
            'state': '',
            'country': '',
            'raw': {}
        }

    def locations_match(self, target_location, profile_location, radius_miles=50):
        """Check if two locations match within a given radius."""
        try:
            target = self.validate_and_normalize_location(target_location)
            profile = self.validate_and_normalize_location(profile_location)
            
            if not target or not profile:
                return False
            
            # Country-level matching
            if target['country'] and profile['country']:
                if target['country'].lower() != profile['country'].lower():
                    return False
            
            # State/Region-level matching
            if target['state'] and profile['state']:
                if target['state'].lower() == profile['state'].lower():
                    return True
            
            # City-level matching
            if target['city'] and profile['city']:
                if target['city'].lower() == profile['city'].lower():
                    return True
            
            # Coordinate-based matching for nearby locations
            if target['coords'] and profile['coords']:
                distance = geodesic(target['coords'], profile['coords']).miles
                return distance <= radius_miles
            
            return False
            
        except Exception as e:
            print(f"Error matching locations: {e}")
            return False

def ensure_clean_state():
    """Ensure the application starts with a clean state."""
    if not st.session_state.get('initialized', False):
        # Clear any existing session state file
        if os.path.exists(SESSION_STATE_FILE):
            try:
                os.remove(SESSION_STATE_FILE)
            except Exception:
                pass
        
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Initialize with fresh values
        initialize_session_state()
        
        # Mark as initialized
        st.session_state['initialized'] = True

def save_session_state():
    """Save session state to JSON file."""
    state_to_save = {
        'current_step': st.session_state.get('current_step', 1),
        'steps_completed': list(st.session_state.get('steps_completed', set())),
        'generated_queries': st.session_state.get('generated_queries', pd.DataFrame()).to_dict('records') if isinstance(st.session_state.get('generated_queries'), pd.DataFrame) else [],
        'scraped_profiles': st.session_state.get('scraped_profiles', pd.DataFrame()).to_dict('records') if isinstance(st.session_state.get('scraped_profiles'), pd.DataFrame) else [],
        'filtered_profiles': st.session_state.get('filtered_profiles', pd.DataFrame()).to_dict('records') if isinstance(st.session_state.get('filtered_profiles'), pd.DataFrame) else [],
        'csv_valid': st.session_state.get('csv_valid', False),
        'api_keys': st.session_state.get('api_keys', {}),
        'email_settings': st.session_state.get('email_settings', {}),
        'company_settings': st.session_state.get('company_settings', {}),
        'zoho_settings': st.session_state.get('zoho_settings', {}),
        'business_context': st.session_state.get('business_context', None),
        'follow_up_templates': st.session_state.get('follow_up_templates', {}),
        'follow_up_tracking': st.session_state.get('follow_up_tracking', {}),
        'email_logs': st.session_state.get('email_logs', pd.DataFrame()).to_dict('records') if isinstance(st.session_state.get('email_logs'), pd.DataFrame) else [],
        'query_instructions': st.session_state.get('query_instructions', ""),
        'email_template_subject': st.session_state.get('email_template_subject', ""),
        'email_template_body': st.session_state.get('email_template_body', "")
    }
    
    try:
        with open('session_state.json', 'w', encoding='utf-8') as f:
            json.dump(state_to_save, f, indent=4)
    except Exception as e:
        st.error(f"Failed to save session state: {str(e)}")

def ensure_dataframe(data, columns=None):
    """Ensure the data is a DataFrame with specified columns."""
    if isinstance(data, pd.DataFrame):
        return data
    elif isinstance(data, list):
        if columns:
            return pd.DataFrame(data, columns=columns)
        return pd.DataFrame(data)
    else:
        if columns:
            return pd.DataFrame(columns=columns)
        return pd.DataFrame()

def load_session_state():
    """Load session state from JSON file."""
    try:
        with open('session_state.json', 'r', encoding='utf-8') as f:
            saved_state = json.load(f)
            
        # Restore all saved states
        st.session_state['current_step'] = saved_state.get('current_step', 1)
        st.session_state['steps_completed'] = set(saved_state.get('steps_completed', []))
        
        # Restore DataFrames
        st.session_state['generated_queries'] = pd.DataFrame(saved_state.get('generated_queries', []))
        st.session_state['scraped_profiles'] = pd.DataFrame(saved_state.get('scraped_profiles', []))
        st.session_state['filtered_profiles'] = pd.DataFrame(saved_state.get('filtered_profiles', []))
        
        # Restore other states
        st.session_state['csv_valid'] = saved_state.get('csv_valid', False)
        st.session_state['api_keys'] = saved_state.get('api_keys', {})
        st.session_state['email_settings'] = saved_state.get('email_settings', {})
        st.session_state['company_settings'] = saved_state.get('company_settings', {})
        st.session_state['zoho_settings'] = saved_state.get('zoho_settings', {})
        st.session_state['business_context'] = saved_state.get('business_context', None)
        st.session_state['follow_up_templates'] = saved_state.get('follow_up_templates', {
            '3_days': {'subject': '', 'body': ''},
            '6_days': {'subject': '', 'body': ''},
            '9_days': {'subject': '', 'body': ''},
            '12_days': {'subject': '', 'body': ''},
            '15_days': {'subject': '', 'body': ''},
            '18_days': {'subject': '', 'body': ''},
            '21_days': {'subject': '', 'body': ''}
        })
        st.session_state['follow_up_tracking'] = saved_state.get('follow_up_tracking', {})
        st.session_state['email_logs'] = pd.DataFrame(saved_state.get('email_logs', []))
        st.session_state['query_instructions'] = saved_state.get('query_instructions', "")
        st.session_state['email_template_subject'] = saved_state.get('email_template_subject', "")
        st.session_state['email_template_body'] = saved_state.get('email_template_body', "")
        
    except FileNotFoundError:
        initialize_session_state()
    except Exception as e:
        st.error(f"Failed to load session state: {str(e)}")
        initialize_session_state()

def initialize_session_state():
    """Initialize default session state values."""
    if 'initialized' not in st.session_state:
        st.session_state.update({
            'initialized': True,
            'api_keys': {},
            'email_settings': {},
            'company_settings': {},
            'zoho_settings': {},
            'business_context': None,
            'email_template_subject': "Premium OEM Car Emblems - Direct from Official Distributor",
            'email_template_body': """
            <p>Hi {username},</p>
            
            <p>I noticed your dealership's focus on quality and brand presentation. As the official distributor of OEM car emblems, we specialize in premium blacked-out versions for all makes and models.</p>
            
            <p>Quick highlights:</p>
            <ul>
            <li>Genuine OEM emblems and badges (original & blacked-out)</li>
            <li>Most items in stock for immediate delivery</li>
            <li>Personal delivery or tracked shipping available</li>
            <li>Custom options for corporate branding</li>
            </ul>
            
            <p>Many dealerships we work with have seen increased customer interest in blacked-out emblems, especially for premium vehicles. We currently supply to multiple dealerships in your area.</p>
            
            <p>Would you be interested in seeing our most popular options for your vehicles? I can share pricing and availability right away.</p>
            
            <p>Just reply "Yes" or call/WhatsApp me directly at 514-232-7355.</p>
            """,
            'follow_up_templates': {
                '3_days': {'subject': '', 'body': ''},
                '6_days': {'subject': '', 'body': ''},
                '9_days': {'subject': '', 'body': ''},
                '12_days': {'subject': '', 'body': ''},
                '15_days': {'subject': '', 'body': ''},
                '18_days': {'subject': '', 'body': ''},
                '21_days': {'subject': '', 'body': ''}
            },
            'follow_up_tracking': {},
            'email_logs': pd.DataFrame()
        })
        save_session_state()

# Load session state at the start
load_session_state()

# Add a "Restart" button
if st.button("Restart"):
    clear_session_state()
    st.experimental_rerun()

# Move this function up near the other session state functions, right after initialize_session_state()
def clear_session_state():
    """Clear the session state file and reset the session."""
    try:
        # 1. Remove the session state file
        if os.path.exists(SESSION_STATE_FILE):
            os.remove(SESSION_STATE_FILE)
        
        # 2. Clear all session state variables except widget-related ones
        keys_to_clear = [key for key in st.session_state.keys() 
                        if not (key.endswith('_button') or 
                               key.endswith('_confirm') or 
                               key.endswith('_sidebar') or
                               key.endswith('_input') or
                               key == 'test_username')]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        # 3. Initialize fresh default values without touching widget states
        st.session_state.update({
            'current_step': 1,
            'uploaded_file': None,
            'generated_queries': pd.DataFrame(columns=['Search Query']),
            'scraped_profiles': pd.DataFrame(),
            'filtered_profiles': pd.DataFrame(),
            'csv_valid': False,
            'stop_scraping': False,
            'steps_completed': set(),
            'email_logs': pd.DataFrame(),
            'show_settings': False,
            'show_test_results': False,
            'test_profile_data': None,
            'test_analysis': None,
            'test_email': None,
            'follow_up_templates': {
                '3_days': {'subject': '', 'body': ''},
                '6_days': {'subject': '', 'body': ''},
                '9_days': {'subject': '', 'body': ''},
                '12_days': {'subject': '', 'body': ''},
                '15_days': {'subject': '', 'body': ''},
                '18_days': {'subject': '', 'body': ''},
                '21_days': {'subject': '', 'body': ''}
            },
            'follow_up_tracking': {}
        })
            
    except Exception as e:
        st.error(f"Error during reset: {str(e)}")
    
    # 4. Use rerun instead of experimental_rerun
    st.rerun()

# ------------------ CORE FUNCTIONS ------------------
def deepseek_chat(prompt, system_prompt=None, temperature=0.7, json_mode=False):
    """
    Renamed to 'deepseek_chat' for minimal changes, but internally uses ChatGPT (GPT-4).
    """
    if not OPENAI_API_KEY:
        st.error("No OPENAI_API_KEY found. Cannot call ChatGPT.")
        return None

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=temperature
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"OpenAI Error: {str(e)}")
        return None

def extract_shortcode(url: str) -> Optional[str]:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    if not path_parts:
        return None
    
    if path_parts[0] in ("p", "reel", "tv") and len(path_parts) >= 2:
        return path_parts[1]
    return None

def extract_username(url: str) -> Optional[str]:
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    
    if path.count('/') == 0 and not path.startswith(('p/', 'reel/', 'tv/')):
        return path
    
    parts = [p for p in path.split('/') if p]
    username = None
    
    if parts:
        if len(parts) >= 2 and parts[1] in ('p', 'reel', 'tv'):
            username = parts[0]
        else:
            username = next((p for p in parts if '.' in p or '_' in p), None)
    
    if not username and parts:
        username = parts[0]
        
    return username

def get_post_owner(url: str) -> Optional[str]:
    short_code = extract_shortcode(url)
    if not short_code:
        return None

    try:
        response = requests.get(
            POST_API_URL,
            headers=HEADERS,
            params={"shortcode": short_code}
        )
        response.raise_for_status()
        top_data = response.json()
        post_data = top_data.get("data", {})
        return post_data.get('owner', {}).get('username')
    except Exception:
        return None

def scrape_recent_post_caption(url: str) -> str:
    short_code = extract_shortcode(url)
    if not short_code:
        return ""
    try:
        response = requests.get(
            POST_API_URL,
            headers=HEADERS,
            params={"shortcode": short_code}
        )
        response.raise_for_status()
        top_data = response.json()
        post_data = top_data.get("data", {})
        return post_data.get("caption", "")
    except Exception as e:
        st.warning(f"Failed to fetch post caption for {url}: {str(e)}")
        return ""

# ------------------ STEP 2: We let the user customize instructions ------------------
def generate_search_queries(csv_file, instructions_text):
    """Generate search queries with worldwide location support."""
    try:
        print("Debug: Starting query generation")
        csv_file.seek(0)
        df = pd.read_csv(csv_file)
        location_validator = LocationValidator()
        
        # Ensure required columns exist
        if 'Location' not in df.columns:
            print("Error: CSV must contain a 'Location' column")
            empty_df = pd.DataFrame(columns=['Search Query'])
            st.session_state['generated_queries'] = empty_df
            return empty_df
            
        if 'Venue Category' not in df.columns:
            print("Error: CSV must contain a 'Venue Category' column")
            empty_df = pd.DataFrame(columns=['Search Query'])
            st.session_state['generated_queries'] = empty_df
            return empty_df
        
        queries = []
        # Get all unique categories at once
        categories = ", ".join(df['Venue Category'].dropna().unique())
        
        # Process each unique location once
        unique_locations = df['Location'].dropna().unique()
        for location in unique_locations:
            print(f"Processing location: {location}")
            # Validate and normalize location
            validated_location = location_validator.validate_and_normalize_location(location)
            
            # Create location string based on available components
            location_parts = []
            if validated_location.get('city'):
                location_parts.append(validated_location['city'])
            if validated_location.get('state'):
                location_parts.append(validated_location['state'])
            if validated_location.get('country'):
                location_parts.append(validated_location['country'])
            
            # If location parts is empty, use the original location string
            location_str = ", ".join(location_parts) if location_parts else location
            print(f"Using location string: {location_str}")
            
            # Replace placeholders in the prompt
            prompt = instructions_text.replace("{CATEGORIES}", categories)
            prompt = prompt.replace("{LOCATION}", location_str)
            
            print(f"Sending prompt with location: {location_str}")
            response = deepseek_chat(
                prompt=prompt,
                system_prompt="Generate precise search queries for Instagram profile discovery. Consider the specific location components (city, state/region, country) when available.",
                temperature=0.7
            )

            if response:
                print(f"Received response for {location_str}")
                cleaned_queries = [line.strip() for line in response.split('\n') if line.strip() and not line.strip().startswith(('1.', '2.', '3.', 'Here'))]
                print(f"Generated {len(cleaned_queries)} queries for {location_str}")
                # Add location to each query for debugging
                labeled_queries = [f"{q} [Location: {location_str}]" for q in cleaned_queries]
                queries.extend(labeled_queries)

        if queries:
            result_df = pd.DataFrame(queries, columns=['Search Query']).drop_duplicates().reset_index(drop=True)
            st.session_state['generated_queries'] = result_df
            st.session_state.steps_completed.add(2)
            save_session_state()
            return result_df
        else:
            print("No queries were generated")
            empty_df = pd.DataFrame(columns=['Search Query'])
            st.session_state['generated_queries'] = empty_df
            return empty_df
    except Exception as e:
        print(f"Debug: Error occurred: {str(e)}")
        empty_df = pd.DataFrame(columns=['Search Query'])
        st.session_state['generated_queries'] = empty_df
        return empty_df

def scrape_profile_details(url: str, max_retries=3, retry_delay=2):
    """Scrape profile details with retry logic and better error handling."""
    for attempt in range(max_retries):
        try:
            username = extract_username(url) or get_post_owner(url)
            
            if not username:
                st.error(f"Could not extract username from: {url}")
                return None

            # First try with username
            response = requests.get(
                PROFILE_API_URL,
                headers=HEADERS,
                params={"username_or_id_or_url": username},
                timeout=15
            )

            # If 404 with username, try with full URL
            if response.status_code == 404:
                response = requests.get(
                    PROFILE_API_URL,
                    headers=HEADERS,
                    params={"username_or_id_or_url": url},
                    timeout=15
                )

            response.raise_for_status()

            top_data = response.json()
            profile_data = top_data.get("data", {})
            
            api_username = profile_data.get("username", "")
            full_name = profile_data.get("full_name", "")
            bio_text = profile_data.get("biography", "")
            external_url = profile_data.get("external_url", "")
            post_count = profile_data.get("media_count", 0)
            is_verified = profile_data.get("is_verified", False)
            
            follower_count = profile_data.get("follower_count", 0)
            is_private = profile_data.get("is_private", False)
            
            if not api_username:
                st.warning(f"No username found in profile data for {url}")
                return None

            recent_post = scrape_recent_post_caption(url)

            return {
                'username': api_username,
                'full_name': full_name,
                'bio': bio_text,
                'is_verified': is_verified,
                'is_private': is_private,
                'follower_count': follower_count,
                'post_count': post_count,
                'website': external_url,
                'profile_url': f"https://instagram.com/{api_username}",
                'source_url': url,
                'recent_post': recent_post
            }
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                st.warning(f"Request timed out, retrying... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                continue
            st.error(f"Request timed out after {max_retries} attempts for {url}")
            return None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                st.warning(f"Profile not found: {url}")
                return None
            st.error(f"API Error {e.response.status_code}: {e.response.text}")
            return None
            
        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries - 1:
                st.warning(f"Connection error, retrying... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                continue
            st.error(f"Connection failed after {max_retries} attempts for {url}: {str(e)}")
            return None
            
        except Exception as e:
            st.error(f"Error processing {url}: {str(e)}")
            return None
    
    return None

def scrape_profiles(queries_df):
    """Scrape profiles with worldwide location support."""
    # Initialize accumulated_results properly
    if isinstance(st.session_state.scraped_profiles, pd.DataFrame):
        accumulated_results = (
            st.session_state.scraped_profiles.to_dict('records')
            if not st.session_state.scraped_profiles.empty
            else []
        )
    elif isinstance(st.session_state.scraped_profiles, list):
        accumulated_results = st.session_state.scraped_profiles
    else:
        accumulated_results = []
    
    queries = queries_df['Search Query'].tolist()
    progress_bar = st.progress(0)
    status_text = st.empty()
    location_validator = LocationValidator()
    
    for idx, query in enumerate(queries):
        if st.session_state.stop_scraping:
            break
        
        progress = (idx + 1) / len(queries)
        status_text.markdown(f"**Searching ({idx+1}/{len(queries)}):** `{query}`")
        progress_bar.progress(progress)
        
        try:
            search = GoogleSearch({
                "engine": "google",
                "q": query,
                "api_key": SERPAPI_API_KEY,
                "hl": "en",
                "gl": "us",  # Keep US as base for consistent results
                "num": 10
            })
            serp_results = search.get_dict()
            
            if 'organic_results' in serp_results:
                for item in serp_results['organic_results']:
                    url = item.get('link', '')
                    if "instagram.com/" in url:
                        try:
                            clean_url = url.split('?')[0].rstrip('/')
                            if not any(p.get('profile_url') == clean_url for p in accumulated_results):
                                profile_data = scrape_profile_details(clean_url)
                                if profile_data:
                                    # Extract and validate location from profile
                                    profile_location = profile_data.get('location', '')
                                    if profile_location:
                                        validated_location = location_validator.validate_and_normalize_location(profile_location)
                                        if validated_location:
                                            profile_data['normalized_location'] = {
                                                'city': validated_location.get('city', ''),
                                                'state': validated_location.get('state', ''),
                                                'country': validated_location.get('country', ''),
                                                'coordinates': validated_location.get('coords')
                                            }
                                    
                                    accumulated_results.append({
                                        "Query": query,
                                        **profile_data
                                    })
                                    time.sleep(random.uniform(1, 3))
                        except Exception as e:
                            st.warning(f"Error processing {url}: {str(e)}")
            
            # Convert to DataFrame and update session state
            st.session_state.scraped_profiles = pd.DataFrame(accumulated_results)
            save_session_state()  # Save after each update
            
        except Exception as e:
            st.warning(f"Error processing query: {str(e)}")
    
    progress_bar.empty()
    status_text.empty()
    
    # Ensure we return a DataFrame
    result_df = pd.DataFrame(accumulated_results)
    st.session_state.scraped_profiles = result_df
    save_session_state()
    return result_df

def ai_profile_analysis(profiles_df):
    """Analyze profiles with worldwide location support."""
    enriched = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    location_validator = LocationValidator()
    
    for idx, row in profiles_df.iterrows():
        progress = (idx + 1) / len(profiles_df)
        status_text.markdown(f"Analyzing {idx+1}/{len(profiles_df)}")
        progress_bar.progress(progress)
        
        # Extract location information
        location_info = ""
        if 'normalized_location' in row:
            loc = row['normalized_location']
            location_parts = []
            if loc.get('city'): location_parts.append(loc['city'])
            if loc.get('state'): location_parts.append(loc['state'])
            if loc.get('country'): location_parts.append(loc['country'])
            location_info = ", ".join(location_parts)
        elif 'location' in row:
            location_info = row['location']
        
        analysis_prompt = f"""
        Analyze this Instagram profile and return ONLY a valid JSON object in this exact format:
        {{
            "emails": [],
            "phones": [],
            "social_media": [],
            "websites": [],
            "addresses": [],
            "location": {{
                "formatted": "",
                "components": {{
                    "city": "",
                    "state": "",
                    "country": ""
                }}
            }},
            "score": 0
        }}

        DO NOT include any other text, only the JSON object.

        Scoring logic (0 to 100, in increments of 20 points each):
        1) If the bio, website, or recent post mention any location/category/keyword from the search query.
        2) If the bio or recent post contain relevant hashtags from the search query.
        3) If the account has more than 10 posts.
        4) If the account is verified.
        5) If there's an additional strong match to the search query or important factor.

        Profile Data:
        - Search Query: {row.get('Query', '')}
        - Bio: {row['bio']}
        - Website: {row['website']}
        - Profile URL: {row['profile_url']}
        - Recent Post Caption: {row.get('recent_post', '')}
        - Post Count: {row['post_count']}
        - Is Verified: {row['is_verified']}
        - Location: {location_info}
        """

        try:
            response = deepseek_chat(
                prompt=analysis_prompt,
                system_prompt="You are an AI that extracts contact info, validates locations, and calculates a match score. Output ONLY valid JSON, no other text.",
                temperature=0.1,
                json_mode=True
            )
            
            if response:
                # Clean the response
                clean_response = response.strip()
                clean_response = clean_response.replace("```json", "").replace("```", "")
                clean_response = clean_response.strip()
                
                try:
                    contact_data = json.loads(clean_response)
                    
                    # Ensure all required fields exist with default values
                    final_data = {
                        "emails": contact_data.get("emails", []),
                        "phones": contact_data.get("phones", []),
                        "social_media": contact_data.get("social_media", []),
                        "websites": contact_data.get("websites", []),
                        "addresses": contact_data.get("addresses", []),
                        "location": contact_data.get("location", {
                            "formatted": "",
                            "components": {
                                "city": "",
                                "state": "",
                                "country": ""
                            }
                        }),
                        "score": contact_data.get("score", 0)
                    }
                    
                    # Validate data types
                    if not isinstance(final_data["emails"], list):
                        final_data["emails"] = []
                    if not isinstance(final_data["phones"], list):
                        final_data["phones"] = []
                    if not isinstance(final_data["social_media"], list):
                        final_data["social_media"] = []
                    if not isinstance(final_data["websites"], list):
                        final_data["websites"] = []
                    if not isinstance(final_data["addresses"], list):
                        final_data["addresses"] = []
                    if not isinstance(final_data["location"], dict):
                        final_data["location"] = {
                            "formatted": "",
                            "components": {
                                "city": "",
                                "state": "",
                                "country": ""
                            }
                        }
                    if not isinstance(final_data["score"], (int, float)):
                        final_data["score"] = 0
                    
                    enriched.append({**row.to_dict(), **final_data})
                    
                except json.JSONDecodeError as je:
                    st.warning(f"JSON parsing error for {row['username']}: {str(je)}")
                    enriched.append({
                        **row.to_dict(),
                        "emails": [],
                        "phones": [],
                        "social_media": [],
                        "websites": [],
                        "addresses": [],
                        "location": {
                            "formatted": "",
                            "components": {
                                "city": "",
                                "state": "",
                                "country": ""
                            }
                        },
                        "score": 0,
                        "parsing_error": clean_response
                    })
            else:
                enriched.append({
                    **row.to_dict(),
                    "emails": [],
                    "phones": [],
                    "social_media": [],
                    "websites": [],
                    "addresses": [],
                    "location": {
                        "formatted": "",
                        "components": {
                            "city": "",
                            "state": "",
                            "country": ""
                        }
                    },
                    "score": 0,
                    "error": "No AI response"
                })
                
        except Exception as e:
            st.warning(f"Analysis error for {row['username']}: {str(e)}")
            enriched.append({
                **row.to_dict(),
                "emails": [],
                "phones": [],
                "social_media": [],
                "websites": [],
                "addresses": [],
                "location": {
                    "formatted": "",
                    "components": {
                        "city": "",
                        "state": "",
                        "country": ""
                    }
                },
                "score": 0,
                "error": str(e)
            })
        
        time.sleep(0.5)
    
    progress_bar.empty()
    status_text.empty()
    
    # Create DataFrame and handle any remaining issues
    result_df = pd.DataFrame(enriched)
    
    # Ensure all required columns exist
    required_columns = ['emails', 'phones', 'social_media', 'websites', 'addresses', 'location', 'score']
    for col in required_columns:
        if col not in result_df.columns:
            if col == 'location':
                result_df[col] = [{
                    "formatted": "",
                    "components": {
                        "city": "",
                        "state": "",
                        "country": ""
                    }
                }] * len(result_df)
            elif col != 'score':
                result_df[col] = [[] for _ in range(len(result_df))]
            else:
                result_df[col] = 0
    
    return result_df

# ------------------ NEW FUNCTIONS FOR EMAIL SENDING ------------------

def generate_personalized_email(bio, username, recent_post="", custom_subject=None, custom_body=None):
    """Generate personalized email using ai_responder's implementation."""
    # Use ai_responder's implementation for consistent email generation
    return ai_responder.generate_personalized_email(
        bio=bio,
        username=username,
        recent_post=recent_post,
        custom_subject=custom_subject,
        custom_body=custom_body
    )

def send_email_via_zoho(to_email, subject, html_content, from_email=None):
    """Send email using Zoho SMTP."""
    if not st.session_state.get('zoho_handler'):
        st.error("❌ Zoho Mail handler is not initialized. Please check your Zoho settings and ensure your credentials are correct.")
        return None

    try:
        # Get the first available Zoho account if from_email not specified
        if not from_email:
            available_accounts = [acc for acc in st.session_state.zoho_handler.accounts if acc.email]
            if not available_accounts:
                st.error("❌ No Zoho email accounts configured. Please add at least one email account in your settings.")
                return None
            from_email = available_accounts[0].email

        if not from_email:
            st.error("❌ No sender email address configured. Please check your Zoho settings.")
            return None

        success = st.session_state.zoho_handler.send_email(
            from_email=from_email,
            to_email=to_email,
            subject=subject,
            body=html_content
        )
        
        if success:
            st.success(f"✅ Email sent successfully from {from_email} to {to_email}")
            return 202
        else:
            st.error("❌ Failed to send email. Please check your Zoho settings and try again.")
            return None
            
    except Exception as e:
        st.error(f"❌ Error sending email: {str(e)}")
        return None

def send_emails_to_leads(df, custom_subject=None, custom_body=None):
    """Send emails to leads using SendGrid."""
    if not st.session_state.email_manager or not st.session_state.email_manager.is_initialized():
        st.error("❌ Email manager is not initialized. Please check your SendGrid settings.")
        return pd.DataFrame()

    try:
        # Create a clean DataFrame for sending emails
        leads_df = pd.DataFrame({
            'email': df.apply(lambda row: row.get('emails', [''])[0] if row.get('emails') else '', axis=1),
            'name': df['full_name'],
            'username': df['username'],
            'subject': custom_subject,
            'body': custom_body
        })
        
        # Remove rows with empty emails
        leads_df = leads_df[leads_df['email'].str.len() > 0].reset_index(drop=True)
        
        if leads_df.empty:
            st.warning("No valid email addresses found in the selected profiles.")
            return pd.DataFrame([{
                "username": "No valid emails",
                "sent_to": None,
                "status": "No Valid Emails Found"
            }])

        # Send emails using SendGrid
        logs = []
        for _, row in leads_df.iterrows():
            try:
                # Send email using SendGrid
                results = st.session_state.email_manager.sendgrid.send_bulk_emails([{
                    'email': row['email'],
                    'name': row['name'],
                    'subject': row['subject'],
                    'body': row['body']
                }])
                
                status = "Sent" if results['success'] > 0 else f"Failed: {results.get('errors', ['Unknown error'])[0]}"
                logs.append({
                    "username": row['username'],
                    "sent_to": row['email'],
                    "status": status,
                    "sent_time": datetime.now().isoformat()
                })
                
                # Add delay between sends to avoid rate limits
                time.sleep(1)
                
            except Exception as e:
                logs.append({
                    "username": row['username'],
                    "sent_to": row['email'],
                    "status": f"Error: {str(e)}",
                    "sent_time": datetime.now().isoformat()
                })

        return pd.DataFrame(logs)

    except Exception as e:
        st.error(f"❌ Error sending emails: {str(e)}")
        return pd.DataFrame([{
            "username": "Error",
            "sent_to": None,
            "status": f"Error: {str(e)}"
        }])

# ------------------ SESSION STATE ------------------
if 'current_step' not in st.session_state:
    st.session_state.update({
        'current_step': 1,
        'uploaded_file': None,
        'generated_queries': pd.DataFrame(),
        'scraped_profiles': pd.DataFrame(),
        'filtered_profiles': pd.DataFrame(),
        'csv_valid': False,
        'stop_scraping': False,
        'steps_completed': set(),
        'email_logs': pd.DataFrame()
    })
    save_session_state()

# Initialize session state for auto-refresh
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.now()

# Initialize monitoring session state
if 'auto_refresh_zoho' not in st.session_state:
    st.session_state.auto_refresh_zoho = False
if 'last_check_time_zoho' not in st.session_state or st.session_state.last_check_time_zoho is None:
    st.session_state.last_check_time_zoho = datetime.now()
if 'processed_replies' not in st.session_state:
    st.session_state.processed_replies = []

# ------------------ UI COMPONENTS ------------------
st.title("📸 Instagram Pro Scraper")
st.markdown("---")

with st.sidebar:
    st.header("Navigation")
    steps = [
        (1, "📁 Upload CSV"),
        (2, "🔍 Generate Queries"),
        (3, "🚀 Scrape Profiles"),
        (4, "📤 Export Results"),
        (5, "📧 Send Emails"),
        (6, "📬 Monitor Replies")
    ]
    
    for step_num, step_name in steps:
        status = "✅" if step_num in st.session_state.steps_completed else "◻️"
        st.markdown(f"{status} **Step {step_num}**: {step_name}")
    
    st.markdown("---")
    
    # Settings Button and Panel
    if st.button("⚙️ Settings"):
        st.session_state.show_settings = not st.session_state.get('show_settings', False)
        save_session_state()
        st.rerun()

    # Settings Panel
    if st.session_state.get('show_settings', False):
        st.markdown("### ⚙️ Settings")
        
        # Show email manager error if exists
        if hasattr(st.session_state, 'email_manager') and st.session_state.email_manager.has_error():
            st.error(st.session_state.email_manager.get_error())
        
        settings_tabs = st.tabs(["API Keys", "Email Settings", "Company Settings", "AI Training"])
        
        with settings_tabs[0]:
            serpapi_key = st.text_input("SerpAPI Key", value=settings_manager.serpapi_key or "", type="password")
            openai_key = st.text_input("OpenAI API Key", value=settings_manager.openai_key or "", type="password")
            rapidapi_key = st.text_input("RapidAPI Key", value=settings_manager.rapidapi_key or "", type="password")
            sendgrid_key = st.text_input("SendGrid API Key", value=settings_manager.sendgrid_key or "", type="password")

        with settings_tabs[1]:
            st.markdown("### SendGrid Settings (Email Sending)")
            settings_manager.settings['email_settings'] = settings_manager.settings.get('email_settings', {})
            
            st.subheader("SendGrid Settings (Email Sending)")
            sendgrid_api_key = st.text_input(
                "SendGrid API Key",
                value=settings_manager.settings['email_settings'].get('sendgrid_api_key', ''),
                type="password",
                help="Required for sending cold emails"
            )
            
            sendgrid_from_email = st.text_input(
                "SendGrid From Email",
                value=settings_manager.cold_email or "",
                help="Your verified sender email (e.g., outreach@mail.yourdomain.com)"
            )
            
            sendgrid_from_name = st.text_input(
                "SendGrid From Name",
                value=settings_manager.settings['email_settings'].get('sendgrid_from_name', ''),
                help="The name that will appear as the sender"
            )
            
            reply_to_email = st.text_input(
                "Reply-To Email",
                value=settings_manager.response_email or "",
                help="Email address where recipients can reply to"
            )

        with settings_tabs[2]:
            st.markdown("### Company Information")
            company_name = st.text_input("Company Name", value=settings_manager.company_name or "")
            company_description = st.text_area(
                "Company Description",
                value=settings_manager.company_description or "",
                help="Brief description of your company and what you do"
            )
            company_services = st.text_area(
                "Services Offered",
                value=settings_manager.company_services or "",
                help="List your main services, one per line"
            )
            email_signature = st.text_area(
                "Email Signature",
                value=settings_manager.email_signature or "",
                help="Your professional email signature (will be added to all emails)"
            )
            company_tone = st.selectbox(
                "Email Tone",
                options=["professional", "casual", "friendly"],
                index=["professional", "casual", "friendly"].index(settings_manager.company_tone) if settings_manager.company_tone in ["professional", "casual", "friendly"] else 0,
                help="The tone of voice to use in emails"
            )

        if st.button("Save Settings"):
            # Update settings
            settings_manager.update_settings(
                serpapi_key=serpapi_key,
                openai_key=openai_key,
                rapidapi_key=rapidapi_key,
                sendgrid_key=sendgrid_api_key,
                cold_email=sendgrid_from_email,
                from_name=sendgrid_from_name,
                reply_to_email=reply_to_email,
                company_name=company_name,
                company_description=company_description,
                company_services=company_services,
                email_signature=email_signature,
                company_tone=company_tone
            )
            st.success("Settings saved!")
            
            # Force reload environment variables
            load_dotenv()
            
            save_session_state()
            st.rerun()

        with settings_tabs[3]:
            st.markdown("### AI Training")
            st.info("Train the AI with your business context to generate better personalized emails.")
            
            # Show current business context if available
            if settings_manager.business_context:
                st.success("✅ AI is currently trained with business context")
                with st.expander("View Current Business Context"):
                    st.json(settings_manager.business_context)
            else:
                st.warning("⚠️ AI is not trained with any business context yet")
            
            st.markdown("---")
            
            training_method = st.radio(
                "Select Training Method",
                ["Website", "CSV"],
                key="training_method"
            )
            
            if training_method == "Website":
                website_url = st.text_input(
                    "Website URL",
                    help="Enter your company website URL to train the AI"
                )
                
                if st.button("Train from Website"):
                    with st.spinner("Training AI from website..."):
                        if ai_responder.train_from_website(website_url):
                            st.success("✅ AI successfully trained from website!")
                            # Show updated business context
                            with st.expander("View Updated Business Context"):
                                st.json(settings_manager.business_context)
                        else:
                            st.error("❌ Failed to train AI from website")
                            
            else:  # CSV training
                uploaded_csv = st.file_uploader(
                    "Upload Training CSV",
                    type=['csv'],
                    help="Upload a CSV file with successful email campaigns"
                )
                
                if uploaded_csv:
                    if st.button("Train from CSV"):
                        with st.spinner("Training AI from CSV..."):
                            if ai_responder.train_from_csv(uploaded_csv):
                                st.success("✅ AI successfully trained from CSV!")
                                # Show updated business context
                                with st.expander("View Updated Business Context"):
                                    st.json(settings_manager.business_context)
                            else:
                                st.error("❌ Failed to train AI from CSV")
            
            # Option to clear business context
            st.markdown("---")
            if st.button("Clear Business Context"):
                settings_manager.update_business_context({})
                ai_responder.business_context = {}
                st.success("✅ Business context cleared!")
                st.rerun()

    st.caption(f"RapidAPI: {'✅' if RAPIDAPI_KEY else '❌'} | OpenAI: {'✅' if OPENAI_API_KEY else '❌'}")

    # Test Profile Section in Sidebar
    st.markdown("---")
    st.markdown("### 🧪 Test Profile")
    
    # Container for test profile input and results
    test_container = st.container()
    
    with test_container:
        # Initialize test_username in session state if not present
        if 'test_username' not in st.session_state:
            st.session_state['test_username'] = ""
        
        # Ensure the value is a string
        current_username = str(st.session_state.get('test_username', ""))
        
        # Simple input field with persistent state
        test_username = st.text_input(
            "Instagram Username or Profile URL",
            value=current_username,
            key="test_username_input"
        )
        
        # Update session state with the new value
        st.session_state['test_username'] = test_username
        
        # Test profile button
        if st.button("🔍 Test Profile", key="test_profile_button"):
            if test_username:
                if not test_username.startswith('http'):
                    test_username = f"https://instagram.com/{test_username}"
                
                with st.spinner("Scraping profile..."):
                    try:
                        profile_data = scrape_profile_details(test_username)
                        if profile_data:
                            # Store profile data and show success message
                            st.session_state['test_profile_data'] = profile_data
                            st.session_state['show_test_results'] = True
                            st.success("Profile scraped successfully!")
                            
                            # Automatically run analysis
                            with st.spinner("Analyzing profile..."):
                                test_df = pd.DataFrame([profile_data])
                                analysis_result = ai_profile_analysis(test_df)
                                if not analysis_result.empty:
                                    st.session_state['test_analysis'] = analysis_result.iloc[0].to_dict()
                                    
                                    # Generate email if analysis successful
                                    profile = st.session_state['test_profile_data']
                                    try:
                                        # Ensure business context is available in ai_responder
                                        if 'business_context' in st.session_state and st.session_state['business_context']:
                                            ai_responder.business_context = st.session_state['business_context']
                                            logger.debug("Business context loaded from session state")
                                        else:
                                            # Load from settings manager if not in session state
                                            ai_responder.business_context = settings_manager.business_context
                                            logger.debug("Business context loaded from settings manager")
                                            
                                        subject, body = ai_responder.generate_personalized_email(
                                            bio=profile.get('bio', ''),
                                            username=profile.get('username', ''),
                                            recent_post=profile.get('recent_post', ''),
                                            custom_subject=st.session_state.get('email_template_subject'),
                                            custom_body=st.session_state.get('email_template_body')
                                        )
                                        st.session_state['test_email'] = {
                                            'subject': subject if subject else "No subject generated",
                                            'body': body if body else "<p>No email body generated</p>"
                                        }
                                    except Exception as e:
                                        st.error(f"Error generating email: {str(e)}")
                                        st.session_state['test_email'] = {
                                            'subject': "Error generating subject",
                                            'body': "<p>Error generating email body</p>"
                                        }
                                    save_session_state()  # Save the state before rerunning
                    except Exception as e:
                        st.error(f"Error processing profile: {str(e)}")
        
        # Clear test button
        if st.button("🔄 Clear Test", key="clear_test_button"):
            # Only clear test-related state data
            test_keys = ['test_profile_data', 'test_analysis', 'test_email', 'show_test_results']
            for key in test_keys:
                if key in st.session_state:
                    del st.session_state[key]
            save_session_state()  # Save the state before rerunning
            st.rerun()

# Remove the test mode tab from steps and tabs
steps = [
    (1, "📁 Upload CSV"),
    (2, "🔍 Generate Queries"),
    (3, "🚀 Scrape Profiles"),
    (4, "📤 Export Results"),
    (5, "📧 Send Emails"),
    (6, "📬 Monitor Replies")
]
tabs = st.tabs([f"Step {num} - {name}" for num, name in steps])

# Step 1: Upload CSV
with tabs[0]:
    st.subheader("1. Upload Venue Data")
    uploaded_file = st.file_uploader("Upload CSV File", type=['csv'])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            if {'Venue Category', 'Location'}.issubset(df.columns):  # Changed from 'State' to 'Location'
                # Validate locations using LocationValidator
                location_validator = LocationValidator()
                valid_locations = []
                invalid_locations = []
                
                for _, row in df.iterrows():
                    location = row['Location']
                    validated = location_validator.validate_and_normalize_location(location)
                    if validated:
                        valid_locations.append(location)
                    else:
                        invalid_locations.append(location)
                
                if invalid_locations:
                    st.warning(f"Some locations could not be validated: {', '.join(invalid_locations)}")
                
                if valid_locations:
                    st.session_state.csv_valid = True
                    st.session_state.uploaded_file = uploaded_file
                    st.session_state.steps_completed.add(1)
                    save_session_state()
                    
                    with st.expander("Preview Data"):
                        st.dataframe(df.head(3))
                    st.success(f"CSV file validated! Found {len(valid_locations)} valid locations.")
                else:
                    st.error("No valid locations found in the CSV file.")
            else:
                st.error("Missing required columns: Venue Category and/or Location")
        except Exception as e:
            st.error(f"Invalid CSV: {str(e)}")

# Step 2: Generate Queries
with tabs[1]:
    st.subheader("2. Generate Search Queries")
    
    if 1 not in st.session_state.steps_completed:
        st.warning("Complete Step 1 first.")
    else:
        # Define default instructions for query generation
        default_instructions = """
        Generate highly effective Google search queries to find **personal Instagram profiles** of professionals across **all** the following categories: 
        {CATEGORIES}, located in **{LOCATION}**.

        Each query should be optimized to locate individuals who are **owners, founders, entrepreneurs, or key decision-makers** in these industries. The queries should be structured to maximize the chances of finding **real people** rather than company pages. 

        Generate **three queries per category** **All queries should be unique and different to avoid getting the same results** using different strategies:

        - **Role-Based Search:** Prioritize roles like "owner," "founder," "CEO," "entrepreneur," "dropshipper," or other relevant titles.
        - **Industry-Specific Search:** Target specific keywords commonly associated with the venue category.
        - **Hashtag-Based Search:** Use hashtags to locate personal Instagram profiles in each category.

        Use the following format for generating queries:

        site:instagram.com "{LOCATION}" ("owner" OR "founder" OR "CEO" OR "entrepreneur" OR "dropshipper") "@gmail.com" "{CATEGORIES}"
        site:instagram.com "{LOCATION}" "{CATEGORIES}" ("business" OR "startup" OR "store" OR "brand") "@gmail.com"
        site:instagram.com "#{LOCATION}" "#{CATEGORIES}" "@gmail.com" ("real" OR "official" OR "personal")

        **Output only the search queries**, each on a new line. Do **not** number the queries. ** Queries should not be too long **
        """

        # Initialize query_instructions in session state if not present
        if "query_instructions" not in st.session_state:
            st.session_state.query_instructions = default_instructions

        # Text area without default value, using only session state
        instructions_text = st.text_area(
            "Instructions for Query Generation",
            value=st.session_state.query_instructions,
            height=300,
            key="query_instructions_input"  # Changed key to avoid conflict
        )

        # Update session state when text changes
        if instructions_text != st.session_state.query_instructions:
            st.session_state.query_instructions = instructions_text
        
        generate_button = st.button("Generate Queries", key="generate_queries_btn")
        
        if generate_button:
            with st.spinner("Creating search queries..."):
                if st.session_state.uploaded_file is not None:
                    # Generate queries without modifying button state
                    queries_df = generate_search_queries(st.session_state.uploaded_file, instructions_text)
                    
                    if not queries_df.empty:
                        st.success(f"Generated {len(queries_df)} queries successfully!")
                        st.dataframe(queries_df, height=300)
                        st.download_button(
                            "Download Queries",
                            data=queries_df.to_csv(index=False),
                            file_name="search_queries.csv",
                            key="download_queries_btn"
                        )
                    else:
                        st.error("No queries were generated. Please check the input data and try again.")
                else:
                    st.error("No file uploaded or file not properly set in session state.")
        
        # Display existing queries if they exist in session state
        elif ('generated_queries' in st.session_state and 
              isinstance(st.session_state.generated_queries, pd.DataFrame) and 
              not st.session_state.generated_queries.empty):
            st.dataframe(st.session_state.generated_queries, height=300)
            st.download_button(
                "Download Queries",
                data=st.session_state.generated_queries.to_csv(index=False),
                file_name="search_queries.csv",
                key="download_existing_queries_btn"
            )

# Step 3: Scrape Profiles
with tabs[2]:
    st.subheader("3. Scrape Instagram Profiles")
    
    if 2 not in st.session_state.steps_completed:
        st.warning("Complete Step 2 first")
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("Start Scraping", type="primary"):
                st.session_state.stop_scraping = False
                # Ensure scraped_profiles is a DataFrame before scraping
                if not isinstance(st.session_state.scraped_profiles, pd.DataFrame):
                    st.session_state.scraped_profiles = pd.DataFrame()
                st.session_state.scraped_profiles = scrape_profiles(st.session_state.generated_queries)
                st.session_state.steps_completed.add(3)
                save_session_state()
                safe_rerun()
        
        with col2:
            if st.button("Stop Scraping"):
                st.session_state.stop_scraping = True
        
        # Check if we have profiles to display
        if isinstance(st.session_state.scraped_profiles, pd.DataFrame):
            if not st.session_state.scraped_profiles.empty:
                st.dataframe(st.session_state.scraped_profiles, height=400)
        elif isinstance(st.session_state.scraped_profiles, list) and st.session_state.scraped_profiles:
            df = pd.DataFrame(st.session_state.scraped_profiles)
            st.session_state.scraped_profiles = df
            st.dataframe(df, height=400)

# Step 4: Analysis & Export
with tabs[3]:
    st.subheader("4. Analysis & Export")
    
    if 3 not in st.session_state.steps_completed:
        st.warning("Complete Step 3 first")
    else:
        if st.button("Analyze Profiles"):
            with st.spinner("Analyzing..."):
                # Ensure scraped_profiles is a DataFrame
                if not isinstance(st.session_state.scraped_profiles, pd.DataFrame):
                    st.session_state.scraped_profiles = pd.DataFrame(st.session_state.scraped_profiles)
                
                st.session_state.filtered_profiles = ai_profile_analysis(st.session_state.scraped_profiles)

                # 1) Remove duplicates by username
                st.session_state.filtered_profiles.drop_duplicates(subset="username", keep="first", inplace=True)

                # 2) Exclude profiles that have NO contact details
                def has_contact_details(row):
                    emails = row.get("emails", [])
                    if not isinstance(emails, list):
                        return False
                    return len(emails) > 0

                st.session_state.filtered_profiles = st.session_state.filtered_profiles[
                    st.session_state.filtered_profiles.apply(has_contact_details, axis=1)
                ]

                st.session_state.steps_completed.add(4)
                save_session_state()  # Save state after analysis
                safe_rerun()
        
        if not st.session_state.filtered_profiles.empty:
            st.dataframe(st.session_state.filtered_profiles)

            csv_data = st.session_state.filtered_profiles.to_csv(index=False)
            st.download_button(
                "Download Full Results",
                data=csv_data,
                file_name="instagram_profiles.csv"
            )

            high_priority = st.session_state.filtered_profiles[
                st.session_state.filtered_profiles["score"] >= 60
            ]
            st.subheader("High Priority Profiles (score >= 60)")
            st.dataframe(high_priority)

            if 'parsing_error' in st.session_state.filtered_profiles.columns:
                error_profiles = st.session_state.filtered_profiles[st.session_state.filtered_profiles['parsing_error'].notna()]
                if not error_profiles.empty:
                    st.warning("Some profiles had parsing errors. You may want to re-analyze these:")
                    st.dataframe(error_profiles[['username', 'parsing_error']])

# Step 5: Send Emails
with tabs[4]:
    st.subheader("5. Send Emails to Leads")

    if 4 not in st.session_state.steps_completed:
        st.warning("Complete Step 4 first (Analyze & Export)")
    else:
        # Ensure email_logs is a DataFrame
        if 'email_logs' not in st.session_state or not isinstance(st.session_state.email_logs, pd.DataFrame):
            st.session_state.email_logs = pd.DataFrame()
        
        # Ensure filtered_profiles is a DataFrame
        if not isinstance(st.session_state.filtered_profiles, pd.DataFrame):
            st.session_state.filtered_profiles = pd.DataFrame(st.session_state.filtered_profiles)
        
        email_option = st.radio(
            "Select email sending option:",
            ["Send to all found emails", "Send to only high priority accounts"]
        )

        # Example Email Preview
        example_df = st.session_state.filtered_profiles.copy()
        if email_option == "Send to only high priority accounts":
            example_df = example_df[example_df["score"] >= 60]

        st.markdown("### Example Email Preview")
        if not example_df.empty:
            first_profile = example_df.iloc[0]
            
            # Store template in session state if not exists
            if 'email_template_subject' not in st.session_state:
                st.session_state.email_template_subject = "Growing Together with {username}"
            if 'email_template_body' not in st.session_state:
                st.session_state.email_template_body = """
                <p>Hello {username},</p>
                <p>I noticed you're an entrepreneur in the e-commerce space.</p>
                <p>I'd love to connect and explore potential collaboration opportunities.</p>
                <p>Best regards,<br>Your Name</p>
                """

            # Use text_input with on_change callback for subject
            subject_input = st.text_input(
                "Subject Template",
                value=st.session_state.email_template_subject,
                key="email_subject_input",
                help="Available placeholders: {username}, {role}, {industry}, {achievements}, {unique_point}",
                on_change=lambda: setattr(st.session_state, 'email_template_subject', st.session_state.email_subject_input)
            )

            # Add CSS for Quill editor height control
            st.markdown("""
                <style>
                .element-container:has(> iframe) {
                    height: 300px;
                    overflow-y: scroll;
                    overflow-x: hidden;
                }
                </style>
            """, unsafe_allow_html=True)
            
            # Use Quill editor for body template
            st.markdown("##### Body Template")
            st.caption("Available placeholders: {username}, {role}, {industry}, {achievements}, {unique_point}")
            
            body_input = st_quill(
                value=st.session_state.email_template_body,
                html=True,
                key="email_body_input",
                toolbar=[
                    ['bold', 'italic', 'underline', 'strike'],
                    ['blockquote', 'code-block'],
                    [{'list': 'ordered'}, {'list': 'bullet'}],
                    [{'align': []}],
                    ['link'],
                    ['clean']
                ]
            )

            # Update session state when body changes
            if body_input != st.session_state.email_template_body:
                st.session_state.email_template_body = body_input
                # Clear preview data to force regeneration
                if 'preview_data' in st.session_state:
                    del st.session_state.preview_data
                if 'selected_email_index' in st.session_state:
                    del st.session_state.selected_email_index
                if 'email_preview_selector' in st.session_state:
                    del st.session_state.email_preview_selector
                save_session_state()

            # Update when subject changes
            if subject_input != st.session_state.email_template_subject:
                st.session_state.email_template_subject = subject_input
                # Clear preview data to force regeneration
                if 'preview_data' in st.session_state:
                    del st.session_state.preview_data
                if 'selected_email_index' in st.session_state:
                    del st.session_state.selected_email_index
                if 'email_preview_selector' in st.session_state:
                    del st.session_state.email_preview_selector
                save_session_state()

            # Save state after any changes
            save_session_state()

            # Show preview with current template
            preview_subject, preview_body = generate_personalized_email(
                bio=first_profile.get("bio", ""),
                username=first_profile.get("username", ""),
                recent_post=first_profile.get("recent_post", ""),
                custom_subject=st.session_state.email_template_subject,
                custom_body=st.session_state.email_template_body
            )

            st.markdown("### Preview")
            st.markdown("**Subject:**")
            st.code(preview_subject)
            st.markdown("**Body:**")
            st.markdown(preview_body, unsafe_allow_html=True)

            # Add buttons for preview control
            col1, col2 = st.columns([1, 3])
            with col1:
                preview_button = st.button("Preview All Emails")
            with col2:
                if st.button("🔄 Regenerate All Previews", type="primary", key="regenerate_preview_btn"):
                    # Clear all preview-related data from session state
                    keys_to_clear = [
                        'preview_data',
                        'selected_email_index',
                        'email_preview_selector'
                    ]
                    for key in keys_to_clear:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    # Force regenerate previews
                    target_df = example_df[example_df["score"] >= 60] if email_option == "Send to only high priority accounts" else example_df
                    
                    preview_data = []
                    for _, row in target_df.iterrows():
                        preview_subject, preview_body = generate_personalized_email(
                            bio=row.get('bio', ''),
                            username=row.get('username', ''),
                            recent_post=row.get('recent_post', ''),
                            custom_subject=st.session_state.email_template_subject,
                            custom_body=st.session_state.email_template_body
                        )
                        preview_data.append({
                            'username': row['username'],
                            'score': row.get('score', 'N/A'),
                            'email': row.get('emails', [''])[0],
                            'subject': preview_subject,
                            'body': preview_body,
                            'subject_length': len(preview_subject),
                            'body_length': len(preview_body)
                        })
                    
                    # Store new preview data
                    st.session_state.preview_data = preview_data
                    st.session_state.selected_email_index = 0
                    save_session_state()
                    st.rerun()  # Use rerun instead of experimental_rerun

            # Remove the old preview generation logic that was triggered by button state
            if preview_button:
                with st.spinner("Generating email previews..."):
                    target_df = example_df[example_df["score"] >= 60] if email_option == "Send to only high priority accounts" else example_df
                    
                    preview_data = []
                    for _, row in target_df.iterrows():
                        preview_subject, preview_body = generate_personalized_email(
                            bio=row.get('bio', ''),
                            username=row.get('username', ''),
                            recent_post=row.get('recent_post', ''),
                            custom_subject=st.session_state.email_template_subject,
                            custom_body=st.session_state.email_template_body
                        )
                        preview_data.append({
                            'username': row['username'],
                            'score': row.get('score', 'N/A'),
                            'email': row.get('emails', [''])[0],
                            'subject': preview_subject,
                            'body': preview_body,
                            'subject_length': len(preview_subject),
                            'body_length': len(preview_body)
                        })
                    
                    # Store preview data in session state
                    st.session_state.preview_data = preview_data
                    st.session_state.selected_email_index = 0
                    save_session_state()
                    st.rerun()  # Use rerun instead of experimental_rerun

            # Show previews if data exists in session state
            if hasattr(st.session_state, 'preview_data') and st.session_state.preview_data:
                preview_container = st.container()
                
                with preview_container:
                    # Display statistics
                    st.markdown("### 📊 Email Preview Statistics")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    preview_data = st.session_state.preview_data
                    
                    with col1:
                        st.metric("Total Emails", len(preview_data))
                    
                    with col2:
                        avg_subject_len = sum(p['subject_length'] for p in preview_data) / len(preview_data)
                        st.metric("Avg Subject Length", f"{avg_subject_len:.0f} chars")
                    
                    with col3:
                        avg_body_len = sum(p['body_length'] for p in preview_data) / len(preview_data)
                        st.metric("Avg Body Length", f"{avg_body_len:.0f} chars")
                    
                    with col4:
                        unique_subjects = len(set(p['subject'] for p in preview_data))
                        st.metric("Unique Subjects", f"{unique_subjects}/{len(preview_data)}")
                    
                    # Display validation warnings if any
                    warnings = []
                    if unique_subjects < len(preview_data) * 0.9:
                        warnings.append("⚠️ Some email subjects are very similar. Consider adding more personalization.")
                    
                    if any(p['subject_length'] > 100 for p in preview_data):
                        warnings.append("⚠️ Some subject lines are very long (>100 chars). Consider shortening them.")
                    
                    if any(p['body_length'] < 100 for p in preview_data):
                        warnings.append("⚠️ Some email bodies are very short (<100 chars). Consider adding more content.")
                    
                    if warnings:
                        st.warning("\n".join(warnings))
                    
                    st.markdown("### 📧 All Email Previews")
                    
                    # Create a two-column layout for vertical tabs
                    col1, col2 = st.columns([1, 2])
                    
                    # Create vertical tabs using radio buttons in the first column
                    with col1:
                        st.markdown("#### Select Email")
                        # Update the radio button implementation
                        email_options = [
                            {
                                'label': f"Email {i+1} - {preview_data[i]['username']}",
                                'value': i
                            } for i in range(len(preview_data))
                        ]
                        selected_email = st.radio(
                            "Choose an email to preview:",
                            options=range(len(preview_data)),
                            format_func=lambda x: f"Email {x+1} - {preview_data[x]['username']}",
                            key=f"email_preview_selector_{len(preview_data)}",
                            index=st.session_state.get('selected_email_index', 0)
                        )
                        # Update selected index in session state
                        st.session_state.selected_email_index = selected_email
                    
                    # Show the selected email preview in the second column
                    with col2:
                        preview = preview_data[selected_email]
                        st.markdown("#### Email Preview")
                        
                        # Profile Info Box
                        with st.expander("Profile Information", expanded=True):
                            st.text(f"Username: {preview['username']}")
                            st.text(f"Score: {preview['score']}")
                            if preview['email']:
                                st.text(f"Email: {preview['email']}")
                        
                        # Email Content Box
                        st.markdown("**Subject:**")
                        st.code(preview['subject'])
                        st.markdown("**Body:**")
                        st.markdown(preview['body'], unsafe_allow_html=True)
                        
                        # Email Stats
                        stats_cols = st.columns(2)
                        with stats_cols[0]:
                            st.metric("Subject Length", f"{preview['subject_length']} chars")
                        with stats_cols[1]:
                            st.metric("Body Length", f"{preview['body_length']} chars")
                
            st.markdown("---")

        if st.button("Send Emails Now"):
            # First verify business context exists
            if not settings_manager.business_context and ('business_context' not in st.session_state or not st.session_state['business_context']):
                st.error("❌ No business context found. Please train the AI with your business information first in the Settings > AI Training section.")
                st.stop()
                
            with st.spinner("Sending emails..."):
                if email_option == "Send to only high priority accounts":
                    leads_df = st.session_state.filtered_profiles[
                        st.session_state.filtered_profiles["score"] >= 60
                    ]
                else:
                    leads_df = st.session_state.filtered_profiles

                # First generate personalized emails for each lead
                with st.spinner("Generating personalized emails..."):
                    emails_data = []
                    for _, row in leads_df.iterrows():
                        try:
                            # Ensure business context is loaded
                            if 'business_context' in st.session_state and st.session_state['business_context']:
                                ai_responder.business_context = st.session_state['business_context']
                            else:
                                ai_responder.business_context = settings_manager.business_context
                            
                            # Generate email content
                            subject, body = ai_responder.generate_personalized_email(
                                bio=row.get('bio', ''),
                                username=row.get('username', ''),
                                recent_post=row.get('recent_post', ''),
                                custom_subject=st.session_state.get('email_template_subject'),
                                custom_body=st.session_state.get('email_template_body')
                            )
                            
                            # Add to emails data
                            row_dict = row.to_dict()
                            row_dict['subject'] = subject
                            row_dict['body'] = body
                            emails_data.append(row_dict)
                            
                        except Exception as e:
                            st.error(f"Error generating email for {row.get('username', '')}: {str(e)}")
                            continue
                    
                    # Convert to DataFrame
                    emails_df = pd.DataFrame(emails_data)
                    
                    # Send emails
                    with st.spinner("Sending emails..."):
                        logs_df = send_emails_to_leads(
                            emails_df,
                            custom_subject=None,  # Already included in emails_df
                            custom_body=None  # Already included in emails_df
                        )
                        
                        st.session_state.email_logs = pd.DataFrame(logs_df)  # Ensure it's a DataFrame
                        save_session_state()  # Save state after sending emails
                        
                        # Show results
                        success_count = len(logs_df[logs_df['status'] == 'Sent'])
                        failed_count = len(logs_df) - success_count
                        
                        if success_count > 0:
                            st.success(f"✅ Successfully sent {success_count} emails!")
                        if failed_count > 0:
                            st.error(f"❌ Failed to send {failed_count} emails. Check the logs for details.")

        # Display email logs if they exist
        if isinstance(st.session_state.email_logs, pd.DataFrame) and not st.session_state.email_logs.empty:
            st.markdown("### 📊 Email Sending Logs")
            st.dataframe(st.session_state.email_logs)

            # Download logs button
            csv_data = st.session_state.email_logs.to_csv(index=False)
            st.download_button(
                "📥 Download Email Logs",
                data=csv_data,
                file_name="sent_emails_logs.csv",
                mime="text/csv"
            )

            # Show merged data with profile information
            if not st.session_state.filtered_profiles.empty:
                st.markdown("### 📈 Detailed Results")
                logs_df = st.session_state.email_logs.rename(columns={"status": "email_status"})
                merged_df = pd.merge(
                    st.session_state.filtered_profiles,
                    logs_df[["username", "sent_to", "email_status", "sent_time"]],
                    on="username",
                    how="left"
                )

                st.dataframe(merged_df)

                # Download merged data button
                merged_csv = merged_df.to_csv(index=False)
                st.download_button(
                    "📥 Download Complete Report",
                    data=merged_csv,
                    file_name="profiles_and_sent_emails.csv",
                    mime="text/csv",
                    key="download_merged_data"
                )

# Add Test Results Section in main area (after the tabs)
if st.session_state.get('show_test_results', False):
    st.markdown("---")
    st.header("🧪 Test Results")
    
    # Create tabs for different test aspects
    test_tabs = st.tabs(["Profile", "Analysis", "Email Generation"])
    
    with test_tabs[0]:
        st.subheader("Profile Data")
        if 'test_profile_data' in st.session_state:
            st.json(st.session_state['test_profile_data'])
    
    with test_tabs[1]:
        st.subheader("Analysis Results")
        if 'test_analysis' in st.session_state:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Profile Score", f"{st.session_state['test_analysis'].get('score', 0)}/100")
                st.write("**Contact Information:**")
                st.write("📧 Emails:", st.session_state['test_analysis'].get('emails', []))
                st.write("📱 Phones:", st.session_state['test_analysis'].get('phones', []))
                st.write("🌐 Websites:", st.session_state['test_analysis'].get('websites', []))
    
    with test_tabs[2]:
        st.subheader("Email Generation")
        if 'test_email' in st.session_state and isinstance(st.session_state['test_email'], dict):
            st.markdown("**Generated Email:**")
            st.markdown("**Subject:**")
            st.code(st.session_state['test_email'].get('subject', 'No subject generated'))
            st.markdown("**Body Preview:**")
            st.markdown(st.session_state['test_email'].get('body', '<p>No email body generated</p>'), unsafe_allow_html=True)
            
            if st.session_state.get('test_analysis', {}).get('emails'):
                col1, col2 = st.columns([2, 1])
                with col1:
                    test_recipient = st.text_input(
                        "Send test email to:", 
                        value=st.session_state['test_analysis']['emails'][0],
                        key="main_recipient_input"
                    )
                with col2:
                    if st.button("📨 Send Test Email via SendGrid", key="main_send_button"):
                        with st.spinner("Sending test email..."):
                            # Create test data for SendGrid
                            test_data = {
                                'email': test_recipient,
                                'name': st.session_state.get('test_profile_data', {}).get('full_name', 'Test User'),
                                'subject': st.session_state['test_email']['subject'],
                                'body': st.session_state['test_email']['body']
                            }
                            
                            # Send email via SendGrid
                            if not st.session_state.email_manager.is_initialized():
                                st.error("❌ Email manager is not initialized. Please check your SendGrid settings.")
                            else:
                                try:
                                    results = st.session_state.email_manager.sendgrid.send_bulk_emails([test_data])
                                    
                                    if results['success'] > 0:
                                        st.success("✅ Test email sent successfully!")
                                    else:
                                        st.error(f"❌ Failed to send test email: {results.get('errors', ['Unknown error'])[0]}")
                                except Exception as e:
                                    st.error(f"❌ Error sending test email: {str(e)}")

# Step 6: Monitor Emails
with tabs[5]:
    st.subheader("6. Monitor Emails 📊")
    
    st.info("""
    Email monitoring is handled through two systems:
    1. SendGrid Event Webhook - For cold email tracking
    2. Zoho Mail - For response monitoring
    """)
    
    st.subheader("Cold Email Monitoring (SendGrid)")
    st.write("To monitor cold email activity:")
    st.markdown("""
    1. Go to your SendGrid dashboard
    2. Navigate to Settings > Mail Settings > Event Webhook
    3. Configure the webhook to receive email events
    4. View detailed analytics in the SendGrid dashboard
    """)
    
    st.subheader("Response Monitoring (Zoho)")
    st.write("Response monitoring is automatically handled through:")
    st.markdown("""
    1. Automatic response checking every 2 minutes
    2. AI-powered response generation
    3. Response logs in the system
    """)
    
    # Add monitoring dashboard
    if st.session_state.get('email_manager'):
        try:
            health_status = st.session_state.email_manager.monitor_email_health()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Cold Email Status")
                status = health_status['cold_emails']['status']
                if status == 'healthy':
                    st.success("✅ SendGrid: Healthy")
                elif status == 'warning':
                    st.warning("⚠️ SendGrid: Issues Detected")
                else:
                    st.error("❌ SendGrid: Error")
                    
                if health_status['cold_emails']['issues']:
                    st.write("Issues:")
                    for issue in health_status['cold_emails']['issues']:
                        st.write(f"- {issue}")
                        
                # Add SendGrid stats if available
                if hasattr(st.session_state.email_manager.sendgrid, 'get_stats'):
                    stats = st.session_state.email_manager.sendgrid.get_stats()
                    if stats:
                        st.write("Last 24 Hours:")
                        st.write(f"- Sent: {stats.get('sent', 0)}")
                        st.write(f"- Delivered: {stats.get('delivered', 0)}")
                        st.write(f"- Opened: {stats.get('opened', 0)}")
                        st.write(f"- Clicked: {stats.get('clicked', 0)}")
            
            with col2:
                st.subheader("Response Status")
                status = health_status['responses']['status']
                if status == 'healthy':
                    st.success("✅ Zoho: Healthy")
                elif status == 'warning':
                    st.warning("⚠️ Zoho: Issues Detected")
                else:
                    st.error("❌ Zoho: Error")
                    
                if health_status['responses']['issues']:
                    st.write("Issues:")
                    for issue in health_status['responses']['issues']:
                        st.write(f"- {issue}")
                        
                # Add Zoho response stats
                if hasattr(st.session_state.email_manager.zoho, 'get_email_logs'):
                    logs = st.session_state.email_manager.zoho.get_email_logs()
                    if not logs.empty:
                        st.write("Recent Activity:")
                        st.write(f"- Total Responses: {len(logs)}")
                        st.write(f"- Last Response: {logs['timestamp'].max()}")
            
            # Add refresh button
            if st.button("🔄 Refresh Status"):
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Error monitoring email health: {str(e)}")
    else:
        st.warning("⚠️ Email manager not initialized. Please check your settings.")
    
    # Add links to dashboards
    col1, col2 = st.columns(2)
    with col1:
        st.link_button("View SendGrid Dashboard", "https://app.sendgrid.com/")
    with col2:
        st.link_button("View Zoho Mail", "https://mail.zoho.com/")

st.markdown("---")
st.caption("Professional Instagram scraping tool with contact extraction and automated email outreach")

def search_profiles(location, category, page=1):
    """Search for profiles with worldwide location support."""
    try:
        # Normalize location
        location_validator = LocationValidator()
        validated_location = location_validator.validate_and_normalize_location(location)
        
        if not validated_location:
            return []
        
        search_queries = []
        
        # Generate location-specific search queries
        country = validated_location.get('country', '')
        state = validated_location.get('state', '')
        city = validated_location.get('city', '')
        
        # Add queries based on available location components
        if city:
            search_queries.extend([
                f"{category} {city}",
                f"{category} in {city}",
                f"{city} {category}"
            ])
            
            if state:
                search_queries.append(f"{category} {city}, {state}")
            
            if country:
                search_queries.append(f"{category} {city}, {country}")
        
        if state:
            search_queries.extend([
                f"{category} {state}",
                f"{category} in {state}",
                f"{state} {category}"
            ])
            
            if country:
                search_queries.append(f"{category} {state}, {country}")
        
        if country:
            search_queries.extend([
                f"{category} {country}",
                f"{category} in {country}",
                f"{country} {category}"
            ])
        
        # Search using each query and combine results
        all_results = []
        seen_profiles = set()
        
        for query in search_queries:
            results = perform_search(query, page)
            
            # Filter and deduplicate results
            for profile in results:
                profile_id = profile.get('id') or profile.get('url')
                if profile_id not in seen_profiles:
                    # Verify location match
                    profile_location = profile.get('location', '')
                    if location_validator.locations_match(location, profile_location):
                        all_results.append(profile)
                        seen_profiles.add(profile_id)
        
        return all_results
        
    except Exception as e:
        print(f"Error in search_profiles: {e}")
        return []

def get_major_cities(state_code):
    """Get major cities for a state."""
    # This could be expanded with a more comprehensive database
    major_cities_dict = {
        'TX': ['Houston', 'Dallas', 'Austin', 'San Antonio', 'Fort Worth', 'El Paso'],
        'CA': ['Los Angeles', 'San Francisco', 'San Diego', 'San Jose', 'Sacramento'],
        'NY': ['New York City', 'Buffalo', 'Rochester', 'Syracuse', 'Albany'],
        # Add more states as needed
    }
    return major_cities_dict.get(state_code, [])

def perform_search(query, page=1):
    """Perform the actual search with the given query."""
    # Your existing search implementation here
    pass

def extract_location_from_profile(profile_text):
    """Extract location information from profile text."""
    try:
        location_validator = LocationValidator()
        
        # Look for common location patterns
        location_patterns = [
            r'Location:\s*(.*?)(?:\n|$)',
            r'Based in\s*(.*?)(?:\n|$)',
            r'(?:^|\n)(?:📍|🌎|📌)\s*(.*?)(?:\n|$)',
            r'(?:^|\n)(?:City|State|Country):\s*(.*?)(?:\n|$)',
            r'(?:^|\n)(?:📍|🌎|📌|📮)\s*([^,\n]+(?:,\s*[^,\n]+)*)',
            r'(?:^|\n)([^,\n]+,\s*[A-Z]{2,3}(?:\s*,\s*[A-Za-z\s]+)?)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, profile_text)
            if match:
                location_str = match.group(1).strip()
                validated_location = location_validator.validate_and_normalize_location(location_str)
                if validated_location:
                    return validated_location
        
        return None
        
    except Exception as e:
        print(f"Error extracting location: {e}")
        return None
