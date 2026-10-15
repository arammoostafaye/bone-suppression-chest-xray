@echo off
setlocal enabledelayedexpansion
title BoneSuppression AI - Multi-AI Patch Updater (v2.7.0)
color 0f

set "URL1=https://github.com/arammoostafaye/bone-suppression-chest-xray/releases/download/v2.7.0/BoneSuppressionAI-v2.7.0-Update-Only.zip"
set "URL2=https://huggingface.co/arammoostafaye/bone-suppression-desktop/resolve/main/BoneSuppressionAI-v2.7.0-Update-Only.zip"
set "OUT=%~dp0BoneSuppressionAI-v2.7.0-Update-Only.zip"

echo ======================================================================
echo   BoneSuppression AI - بروزرسانی اتصال مستقیم به پکس مدال (نگارش v2.7.0)
echo   قابلیت‌های جدید:
echo     1. دریافت مستقیم تصاویر دایکام از پکس مدال بیمارستان با لینک پیامک/وب
echo     2. چینش و تحلیل هوشمند خودکار ۴ نمای استاندارد ماموگرافی
echo     3. مدیریت و پاک‌سازی هوشمند کش موقت جهت آزادسازی فضای درایو C
echo     4. موتور پیشرفته گزارش‌نویسی بالینی آکادمیک (Consultant-Grade)
echo   توسعه‌دهنده: آرام مصطفائی - بیمارستان بوعلی مریوان
echo ======================================================================
echo.
echo  در حال دریافت پکیج سبک آپدیت (~280 مگابایت)...
echo  (فایل‌های حجیم ۸۳۵ مگابایتی قبلی شما حفظ می‌شوند و مجدداً دانلود نخواهند شد)
echo.

set N=0
:loop
set /a N+=1
if %N% GTR 12 (
  echo.
  echo  خطا در برقراری ارتباط پایدار. لطفاً اتصال اینترنت را چک فرمایید.
  pause
  exit /b 1
)
echo  در حال دریافت فایل با قابلیت ادامه (Resume) - تلاش %N% ...
curl -L -C - --retry 5 --retry-all-errors --retry-delay 2 --connect-timeout 20 -o "%OUT%" "%URL1%"
if errorlevel 1 curl -L -C - --retry 5 --retry-all-errors --retry-delay 2 --connect-timeout 20 -o "%OUT%" "%URL2%"

if not exist "%OUT%" goto loop

REM Check file size (must be at least 250 MB)
for %%F in ("%OUT%") do set "FSIZE=%%~zF"
if !FSIZE! LSS 240000000 (
    echo  فایل به طور کامل دریافت نشده است (!FSIZE! بایت). در حال ادامه دانلود...
    goto loop
)

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
