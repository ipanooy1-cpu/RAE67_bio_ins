@echo off
setlocal
cd /d "%~dp0\..\.."
python -m pip install -r tools\servo_calibration_gui\requirements.txt
if errorlevel 1 (
  echo.
  echo ติดตั้งไม่สำเร็จ กรุณาตรวจอินเทอร์เน็ตและ Python
) else (
  echo.
  echo ติดตั้งสำเร็จแล้ว
)
pause
endlocal
