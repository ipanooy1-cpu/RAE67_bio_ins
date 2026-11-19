@echo off
setlocal
cd /d "%~dp0\..\.."
python -m tools.servo_calibration_gui.app
if errorlevel 1 (
  echo.
  echo โปรแกรมปิดด้วยข้อผิดพลาด กรุณาอ่าน README_TH.md
  pause
)
endlocal
