# Remove existing .git directory if it exists
if (Test-Path .git) {
    Remove-Item -Recurse -Force .git
}

# Initialize new repository
git init

# Add all files
git add .

# Commit changes
git commit -m "Initial commit with complete Instagram Pro Scrapper"

# Rename branch to main
git branch -M main

# Add remote origin
git remote add origin https://github.com/daniyalbarcha/Instagram-Pro-Scrapper.git

# Push to GitHub with force
git push -u origin main --force 