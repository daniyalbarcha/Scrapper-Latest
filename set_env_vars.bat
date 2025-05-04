@echo off
echo ============================================================
echo INSTAGRAM PRO SCRAPPER - SET ENVIRONMENT VARIABLES
echo ============================================================
echo.
echo This batch file will set environment variables for API keys.
echo These will only last for the current terminal session.
echo.

set /p OPENAI_KEY=Enter your OpenAI API Key: 
set /p SERPAPI_KEY=Enter your SerpAPI Key: 
set /p RAPIDAPI_KEY=Enter your RapidAPI Key: 

echo.
echo Setting environment variables...
echo.

set OPENAI_API_KEY=%OPENAI_KEY%
set SERPAPI_API_KEY=%SERPAPI_KEY%
set RAPIDAPI_KEY=%RAPIDAPI_KEY%

echo Environment variables set:
echo.
echo OPENAI_API_KEY=%OPENAI_API_KEY%
echo SERPAPI_API_KEY=%SERPAPI_API_KEY%
echo RAPIDAPI_KEY=%RAPIDAPI_KEY%
echo.
echo ============================================================
echo.
echo Now run your application in this SAME terminal window.
echo These settings will be lost if you close this window.
echo.
echo Press any key to continue...
pause > nul 