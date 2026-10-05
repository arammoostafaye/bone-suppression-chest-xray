@echo off
setlocal enabledelayedexpansion
title BoneSuppression AI - Multi-AI Quick Updater (v2.3.0)
color 0f

echo ======================================================================
echo   BoneSuppression AI - انتقال و اتصال خودکار وزن‌های مدل قبلی
echo   بیمارستان بوعلی مریوان - شبکه بهداشت و درمان مریوان
echo ======================================================================
echo.

set "TARGET_DIR=%~dp0_internal\weights"
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

if exist "%TARGET_DIR%\bone_suppression.ts" (
    echo [OK] وزن‌های مدل حذف استخوان در این پوشه موجود هستند.
    goto check_new_models
)

echo در حال جستجوی وزن‌های مدل در پوشه‌های نسخه قبلی...

set "FOUND="
for %%P in (
    "%~dp0..\_internal\weights"
    "%~dp0..\weights"
    "%~dp0..\BoneSuppressionAI\_internal\weights"
    "%~dp0..\BoneSuppressionAI\weights"
    "%~dp0..\..\BoneSuppressionAI\_internal\weights"
    "%~dp0..\..\weights"
    "%USERPROFILE%\Downloads\BoneSuppressionAI\_internal\weights"
    "%USERPROFILE%\Downloads\BoneSuppressionAI\weights"
    "%USERPROFILE%\Desktop\BoneSuppressionAI\_internal\weights"
    "C:\BoneSuppressionAI\_internal\weights"
    "D:\BoneSuppressionAI\_internal\weights"
    "E:\BoneSuppressionAI\_internal\weights"
) do (
    if exist "%%~fP\bone_suppression.ts" (
        set "FOUND=%%~fP"
        goto copy_weights
    )
)

:prompt_manual
echo.
echo [!] مسیر خودکار فایل‌های قبلی یافت نشد.
echo اگر پوشه weights نسخه قبلی را دارید، آن را درون پوشه _internal کپی نمایید.
goto check_new_models

:copy_weights
echo.
echo [✓] وزن‌های مدل قبلی در مسیر زیر یافت شدند:
echo     !FOUND!
echo.
echo در حال کپی مدل‌های سنگین ۸۳۵ مگابایتی به نسخه جدید...
copy /y "!FOUND!\bone_suppression.ts" "%TARGET_DIR%\" >nul
copy /y "!FOUND!\lung_component_suppression.ts" "%TARGET_DIR%\" >nul
echo [✓] انتقال وزن‌های قبلی با موفقیت انجام شد!
echo.

:check_new_models
echo [✓] بررسی مدل‌های جدید شکستگی و ۱۸ بیماری ریه...
if not exist "%TARGET_DIR%\fracture_yolov8.onnx" (
    if exist "%~dp0weights\fracture_yolov8.onnx" copy /y "%~dp0weights\fracture_yolov8.onnx" "%TARGET_DIR%\" >nul
)
if not exist "%TARGET_DIR%\cxr_densenet18.ts" (
    if exist "%~dp0weights\cxr_densenet18.ts" copy /y "%~dp0weights\cxr_densenet18.ts" "%TARGET_DIR%\" >nul
)

:launch
echo ======================================================================
echo اجرای BoneSuppression AI (Multi-AI Workstation v2.3.0)...
echo ======================================================================
if exist "%~dp0BoneSuppressionAI.exe" (
    start "" "%~dp0BoneSuppressionAI.exe"
)
exit /b 0
