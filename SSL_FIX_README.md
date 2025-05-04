# SSL Certificate Verification Fix

This guide provides solutions for SSL certificate verification issues in the Instagram Pro Scrapper tool.

## The Problem

When running the application, you may encounter errors like:

```
SSLError(SSLCertVerificationError(5, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1028)'))
```

This error occurs when Python cannot verify the SSL certificates of websites it connects to (mainly the geocoding service).

## Solution 1: Run the Patched Version (Recommended)

We've created a patched version that completely bypasses SSL verification and uses multiple alternative geocoding services:

1. Make sure all files are in your directory:
   - `disable_ssl.py`
   - `alternative_geocoding.py` 
   - `patched_main.py`

2. Run the patched version:
   ```
   python patched_main.py
   ```

This version:
- Disables all SSL certificate verification
- Uses 6 different geocoding services as fallbacks
- Monkey patches key libraries to avoid certificate errors
- Provides detailed logs about what's happening

## Solution 2: Test Your SSL Connection

If you want to diagnose the problem:

```
python test_ssl.py
```

This will show if your system can connect to the geocoding API and what SSL settings are in effect.

## Solution 3: Manual Import Fix

If you want to use the original `scrapper.py` but with SSL fixes, add this at the top of your Python script:

```python
import os
import ssl

# Disable SSL verification
os.environ['PYTHONHTTPSVERIFY'] = '0'
ssl._create_default_https_context = ssl._create_unverified_context

# Then import the rest of your code
# import scrapper
```

## Solution 4: Update Your Certificate Authority Store

If you want to fix the root issue rather than bypass verification:

1. **Windows**: Install the latest root certificates
2. **macOS**: Run Python's certificate installer: `/Applications/Python 3.x/Install Certificates.command`
3. **Linux**: Update your CA certificates: `sudo apt-get update && sudo apt-get install ca-certificates`

## Security Note

Disabling SSL verification is a security risk as it makes your application vulnerable to man-in-the-middle attacks. Only use these solutions in environments you trust or for development purposes. 