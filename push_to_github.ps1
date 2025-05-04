# Script to push code to GitHub
# Usage: .\push_to_github.ps1 [commit_message]

# Get commit message from args or set default
param (
    [string]$CommitMessage = "Updated code"
)

Write-Host "Preparing to push to GitHub..." -ForegroundColor Green

# Check if Git is installed
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Git is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# Check if .env file exists (make sure sensitive data isn't pushed)
if (Test-Path .env) {
    Write-Host "Warning: .env file detected with sensitive data" -ForegroundColor Yellow
    Write-Host "Checking if .env is in .gitignore..." -ForegroundColor Yellow
    
    $gitignore = Get-Content .gitignore -ErrorAction SilentlyContinue
    if (!($gitignore -contains ".env")) {
        Write-Host "Warning: .env is not in .gitignore! Please add it before continuing." -ForegroundColor Red
        $continue = Read-Host "Continue anyway? (y/n)"
        if ($continue -ne "y") {
            exit 1
        }
    } else {
        Write-Host ".env is correctly listed in .gitignore" -ForegroundColor Green
    }
}

# Check if repository is initialized
if (!(Test-Path .git)) {
    Write-Host "Git repository not found. Initializing..." -ForegroundColor Yellow
    git init
    
    # Ask for remote URL if not already set
    $remoteUrl = Read-Host "Enter your GitHub repository URL (e.g., https://github.com/username/repo.git)"
    if ($remoteUrl) {
        git remote add origin $remoteUrl
    } else {
        Write-Host "No remote URL provided. You'll need to add it manually later." -ForegroundColor Yellow
    }
}

# Stage, commit and push
Write-Host "Staging changes..." -ForegroundColor Green
git add .

Write-Host "Committing with message: $CommitMessage" -ForegroundColor Green
git commit -m $CommitMessage

$currentBranch = git rev-parse --abbrev-ref HEAD
Write-Host "Pushing to branch: $currentBranch" -ForegroundColor Green

# Try to push and handle if upstream is not set
$pushResult = git push origin $currentBranch 2>&1
if ($LASTEXITCODE -ne 0) {
    if ($pushResult -match "no upstream branch") {
        Write-Host "Setting upstream branch and pushing..." -ForegroundColor Yellow
        git push --set-upstream origin $currentBranch
    } else {
        Write-Host "Error pushing to GitHub: $pushResult" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Successfully pushed to GitHub!" -ForegroundColor Green 