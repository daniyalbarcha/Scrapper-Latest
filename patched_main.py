"""
Patched Main Entry Point

This script serves as the entry point for the Instagram Pro Scrapper application
with all SSL verification issues fixed and using alternative geocoding.

Run this script instead of the original scrapper.py to use the SSL-fixed version.
"""

# =========== Import SSL disabler first ===========
try:
    import disable_ssl
    print("✅ SSL verification disabled successfully")
except ImportError as e:
    print(f"⚠️ Failed to import SSL disabler: {e}")

# =========== Monkey patch key modules ===========
import sys
import os
import ssl
import requests
import urllib3

# Force environment variables
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''
os.environ['GEOPY_SSL_CONTEXT'] = 'unverified'

# Monkey patch ssl
try:
    _create_unverified_context = ssl._create_unverified_context
    ssl._create_default_https_context = _create_unverified_context
    print("✅ Monkey patched SSL module")
except AttributeError:
    print("⚠️ Unable to monkey patch SSL module")

# Disable urllib3 warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Monkey patch requests to always use verify=False
original_get = requests.get
original_post = requests.post

def patched_get(*args, **kwargs):
    kwargs['verify'] = False
    return original_get(*args, **kwargs)

def patched_post(*args, **kwargs):
    kwargs['verify'] = False
    return original_post(*args, **kwargs)

requests.get = patched_get
requests.post = patched_post
print("✅ Monkey patched requests module")

# =========== Import AlternativeGeocoder ===========
try:
    from alternative_geocoding import AlternativeGeocoder
    alternative_geocoder = AlternativeGeocoder()
    print("✅ Alternative geocoder loaded")
except ImportError as e:
    print(f"⚠️ Failed to import alternative geocoder: {e}")
    alternative_geocoder = None

# =========== Monkey patch LocationValidator in the main app ===========
# We need to define this function before importing the main app
def patch_location_validator():
    from scrapper import LocationValidator
    
    # Save the original init and validate methods
    original_init = LocationValidator.__init__
    original_validate = LocationValidator.validate_and_normalize_location
    
    # Override the init method to add our alternative geocoder
    def patched_init(self):
        # Call the original init
        original_init(self)
        # Add our alternative geocoder
        self.alt_geocoder = alternative_geocoder
        print("✅ LocationValidator patched with alternative geocoder")
        
    # Override the validate method to use our alternative geocoder first
    def patched_validate(self, location_str):
        # First try the alternative geocoder if available
        if hasattr(self, 'alt_geocoder') and self.alt_geocoder:
            try:
                print(f"Trying alternative geocoder for: {location_str}")
                result = self.alt_geocoder.geocode(location_str)
                if result:
                    print(f"✅ Alternative geocoder succeeded for: {location_str}")
                    return result
                print(f"⚠️ Alternative geocoder returned no results for: {location_str}")
            except Exception as e:
                print(f"⚠️ Alternative geocoder failed for: {location_str} - {e}")
                
        # Fall back to the original method
        print(f"Falling back to original geocoder for: {location_str}")
        return original_validate(self, location_str)
        
    # Apply the patches
    LocationValidator.__init__ = patched_init
    LocationValidator.validate_and_normalize_location = patched_validate
    print("✅ LocationValidator methods patched")

# =========== Now import and run the main app ===========
print("Starting the Instagram Pro Scrapper with all SSL fixes applied...")
print("=" * 60)

# Try to patch the LocationValidator
try:
    patch_location_validator()
except Exception as e:
    print(f"⚠️ Failed to patch LocationValidator: {e}")

# Import and run the main app
import scrapper 