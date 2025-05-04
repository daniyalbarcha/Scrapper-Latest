# GitHub Upload Instructions

This document provides instructions for uploading the Instagram Pro Scrapper to your GitHub account.

## Preparation Checklist

✅ Added `.env.example` file with template environment variables  
✅ Added proper `.gitignore` to exclude sensitive files  
✅ Created an improved `README.md` with detailed instructions  
✅ Added `LICENSE` file with MIT License  
✅ Updated `requirements.txt` to include all dependencies  
✅ Created push script (`push_to_github.ps1`) to help with upload  

## Steps to Upload

1. **Setup GitHub Repository**
   - Go to [GitHub](https://github.com/) and sign in
   - Click the "+" in the top right corner and select "New repository"
   - Name your repository (recommended: "Instagram-Pro-Scrapper")
   - Add a description if desired
   - Choose public or private visibility
   - Do NOT initialize with README, .gitignore, or license (we already have these)
   - Click "Create repository"

2. **Check for Sensitive Data**
   - Make sure you don't have a `.env` file with real API keys
   - Verify no API keys or passwords are hardcoded in the scripts
   - Check `session_state.json` to ensure it doesn't contain sensitive information

3. **Use the Push Script**
   - Open PowerShell in your project directory
   - Run the script:
     ```
     .\push_to_github.ps1
     ```
   - When prompted, enter your GitHub repository URL (e.g., `https://github.com/yourusername/Instagram-Pro-Scrapper.git`)
   - Enter your commit message or accept the default

4. **Verify Upload**
   - Go to your GitHub repository page to verify all files were uploaded correctly
   - Check that sensitive files like `.env` and `session_state.json` were not uploaded

## After Upload

1. **Set Repository Description**
   - Add a short description to your repository
   - Add relevant topics (e.g., instagram, scraping, python, streamlit, fastapi)

2. **Enable GitHub Pages (Optional)**
   - Go to repository Settings → Pages
   - Select main branch as source
   - This will create a website for your project documentation

3. **Set Up Branch Protection (Optional)**
   - Go to Settings → Branches → Add rule
   - Protect your main branch to prevent accidental pushes

## Notes on API Keys and Security

All API keys should be stored in your `.env` file, which is excluded from GitHub by the `.gitignore` file. Users who clone your repository will need to:

1. Copy `.env.example` to `.env`
2. Add their own API keys in the `.env` file
3. Install the requirements using `pip install -r requirements.txt`

Never commit or push the following files to GitHub:
- `.env` (contains your API keys)
- `session_state.json` (may contain sensitive user data)
- Any log files with sensitive information

## Troubleshooting

If you encounter issues:

- **Authentication issues**: Make sure you've set up your Git authentication correctly (SSH key or personal access token)
- **Permission issues**: Ensure you have the right permissions for the repository
- **Large files**: If any files are too large, you might need to use Git LFS or exclude them

For more help with GitHub, refer to the [GitHub documentation](https://docs.github.com/en). 