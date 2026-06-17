@echo off
echo.
echo ========================================
echo   Moomoo ^> Notion Sync
echo ========================================
echo.

:: Make sure Futu OpenD is running before continuing
echo Make sure Futu OpenD is open and logged in!
echo.
pause

:: Run the sync script
python "C:\Users\ccalv\Documents\GitHub Repos\Notion-Investment-Tracker\moomoo_notion_sync.py"

echo.
pause