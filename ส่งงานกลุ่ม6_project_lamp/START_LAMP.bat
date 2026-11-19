@echo off
setlocal
title Emotion Robotic Lamp - ROS 2 Jazzy
cd /d "%~dp0"

echo ==========================================
echo    EMOTION ROBOTIC LAMP - 4 DOF
echo ==========================================
echo.

docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Please start Docker Desktop.
    pause
    exit /b 1
)

if not exist "workspace\src\lamp_cad_4dof" (
    echo Extracting workspace...
    if not exist "workspace" mkdir "workspace"

    powershell -NoProfile -Command "Expand-Archive -LiteralPath 'Emotion_Lamp_Workspace_Clean.zip' -DestinationPath 'workspace' -Force"

    if errorlevel 1 (
        echo ERROR: Extracting workspace failed.
        pause
        exit /b 1
    )
)

if not exist "workspace\src\lamp_cad_4dof" (
    echo ERROR: CAD package not found after extraction.
    pause
    exit /b 1
)

echo Starting Docker...
docker compose up -d --build

if errorlevel 1 (
    echo ERROR: Docker startup failed.
    pause
    exit /b 1
)

echo Starting ROS 2 + CAD + CPG + RViz2...
docker cp run_lamp.sh emotion_lamp_windows:/tmp/run_lamp.sh

if errorlevel 1 (
    echo ERROR: run_lamp.sh not found.
    pause
    exit /b 1
)

docker compose exec emotion_lamp bash /tmp/run_lamp.sh

pause
