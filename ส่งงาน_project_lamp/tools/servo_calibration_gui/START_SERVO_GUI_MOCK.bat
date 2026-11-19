@echo off
setlocal
cd /d "%~dp0\..\.."
python -m tools.servo_calibration_gui.app --mock
if errorlevel 1 pause
endlocal
