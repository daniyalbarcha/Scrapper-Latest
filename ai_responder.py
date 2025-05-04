import openai
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
from settings_manager import SettingsManager

class AIResponder:
    def __init__(self, openai_api_key):
        self.openai_api_key = openai_api_key
        self.business_context = {}
        self.settings_manager = SettingsManager()  # Initialize settings manager
        openai.api_key = openai_api_key  # Set OpenAI key

    def deepseek_chat(self, prompt, system_prompt=None, temperature=0.7, json_mode=False):
        """
        Renamed to 'deepseek_chat' for minimal changes, but internally uses ChatGPT (GPT-4).
        """
        if not self.openai_api_key:
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

    def train_from_website(self, website_url):
        """
        Analyze website content to train the AI for email responses.
        
        Args:
            website_url (str): URL of the website to analyze
        Returns:
            bool: True if training was successful, False otherwise
        """
        try:
            # Validate and clean the URL
            if not website_url.startswith(('http://', 'https://')):
                website_url = 'https://' + website_url

            # Set up headers to mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }

            # Fetch website content with timeout and headers
            response = requests.get(
                website_url,
                headers=headers,
                timeout=10,
                verify=False  # Disable SSL verification
            )
            response.raise_for_status()  # Raise an exception for bad status codes
            
            # Check if we got HTML content
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                st.error(f"Invalid content type received: {content_type}. Expected HTML content.")
                return False

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract relevant content (main text, services, etc.)
            # Get text from common content areas
            content_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'section', 'article'])
            content_text = []
            
            for element in content_elements:
                # Skip elements with no text or navigation/footer/header elements
                if (element.text.strip() and 
                    not element.find_parent(['nav', 'footer', 'header']) and
                    'copyright' not in element.get('class', [])):
                    content_text.append(element.text.strip())

            # Get meta description and title
            meta_desc = soup.find('meta', {'name': ['description', 'Description']})
            meta_desc = meta_desc['content'] if meta_desc else ''
            
            title = soup.title.text if soup.title else ''
            
            # Combine content
            content = {
                'text': ' '.join(content_text),
                'title': title,
                'meta_description': meta_desc
            }
            
            # Create a system prompt for training
            training_prompt = f"""
            Analyze this website content and create a comprehensive business profile:
            Title: {content['title']}
            Description: {content['meta_description']}
            Content: {content['text'][:2000]}  # Limiting content length for API
            
            Extract and format as JSON:
            {{
                "main_services": "list of main services/products offered",
                "company_tone": "analysis of company's tone and style",
                "value_propositions": "key value propositions and benefits",
                "target_audience": "identified target audience segments",
                "industry": "primary industry or business sector"
            }}
            """
            
            # Get AI analysis
            analysis = self.deepseek_chat(
                training_prompt,
                system_prompt="You are a business analyst. Analyze the website content and provide structured insights. Return only valid JSON.",
                temperature=0.3
            )
            
            if not analysis:
                st.error("Failed to analyze website content with AI.")
                return False
            
            try:
                # Validate the analysis is proper JSON
                analysis_json = json.loads(analysis)
                
                # Extract company name from title or content
                company_name = content['title'].split('-')[0].strip() if content['title'] else ''
                
                # Store the context for email generation
                self.business_context = {
                    'website_analysis': analysis_json,
                    'source': 'website',
                    'url': website_url,
                    'raw_content': {
                        'title': content['title'],
                        'description': content['meta_description']
                    },
                    'company_name': company_name
                }
                
                # Update settings manager with business context and company name
                self.settings_manager.update_settings(company_name=company_name)
                self.settings_manager.update_business_context(self.business_context)
                
                # Update session state with business context
                st.session_state['business_context'] = self.business_context
                
                st.success("✅ Website analysis completed successfully!")
                return True
                
            except json.JSONDecodeError:
                st.error("Failed to parse AI analysis results.")
                return False
                
        except requests.exceptions.SSLError:
            st.error("SSL Certificate verification failed. The website might not be secure.")
            return False
        except requests.exceptions.ConnectionError as e:
            st.error(f"Failed to connect to the website. Please check if the URL is correct and the website is accessible.\nError: {str(e)}")
            return False
        except requests.exceptions.Timeout:
            st.error("Request timed out. The website took too long to respond.")
            return False
        except requests.exceptions.RequestException as e:
            st.error(f"An error occurred while fetching the website: {str(e)}")
            return False
        except Exception as e:
            st.error(f"Website analysis failed: {str(e)}")
            return False

    def train_from_csv(self, csv_file):
        """
        Train the AI using business information from a CSV file.
        
        Args:
            csv_file: CSV file containing business information in field,value format
        Returns:
            bool: True if training was successful, False otherwise
        """
        try:
            # Read CSV file
            df = pd.read_csv(csv_file)
            
            # Convert the field,value format to a dictionary
            settings_dict = dict(zip(df['field'], df['value']))
            
            # Extract required values
            company_name = settings_dict.get('company_name', '')
            company_tone = settings_dict.get('company_tone', 'Professional')
            
            # Normalize company tone
            if company_tone.lower() == 'professional':
                company_tone = 'Professional'
            elif company_tone.lower() == 'casual':
                company_tone = 'Casual'
            elif company_tone.lower() == 'friendly':
                company_tone = 'Friendly'
            elif company_tone.lower() == 'formal':
                company_tone = 'Formal'
            else:
                company_tone = 'Professional'  # Default value
            
            # Create a consolidated business profile
            training_prompt = f"""
            Analyze this business information and create a comprehensive profile:
            Company Name: {settings_dict.get('company_name', '')}
            Description: {settings_dict.get('company_description', '')}
            Services: {settings_dict.get('company_services', '')}
            Target Audience: {settings_dict.get('target_audience', '')}
            Value Proposition: {settings_dict.get('value_proposition', '')}
            Success Stories: {settings_dict.get('success_stories', '')}
            
            Create a structured summary of:
            1. Business offerings and services
            2. Target audience and customer segments
            3. Communication style and brand voice
            4. Key differentiators and value propositions
            """
            
            # Get AI analysis
            analysis = self.deepseek_chat(training_prompt, temperature=0.3)
            
            # Store the context for email generation
            self.business_context = {
                'csv_analysis': analysis,
                'source': 'csv',
                'data': settings_dict,
                'company_name': company_name
            }
            
            # Update settings manager with all relevant settings
            self.settings_manager.update_settings(
                company_name=company_name,
                company_tone=company_tone,
                company_description=settings_dict.get('company_description', ''),
                company_services=settings_dict.get('company_services', ''),
                email_signature=settings_dict.get('email_signature', ''),
                response_email=settings_dict.get('response_email', ''),
                cold_email=settings_dict.get('cold_email', '')
            )
            self.settings_manager.update_business_context(self.business_context)
            
            # Update session state with business context
            st.session_state['business_context'] = self.business_context
            
            return True
            
        except Exception as e:
            st.error(f"CSV analysis failed: {str(e)}")
            return False

    def generate_personalized_email(self, bio, username, recent_post="", custom_subject=None, custom_body=None):
        """Generate a personalized email using business context if available."""
        # Get business context if available
        business_context = ""
        if hasattr(self, 'business_context'):
            if self.business_context.get('source') == 'website':
                business_context = f"\nBusiness Context:\n{self.business_context.get('website_analysis', '')}"
            elif self.business_context.get('source') == 'csv':
                business_context = f"\nBusiness Context:\n{self.business_context.get('csv_analysis', '')}"

        # Add company information to business context
        company_info = """
        Company Name: {company_name}
        Company Description: {company_description}
        Services: {services}
        Email Signature: {signature}
        """.format(
            company_name=self.settings_manager.company_name or "Our Company",
            company_description=self.settings_manager.company_description or "",
            services=self.settings_manager.company_services or "",
            signature=self.settings_manager.email_signature or "Best regards"
        )
        business_context += "\n" + company_info

        if custom_subject and custom_body:
            # Extract key information from bio for better personalization
            prompt = f"""
            Analyze this profile information and extract key details for email personalization:
            - Username: {username}
            - Bio: {bio}
            - Recent Post: {recent_post}
            {business_context}

            Return ONLY a JSON object with these fields:
            {{
                "role": "their professional role/position (fallback to 'professional' or industry-specific term if unclear)",
                "industry": "their industry/business type (fallback to 'your industry' only if completely unclear)",
                "achievements": "notable achievements/stats (omit if none found)",
                "unique_point": "something unique about them (fallback to something from their content if no standout point)",
                "interests": "their apparent interests or focus areas",
                "style": "their communication style (professional, casual, technical, etc.)"
            }}
            """
            
            # Get profile details
            details_response = self.deepseek_chat(
                prompt=prompt,
                system_prompt="Extract profile information and provide natural fallbacks. Never return empty fields.",
                temperature=0.3,
                json_mode=True
            )
            
            try:
                # Parse the profile details
                profile_details = json.loads(details_response) if details_response else {
                    "role": "professional",
                    "industry": "your industry",
                    "achievements": "",
                    "unique_point": "your content",
                    "interests": "business growth",
                    "style": "professional"
                }

                # Now use these details to rewrite the template while maintaining the core message
                rewrite_prompt = f"""
                I need you to rewrite an email template while maintaining its core message and intent, but making it unique and personalized.

                Original Template Subject: {custom_subject}
                Original Template Body: {custom_body}

                Profile Details:
                - Role: {profile_details['role']}
                - Industry: {profile_details['industry']}
                - Achievements: {profile_details['achievements']}
                - Unique Point: {profile_details['unique_point']}
                - Interests: {profile_details['interests']}
                - Style: {profile_details['style']}

                {business_context}

                Requirements:
                1. Keep the same core message and marketing pitch
                2. Match their communication style ({profile_details['style']})
                3. Reference their specific interests and unique points
                4. Make the language feel natural and conversational
                5. Maintain professionalism while being personable
                6. Keep similar length but use different phrasing
                7. Include a clear call-to-action
                8. If business context is available, incorporate relevant aspects of our business that align with their profile
                9. Return ONLY two lines:
                   First line: Subject: [your subject]
                   Second line: [your email body in HTML format]
                10. NEVER use placeholders like [Your Name] or [Company Name]. Instead, use actual values from the business context.
                11. Always end with the proper signature from business context, or "Best regards, [Company Name] Team" if no signature is provided.

                Do not include any other text or explanations.
                """

                # Get the rewritten email
                rewrite_response = self.deepseek_chat(
                    prompt=rewrite_prompt,
                    system_prompt=f"""You are an expert email copywriter who creates unique, personalized variations while maintaining the core message.
                    Company Name: {self.settings_manager.company_name or 'Our Company'}
                    Signature: {self.settings_manager.email_signature or f'Best regards,{chr(10)}{self.settings_manager.company_name} Team'}
                    Never use placeholders - always use actual company name and signature.""",
                    temperature=0.7
                )

                if rewrite_response:
                    lines = rewrite_response.strip().split('\n')
                    if len(lines) >= 2 and lines[0].lower().startswith('subject:'):
                        personalized_subject = lines[0].replace('Subject:', '').strip()
                        personalized_body = '\n'.join(lines[1:]).strip()
                        
                        # Ensure username is replaced in both subject and body
                        personalized_subject = personalized_subject.replace("{username}", username)
                        personalized_body = personalized_body.replace("{username}", username)
                        
                        # Replace any remaining placeholders with actual values
                        replacements = {
                            "[Your Name]": self.settings_manager.company_name or "Our Company",
                            "[Company Name]": self.settings_manager.company_name or "Our Company",
                            "[COMPANY NAME]": self.settings_manager.company_name or "Our Company",
                            "[company name]": self.settings_manager.company_name or "Our Company",
                            "[Name]": self.settings_manager.company_name or "Our Company",
                            "[name]": self.settings_manager.company_name or "Our Company",
                            "[Signature]": self.settings_manager.email_signature or f"Best regards,\n{self.settings_manager.company_name} Team",
                            "[signature]": self.settings_manager.email_signature or f"Best regards,\n{self.settings_manager.company_name} Team"
                        }
                        
                        for placeholder, value in replacements.items():
                            personalized_subject = personalized_subject.replace(placeholder, value)
                            personalized_body = personalized_body.replace(placeholder, value)
                        
                        return personalized_subject, personalized_body

                # Fallback to template with basic personalization if rewrite fails
                replacements = {
                    "{username}": username,
                    "{role}": profile_details["role"],
                    "{industry}": profile_details["industry"],
                    "{achievements}": profile_details["achievements"],
                    "{unique_point}": profile_details["unique_point"],
                    "[Your Name]": self.settings_manager.company_name or "Our Company",
                    "[Company Name]": self.settings_manager.company_name or "Our Company",
                    "[COMPANY NAME]": self.settings_manager.company_name or "Our Company",
                    "[company name]": self.settings_manager.company_name or "Our Company",
                    "[Name]": self.settings_manager.company_name or "Our Company",
                    "[name]": self.settings_manager.company_name or "Our Company",
                    "[Signature]": self.settings_manager.email_signature or f"Best regards,\n{self.settings_manager.company_name} Team",
                    "[signature]": self.settings_manager.email_signature or f"Best regards,\n{self.settings_manager.company_name} Team"
                }
                
                personalized_subject = custom_subject
                personalized_body = custom_body
                
                # Handle achievements specially - if empty, remove the entire sentence containing it
                if not profile_details["achievements"]:
                    personalized_body = "\n".join([
                        line for line in personalized_body.split('\n')
                        if "{achievements}" not in line
                    ])
                
                # Apply the replacements
                for placeholder, value in replacements.items():
                    personalized_subject = personalized_subject.replace(placeholder, value)
                    personalized_body = personalized_body.replace(placeholder, value)
                
                return personalized_subject, personalized_body
                
            except json.JSONDecodeError:
                # Fallback to simple personalization if JSON parsing fails
                personalized_subject = custom_subject.replace("{username}", username)
                personalized_body = custom_body.replace("{username}", username)
                
                # Replace any remaining placeholders
                replacements = {
                    "[Your Name]": self.settings_manager.company_name or "Our Company",
                    "[Company Name]": self.settings_manager.company_name or "Our Company",
                    "[COMPANY NAME]": self.settings_manager.company_name or "Our Company",
                    "[company name]": self.settings_manager.company_name or "Our Company",
                    "[Name]": self.settings_manager.company_name or "Our Company",
                    "[name]": self.settings_manager.company_name or "Our Company",
                    "[Signature]": self.settings_manager.email_signature or f"Best regards,\n{self.settings_manager.company_name} Team",
                    "[signature]": self.settings_manager.email_signature or f"Best regards,\n{self.settings_manager.company_name} Team"
                }
                
                for placeholder, value in replacements.items():
                    personalized_subject = personalized_subject.replace(placeholder, value)
                    personalized_body = personalized_body.replace(placeholder, value)
                
                return personalized_subject, personalized_body
                
        else:
            # Default email generation if no template provided
            prompt = f"""
            Write a short, friendly outreach email referencing:
            - Username: {username}
            - Bio: {bio}
            - Recent Post: {recent_post}
            {business_context}

            Requirements:
            1. Make it unique and personal to their profile
            2. Reference specific details from their bio or post
            3. Keep it natural and conversational
            4. Include a clear call-to-action
            5. Return only two lines:
               First line: Subject: [your subject]
               Second line: [your email body in HTML format]
            6. No placeholders or variables - use actual company name and signature
            7. Keep language natural and professional
            8. End with proper signature from business context
            """

            system_prompt = f"""You are an expert email copywriter who creates unique, personalized emails for each recipient.
            Company Name: {self.settings_manager.company_name or 'Our Company'}
            Signature: {self.settings_manager.email_signature or f'Best regards,{chr(10)}{self.settings_manager.company_name} Team'}
            Never use placeholders - always use actual company name and signature."""

            response = self.deepseek_chat(prompt, system_prompt=system_prompt, temperature=0.7)
            if not response:
                return "Hello from Our Team", "<p>Could not generate personalized email.</p>"

            lines = response.strip().split("\n")
            if lines and lines[0].lower().startswith("subject:"):
                subject_line = lines[0].replace("Subject:", "").strip()
                html_body = "\n".join(lines[1:]).strip()
            else:
                subject_line = "Hello from Our Team"
                html_body = response

            # Replace any remaining placeholders
            replacements = {
                "[Your Name]": self.settings_manager.company_name or "Our Company",
                "[Company Name]": self.settings_manager.company_name or "Our Company",
                "[COMPANY NAME]": self.settings_manager.company_name or "Our Company",
                "[company name]": self.settings_manager.company_name or "Our Company",
                "[Name]": self.settings_manager.company_name or "Our Company",
                "[name]": self.settings_manager.company_name or "Our Company",
                "[Signature]": self.settings_manager.email_signature or f"Best regards,\n{self.settings_manager.company_name} Team",
                "[signature]": self.settings_manager.email_signature or f"Best regards,\n{self.settings_manager.company_name} Team"
            }
            
            for placeholder, value in replacements.items():
                subject_line = subject_line.replace(placeholder, value)
                html_body = html_body.replace(placeholder, value)

            return subject_line, html_body