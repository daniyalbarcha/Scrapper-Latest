# Instagram Pro Scrapper

A powerful Instagram automation and scraping tool built with Python. This tool provides advanced features for Instagram data collection and analysis.

## Features

- Profile data scraping
- Email management and automation
- Streamlit-based user interface
- FastAPI backend integration
- Secure credential management
- Business profile analysis
- Automated email responses

## Installation

1. Clone the repository:
```bash
git clone https://github.com/daniyalbarcha/Instagram-Pro-Scrapper.git
cd Instagram-Pro-Scrapper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

## Usage

1. Start the FastAPI backend:
```bash
python fastapi_backend.py
```

2. Run the Streamlit interface:
```bash
streamlit run scrapper.py
```

## Configuration

- Configure your settings in `settings.json`
- Email templates can be customized in `default_email_template.txt`
- Environment variables should be set in `.env` file

## Security Note

- Never commit your `.env` file
- Keep your API keys and credentials secure
- Use the provided `.env.example` as a template

## License

MIT License - See LICENSE file for details

## Author

Created by @daniyalbarcha 
