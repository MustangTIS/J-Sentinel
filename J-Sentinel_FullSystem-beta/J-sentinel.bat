@echo off
setlocal
cd /d %~dp0

echo ==========================================
echo   J-Sentinel ～ 高度防災システム - Booter
echo ==========================================

:PYTHON_CHECK
echo [Step 1] Checking Python...
:: まず python を試す
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY=python
    goto :PYTHON_OK
)
:: だめなら py を試す
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY=py
    goto :PYTHON_OK
)

:: どちらもだめな場合
echo [Error] Python path is not found.
pause
exit /b

:PYTHON_OK
echo [Status] Using command: %PY%

:LIBRARY_CHECK
echo [Step 2] Checking Libraries...
:: 変数 %PY% を使ってチェック
%PY% -c "import psutil, requests, PIL, customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [Notice] Installing missing libraries...
    %PY% -m pip install --upgrade pip
    %PY% -m pip install psutil requests Pillow customtkinter --prefer-binary
)

:BOOT_MAIN
if exist "J-Sentinel_main.py" (
    echo [Step 3] Launching System...
    echo.
    
    :: 決定したコマンド (%PY%) で実行
    cmd /c %PY% "J-Sentinel_main.py"
    
    echo.
    echo ------------------------------------------
    echo [System] Process finished. Code: %errorlevel%
    echo ------------------------------------------
    pause
) else (
    echo [Error] J-Sentinel_main.py not found.
    pause
)

exit /b