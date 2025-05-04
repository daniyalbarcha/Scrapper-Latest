import requests
import time
import random
import pandas as pd
import streamlit as st
from serpapi import GoogleSearch
from urllib.parse import urlparse
from typing import Optional

class ProfileScraper:
    def __init__(self, serpapi_key, rapidapi_key):
        self.serpapi_key = serpapi_key
        self.rapidapi_key = rapidapi_key
        self.profile_api_url = "https://social-api4.p.rapidapi.com/v1/info"
        self.post_api_url = "https://social-api4.p.rapidapi.com/v1/post"
        self.headers = {
            "x-rapidapi-key": self.rapidapi_key,
            "x-rapidapi-host": "social-api4.p.rapidapi.com"
        }

    def extract_shortcode(self, url: str) -> Optional[str]:
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        if not path_parts:
            return None
        
        if path_parts[0] in ("p", "reel", "tv") and len(path_parts) >= 2:
            return path_parts[1]
        return None

    def extract_username(self, url: str) -> Optional[str]:
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

    def get_post_owner(self, url: str) -> Optional[str]:
        short_code = self.extract_shortcode(url)
        if not short_code:
            return None

        try:
            response = requests.get(
                self.post_api_url,
                headers=self.headers,
                params={"shortcode": short_code},
                verify=False
            )
            response.raise_for_status()
            top_data = response.json()
            post_data = top_data.get("data", {})
            return post_data.get('owner', {}).get('username')
        except Exception:
            return None

    def scrape_recent_post_caption(self, url: str) -> str:
        short_code = self.extract_shortcode(url)
        if not short_code:
            return ""
        try:
            response = requests.get(
                self.post_api_url,
                headers=self.headers,
                params={"shortcode": short_code},
                verify=False
            )
            response.raise_for_status()
            top_data = response.json()
            post_data = top_data.get("data", {})
            return post_data.get("caption", "")
        except Exception as e:
            st.warning(f"Failed to fetch post caption for {url}: {str(e)}")
            return ""

    def scrape_profile_details(self, url: str):
        try:
            username = self.extract_username(url) or self.get_post_owner(url)
            
            if not username:
                st.error(f"Could not extract username from: {url}")
                return None

            response = requests.get(
                self.profile_api_url,
                headers=self.headers,
                params={"username_or_id_or_url": username},
                verify=False
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
                st.error(f"No username found in profile data for {url} (API response: {top_data})")
                return None

            recent_post = self.scrape_recent_post_caption(url)

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
            
        except requests.exceptions.HTTPError as e:
            st.error(f"API Error {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            st.error(f"Error processing {url}: {str(e)}")
            return None

    def scrape_profiles(self, queries_df):
        accumulated_results = (
            st.session_state.scraped_profiles.to_dict('records')
            if not st.session_state.scraped_profiles.empty
            else []
        )
        
        queries = queries_df['Search Query'].tolist()
        progress_bar = st.progress(0)
        status_text = st.empty()
        
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
                    "api_key": self.serpapi_key,
                    "hl": "en",
                    "gl": "us",
                    "num": 5
                })
                serp_results = search.get_dict()
                
                if 'organic_results' in serp_results:
                    for item in serp_results['organic_results']:
                        url = item.get('link', '')
                        if "instagram.com/" in url:
                            try:
                                clean_url = url.split('?')[0].rstrip('/')
                                if not any(p['profile_url'] == clean_url for p in accumulated_results):
                                    profile_data = self.scrape_profile_details(clean_url)
                                    if profile_data:
                                        accumulated_results.append({
                                            "Query": query,
                                            **profile_data
                                        })
                                        time.sleep(random.uniform(1, 3))
                            except Exception as e:
                                st.warning(f"Error processing {url}: {str(e)}")
                
                st.session_state.scraped_profiles = pd.DataFrame(accumulated_results)
                
            except Exception as e:
                st.warning(f"Error processing query: {str(e)}")
        
        progress_bar.empty()
        status_text.empty()
        return pd.DataFrame(accumulated_results) 