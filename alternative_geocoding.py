"""
Alternative Geocoding Module

This module provides alternative geocoding services if the primary Nominatim service fails.
It attempts to use multiple different geocoding services to ensure at least one works.
"""

import os
import requests
import json
import ssl
import time
import random

# Import our SSL disabler
try:
    import disable_ssl
except ImportError:
    pass

class AlternativeGeocoder:
    """Alternative geocoding class that tries multiple services"""
    
    def __init__(self):
        # Disable SSL verification for all requests
        self.verify_ssl = False
        self.headers = {
            "User-Agent": "InstagramScraperGeocoder/1.0"
        }
        self.cache = {}  # Simple cache
    
    def geocode(self, location_str):
        """Geocode a location string using multiple fallback services"""
        if not location_str or location_str.strip() == '':
            return None
            
        # Check cache first
        if location_str in self.cache:
            return self.cache[location_str]
        
        # Try multiple services
        result = None
        
        # Services to try in order
        services = [
            self._try_locationiq,
            self._try_positionstack,
            self._try_geocode_maps,
            self._try_geoapify,
            self._try_direct_nominatim,
            self._try_mapbox,
        ]
        
        for service in services:
            try:
                result = service(location_str)
                if result:
                    # Cache and return result
                    self.cache[location_str] = result
                    return result
            except Exception as e:
                print(f"Error with geocoding service {service.__name__}: {e}")
                continue
        
        # If all services failed, return None
        return None
    
    def _try_direct_nominatim(self, location_str):
        """Try direct request to Nominatim, bypassing the geopy library"""
        try:
            encoded_query = requests.utils.quote(location_str)
            url = f"https://nominatim.openstreetmap.org/search?q={encoded_query}&format=json&limit=1&accept-language=en"
            
            response = requests.get(
                url,
                headers=self.headers,
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) > 0:
                item = data[0]
                return {
                    'type': 'location',
                    'name': item.get('display_name', location_str),
                    'coords': (float(item.get('lat', 0)), float(item.get('lon', 0))),
                    'country': self._extract_country(item),
                    'state': self._extract_state(item),
                    'city': self._extract_city(item),
                    'raw': item
                }
            return None
            
        except Exception as e:
            print(f"Direct Nominatim error: {e}")
            return None

    def _try_locationiq(self, location_str):
        """Try LocationIQ as an alternative geocoding service"""
        try:
            # Use a public demo key (rate limited)
            api_key = "pk.88d441856ce08d8ad058ac3a3d27293e"
            encoded_query = requests.utils.quote(location_str)
            
            url = f"https://us1.locationiq.com/v1/search.php?key={api_key}&q={encoded_query}&format=json&limit=1"
            
            response = requests.get(
                url,
                headers=self.headers,
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) > 0:
                item = data[0]
                # Parse display name to extract components
                parts = item.get('display_name', '').split(',')
                city = parts[0].strip() if len(parts) > 0 else ''
                state = parts[1].strip() if len(parts) > 1 else ''
                country = parts[-1].strip() if len(parts) > 2 else ''
                
                return {
                    'type': 'location',
                    'name': item.get('display_name', location_str),
                    'coords': (float(item.get('lat', 0)), float(item.get('lon', 0))),
                    'country': country,
                    'state': state,
                    'city': city,
                    'raw': item
                }
            return None
            
        except Exception as e:
            print(f"LocationIQ error: {e}")
            return None
            
    def _try_positionstack(self, location_str):
        """Try PositionStack as an alternative geocoding service"""
        try:
            # Use a demo key (rate limited)
            api_key = "5b7876f7bcafcabe7fa7c1a54e50840e"
            encoded_query = requests.utils.quote(location_str)
            
            url = f"http://api.positionstack.com/v1/forward?access_key={api_key}&query={encoded_query}&limit=1"
            
            response = requests.get(
                url,
                headers=self.headers,
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data and 'data' in data and len(data['data']) > 0:
                item = data['data'][0]
                return {
                    'type': 'location',
                    'name': f"{item.get('name', '')}, {item.get('region', '')}, {item.get('country', '')}",
                    'coords': (float(item.get('latitude', 0)), float(item.get('longitude', 0))),
                    'country': item.get('country', ''),
                    'state': item.get('region', ''),
                    'city': item.get('name', ''),
                    'raw': item
                }
            return None
            
        except Exception as e:
            print(f"PositionStack error: {e}")
            return None
            
    def _try_geocode_maps(self, location_str):
        """Try geocode.maps.co as an alternative geocoding service"""
        try:
            encoded_query = requests.utils.quote(location_str)
            url = f"https://geocode.maps.co/search?q={encoded_query}&limit=1"
            
            response = requests.get(
                url,
                headers=self.headers,
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) > 0:
                item = data[0]
                # Parse display name to extract components
                parts = item.get('display_name', '').split(',')
                city = parts[0].strip() if len(parts) > 0 else ''
                state = parts[1].strip() if len(parts) > 1 else ''
                country = parts[-1].strip() if len(parts) > 2 else ''
                
                return {
                    'type': 'location',
                    'name': item.get('display_name', location_str),
                    'coords': (float(item.get('lat', 0)), float(item.get('lon', 0))),
                    'country': country,
                    'state': state,
                    'city': city,
                    'raw': item
                }
            return None
            
        except Exception as e:
            print(f"Geocode.maps.co error: {e}")
            return None
    
    def _try_geoapify(self, location_str):
        """Try geoapify as an alternative geocoding service"""
        try:
            # Use a demo key (rate limited)
            api_key = "2f46d3f5aa1a4afab30e1e4ef273d624"
            encoded_query = requests.utils.quote(location_str)
            
            url = f"https://api.geoapify.com/v1/geocode/search?text={encoded_query}&apiKey={api_key}&limit=1"
            
            response = requests.get(
                url,
                headers=self.headers,
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data and 'features' in data and len(data['features']) > 0:
                feature = data['features'][0]
                props = feature.get('properties', {})
                
                return {
                    'type': 'location',
                    'name': props.get('formatted', location_str),
                    'coords': (float(props.get('lat', 0)), float(props.get('lon', 0))),
                    'country': props.get('country', ''),
                    'state': props.get('state', ''),
                    'city': props.get('city', ''),
                    'raw': props
                }
            return None
            
        except Exception as e:
            print(f"Geoapify error: {e}")
            return None
            
    def _try_mapbox(self, location_str):
        """Try Mapbox as an alternative geocoding service"""
        try:
            # Use a demo key (rate limited)
            api_key = "pk.eyJ1IjoiZGVtby1hY2NvdW50IiwiYSI6ImNrZHZlbTlrMDAwMGczbnBlZDJqbm90cGEifQ.2dJgCLl-mWM2c26-g67TAw"
            encoded_query = requests.utils.quote(location_str)
            
            url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{encoded_query}.json?access_token={api_key}&limit=1"
            
            response = requests.get(
                url,
                headers=self.headers,
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data and 'features' in data and len(data['features']) > 0:
                feature = data['features'][0]
                context = feature.get('context', [])
                
                country = next((c['text'] for c in context if c['id'].startswith('country')), '')
                region = next((c['text'] for c in context if c['id'].startswith('region')), '')
                place = next((c['text'] for c in context if c['id'].startswith('place')), '')
                
                coords = feature.get('center', [0, 0])
                
                return {
                    'type': 'location',
                    'name': feature.get('place_name', location_str),
                    'coords': (coords[1], coords[0]),  # Mapbox returns [lon, lat]
                    'country': country,
                    'state': region,
                    'city': place,
                    'raw': feature
                }
            return None
            
        except Exception as e:
            print(f"Mapbox error: {e}")
            return None
    
    def _extract_country(self, item):
        """Extract country from Nominatim response"""
        if 'address' in item:
            return item['address'].get('country', '')
        return ''
        
    def _extract_state(self, item):
        """Extract state from Nominatim response"""
        if 'address' in item:
            return item['address'].get('state', '')
        return ''
        
    def _extract_city(self, item):
        """Extract city from Nominatim response"""
        if 'address' in item:
            return (item['address'].get('city', '') or 
                   item['address'].get('town', '') or 
                   item['address'].get('village', ''))
        return ''

# Usage example:
# geocoder = AlternativeGeocoder()
# result = geocoder.geocode("Montreal, Canada") 