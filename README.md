# Instagram Pro Scrapper

A powerful Instagram automation and scraping tool built with Python. This tool provides advanced features for Instagram data collection, contact extraction, and email outreach automation with AI-powered personalization.

## Features

- 🔍 Instagram profile discovery based on location and business type
- 📊 Profile data scraping and automated analysis
- 📧 AI-powered email personalization and automation
- 📱 Contact details extraction (emails, phones, websites)
- 🧠 OpenAI GPT-4 integration for intelligent content generation
- 🌐 Location-based targeting with global support
- 📈 Profile scoring and prioritization
- 📬 Email response monitoring and handling
- 🚀 Streamlit-based user interface
- ⚡ FastAPI backend for webhooks and API integration

## Prerequisites

Before you begin, ensure you have the following:

- Python 3.8 or higher
- API keys for:
  - [SerpAPI](https://serpapi.com/) (for Google search functionality)
  - [OpenAI API](https://openai.com/api/) (for GPT-4 integration)
  - [RapidAPI](https://rapidapi.com/) (for Instagram data access)
  - [SendGrid](https://sendgrid.com/) (for email sending)
- Zoho Mail account (optional, for email response handling)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Instagram-Pro-Scrapper.git
cd Instagram-Pro-Scrapper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and credentials
```

## Usage

1. Start the FastAPI backend for webhook handling:
```bash
python fastapi_backend.py
```

2. Run the Streamlit interface:
```bash
streamlit run scrapper.py
```

3. Follow the step-by-step workflow in the UI:
   - Upload a CSV with target locations and business categories
   - Generate search queries using AI
   - Scrape Instagram profiles
   - Analyze and filter profiles
   - Send personalized emails to discovered contacts
   - Monitor email responses

## Configuration

- **API Keys**: Add your API keys to the `.env` file
- **Email Templates**: Customize templates using the built-in editor
- **Business Context**: Train the AI with your business information for better personalization
- **Location Targeting**: Specify target locations in your CSV file
- **Email Settings**: Configure SendGrid and Zoho settings in the UI

## CSV Format

Your input CSV should contain these columns:
```
Venue Category,Location
Dropshipping Business,Toronto, Ontario
E-commerce Store,Vancouver, British Columbia
```

## Security Note

- Never commit your `.env` file containing API keys
- Always use the `.gitignore` file to exclude sensitive information
- Regularly rotate your API keys for better security
- Respect Instagram's terms of service and rate limits
- Follow email marketing regulations and best practices

## Troubleshooting

- If geocoding fails, check your internet connection or try a different location format
- API errors may indicate rate limiting - try again after waiting
- For SendGrid issues, verify your API key and sender authentication
- Error logs are stored in `app.log` for debugging

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - See LICENSE file for details

## Author

Created by @yourusername 
