"""
SSL Verification Disabler

This script completely disables SSL certificate verification at the Python level.
Import this at the VERY BEGINNING of your app before any other imports.

WARNING: This disables ALL certificate validation, which is a security risk.
Only use in development environments or when you absolutely cannot fix certificate issues.
"""

import os
import sys
import ssl

# Disable SSL verification in environment variables (picked up by urllib3, requests, and others)
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''

# Monkey patch the stdlib ssl module to disable verification
try:
    _create_unverified_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python doesn't have the attribute
    pass
else:
    # Monkey patch to disable SSL verification globally
    ssl._create_default_https_context = _create_unverified_context

# For urllib3 (used by requests)
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass

print("⚠️ SSL certificate verification has been completely disabled! ⚠️")
print("This is a security risk - only use for testing when certificates can't be fixed.") 