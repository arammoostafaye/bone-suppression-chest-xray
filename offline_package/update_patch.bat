@echo off
setlocal enabledelayedexpansion
title BoneSuppression AI - Multi-AI Patch Updater (v2.3.0)
color 0f

set "URL1=https://github.com/arammoostafaye/bone-suppression-chest-xray/releases/download/v2.3.0/BoneSuppressionAI-v2.3-Update-Only.zip"
set "URL2=https://huggingface.co/arammoostafaye/bone-suppression-desktop/resolve/main/BoneSuppressionAI-v2.3-Update-Only.zip"
set "OUT=%~dp0BoneSuppressionAI-v2.3-Update-Only.zip"

echo ======================================================================
echo   BoneSuppression AI - بروزرسانی چندمدله رادیولوژی (نگارش جدید v2.3.0)
echo   اضافه‌شدن: ۱. غربالگری شکستگی استخوان  ۲. غربالگری ۱۸ بیماری ریه
echo   توسعه‌دهنده: آرام مصطفائی - بیمارستان بوعلی مریوان
echo ======================================================================
echo.
echo  در حال دریافت پکیج سبک آپدیت (~280 مگابایت)...
echo  (فایل‌های حجیم ۸۳۵ مگابایتی قبلی شما حفظ می‌شوند و مجدداً دانلود نخواهند شد)
echo.

set N=0
:loop
set /a N+=1
if %N% GTR 10 (
  echo.
  echo  تعداد دفعات خطا بیش از حد مجاز شد. لطفاً اتصال اینترنت را بررسی کنید.
  pause
  exit /b 1
)
echo  در حال اتصال و دانلود (تلاش %N%) ...
curl -L -C - --retry 5 --retry-all-errors --retry-delay 2 --connect-timeout 20 -o "%OUT%" "%URL1%"
if errorlevel 1 curl -L -C - --retry 5 --retry-all-errors --retry-delay 2 --connect-timeout 20 -o "%OUT%" "%URL2%"

if not exist "%OUT%" goto loop

echo.
echo  [✓] دریافت کامل شد. در حال استخراج بروزرسانی...
powershell -NoProfile -Command "Expand-Archive -LiteralPath '%OUT%' -DestinationPath '%~dp0' -Force"

if exist "%~dp0BoneSuppressionAI\BoneSuppressionAI.exe" (
    set "APPDIR=%~dp0BoneSuppressionAI"
) else (
    set "APPDIR=%~dp0"
)

echo.
echo  [✓] اتصال و انتقال مدل‌های قبلی به پوشه برنامه...
cd /d "%APPDIR%"
if exist "apply_update.bat" call "apply_update.bat"
if exist "BoneSuppressionAI.exe" start "" "BoneSuppressionAI.exe"
exit /b 0
