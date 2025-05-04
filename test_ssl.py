"""
SSL Connection Test Script

This script tests connections to various APIs to verify
if SSL verification fixes are working properly.
"""

# Import the SSL disabler first
try:
    import disable_ssl
except ImportError:
    print("⚠️ SSL disabler not found, continuing without it")

import requests
import sys
import os
import time
from geopy.geocoders import Nominatim
import ssl
import urllib3

# Check environment vars for SSL
print("Checking environment variables:")
for var in ['PYTHONHTTPSVERIFY', 'REQUESTS_CA_BUNDLE', 'SSL_CERT_FILE', 'GEOPY_SSL_CONTEXT']:
    print(f"  {var}: {os.environ.get(var, 'Not set')}")

# Test SSL context
print("\nChecking SSL context:")
try:
    ctx = ssl.create_default_https_context()
    print(f"  Default SSL context verify mode: {ctx.verify_mode}")
    if ctx.verify_mode == ssl.CERT_NONE:
        print("  ✅ SSL verification is disabled!")
    else:
        print("  ❌ SSL verification is still enabled!")
except Exception as e:
    print(f"  Error checking SSL context: {e}")

# Test a connection to OpenStreetMap's Nominatim API (the one that fails)
print("\nTesting connection to Nominatim API:")
try:
    # Create a custom SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # Create the geocoder with our disabled SSL context
    geolocator = Nominatim(
        user_agent="test_script",
        timeout=10,
        scheme="https",
        ssl_context=ssl_context
    )
    
    print("  Attempting geocoding for 'Montreal'...")
    location = geolocator.geocode("Montreal", timeout=10)
    
    if location:
        print(f"  ✅ Successfully geocoded! Found: {location.address}")
    else:
        print("  ⚠️ Geocoding returned no results, but no errors occurred")
        
except Exception as e:
    print(f"  ❌ Error geocoding with SSL context: {str(e)}")

# Test direct HTTP request to Nominatim
print("\nTesting direct request to Nominatim API:")
try:
    response = requests.get(
        "https://nominatim.openstreetmap.org/search?q=Montreal&format=json&limit=1&accept-language=en",
        headers={"User-Agent": "test_script"},
        verify=False
    )
    response.raise_for_status()
    data = response.json()
    
    if data:
        print(f"  ✅ Successfully received data: {data[0].get('display_name', '')}")
    else:
        print("  ⚠️ Request succeeded but no data returned")
        
except Exception as e:
    print(f"  ❌ Error making request: {str(e)}")

print("\nTest complete!") 