@echo off
chcp 65001 >nul
title Launch BoneSuppression AI Desktop
color 0f

if exist "BoneSuppressionAI.exe" (
    start "" "BoneSuppressionAI.exe"
    exit /b 0
)

if exist "BoneSuppressionAI\BoneSuppressionAI.exe" (
    start "" "BoneSuppressionAI\BoneSuppressionAI.exe"
    exit /b 0
)

if exist "dist\BoneSuppressionAI\BoneSuppressionAI.exe" (
    start "" "dist\BoneSuppressionAI\BoneSuppressionAI.exe"
    exit /b 0
)

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [خطا] پایتون یافت نشد. لطفاً ابتدا پایتون را نصب کنید یا فایل اجرایی کامپایل شده را اجرا فرمایید.
    pause
    exit /b 1
)

start "" pythonw BoneSuppression_Desktop.py
