@echo off
setlocal enabledelayedexpansion
title BoneSuppression AI - Quick Updater
color 0f

echo ======================================================================
echo   BoneSuppression AI - انتقال خودکار وزن‌های مدل از نسخه قبلی
echo   بیمارستان بوعلی مریوان - شبکه بهداشت و درمان مریوان
echo ======================================================================
echo.

set "TARGET_DIR=%~dp0_internal\weights"
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

if exist "%TARGET_DIR%\bone_suppression.ts" (
    echo [OK] وزن‌های مدل در این پوشه موجود هستند. نیازی به کپی نیست.
    goto launch
)

echo در حال جستجوی وزن‌های مدل در پوشه‌های نسخه قبلی...

set "FOUND="
for %%P in (
    "%~dp0..\BoneSuppressionAI\_internal\weights"
    "%~dp0..\BoneSuppressionAI\weights"
    "%~dp0..\weights"
    "%USERPROFILE%\Downloads\BoneSuppressionAI\_internal\weights"
    "%USERPROFILE%\Downloads\BoneSuppressionAI\weights"
    "%USERPROFILE%\Desktop\BoneSuppressionAI\_internal\weights"
    "C:\BoneSuppressionAI\_internal\weights"
    "D:\BoneSuppressionAI\_internal\weights"
) do (
    if exist "%%~fP\bone_suppression.ts" (
        set "FOUND=%%~fP"
        goto copy_weights
    )
)

:prompt_manual
echo.
echo [!] مسیر خودکار فایل‌های قبلی یافت نشد.
echo لطفاً پوشه weights از نسخه قبلی را درون همین پوشه یا درون _internal کپی نمایید.
pause
goto launch

:copy_weights
echo.
echo [✓] وزن‌های مدل در مسیر زیر یافت شدند:
echo     !FOUND!
echo.
echo در حال کپی مدل‌ها به نسخه جدید (چند ثانیه)...
copy /y "!FOUND!\bone_suppression.ts" "%TARGET_DIR%\" >nul
copy /y "!FOUND!\lung_component_suppression.ts" "%TARGET_DIR%\" >nul
echo [✓] کپی با موفقیت انجام شد!
echo.

:launch
echo ======================================================================
echo اجرای BoneSuppression AI...
echo ======================================================================
if exist "%~dp0BoneSuppressionAI.exe" (
    start "" "%~dp0BoneSuppressionAI.exe"
)
exit /b 0
