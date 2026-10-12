@echo off
setlocal
set "DY_DEVICE_PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%DY_DEVICE_PYTHON%" (
  echo Python 3.13 was not found at the known B-machine location.
  echo %DY_DEVICE_PYTHON%
  pause
  exit /b 1
)
"%DY_DEVICE_PYTHON%" "%~dp0collect_device_connections.py"
echo.
pause
endlocal
