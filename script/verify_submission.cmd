@echo off
setlocal
cd /d "%~dp0.."
python --version
if errorlevel 1 exit /b 1
python script/run_phase1.py
if errorlevel 1 exit /b 1
python script/run_corruption_flow.py
if errorlevel 1 exit /b 1
echo Baseline and corruption flow completed. For real agent evidence run python script/run_agent_demo.py
