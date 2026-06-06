@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
    echo Python launcher "py" was not found.
    pause
    exit /b 1
)

py -c "import PIL, numpy, cv2" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    py -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Dependency installation failed.
        pause
        exit /b 1
    )
)

py screenshot_tool.py
if errorlevel 1 pause
