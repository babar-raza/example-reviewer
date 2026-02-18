@echo off
REM Task C: Mini Rehearsal Script for Telemetry Investigation (Windows)
REM
REM This script runs a mini rehearsal to test the telemetry API and strict validator
REM DB wiring end-to-end.
REM
REM USAGE:
REM   tools\run_telemetry_investigation_rehearsal.bat

echo =========================================
echo Telemetry Investigation Mini Rehearsal
echo =========================================
echo.

REM Step 1: Run tests
echo [Step 1] Running tests...
python -m pytest -q
if errorlevel 1 (
    echo [WARN] Tests failed, continuing anyway...
)
echo.

REM Step 2: Run pipeline with safe workspace
echo [Step 2] Running pipeline with safe workspace...
echo Command: python -m src.cli.main run --family zip --config config/global_strict_context.json ^
echo   --safe-workspace --use-workspace-copy --no-dry-run --skip-llm-fixes --max-examples 5 --verbose
echo.

python -m src.cli.main run --family zip --config config/global_strict_context.json ^
  --safe-workspace --use-workspace-copy --no-dry-run --skip-llm-fixes --max-examples 5 --verbose > temp_run_output.txt 2>&1

type temp_run_output.txt
echo.

REM Extract RUN_ID from output
for /f "tokens=2 delims=: " %%i in ('findstr /C:"RUN_ID:" temp_run_output.txt') do set RUN_ID=%%i

if "%RUN_ID%"=="" (
    echo [ERROR] Could not extract RUN_ID from pipeline output
    del temp_run_output.txt
    exit /b 1
)

echo [INFO] Captured RUN_ID: %RUN_ID%
echo.

REM Extract DB_PATH from output
for /f "tokens=2* delims=: " %%i in ('findstr /C:"DB_PATH:" temp_run_output.txt') do set DB_PATH=%%i

if "%DB_PATH%"=="" (
    echo [WARN] Could not extract DB_PATH from pipeline output, will use auto-location
    set DB_PATH_ARG=
) else (
    echo [INFO] Captured DB_PATH: %DB_PATH%
    set DB_PATH_ARG=--db-path "%DB_PATH%"
)
echo.

del temp_run_output.txt

REM Create output directory
if not exist reports\telemetry_investigation mkdir reports\telemetry_investigation

REM Step 3: Run strict validator
echo [Step 3] Running strict context validator...
if "%DB_PATH_ARG%"=="" (
    python tools\validate_strict_context_mode.py --run-id %RUN_ID% ^
      --output reports\telemetry_investigation\validation_report.json
) else (
    python tools\validate_strict_context_mode.py --run-id %RUN_ID% %DB_PATH_ARG% ^
      --output reports\telemetry_investigation\validation_report.json
)
echo.

REM Step 4: Run telemetry verify
echo [Step 4] Running telemetry verify...
if "%TELEMETRY_URL%"=="" set TELEMETRY_URL=http://localhost:8765
echo Telemetry API URL: %TELEMETRY_URL%

python -m src.cli.main telemetry-verify --run-id %RUN_ID% --telemetry-url %TELEMETRY_URL% ^
  > reports\telemetry_investigation\telemetry_verify_output.txt 2>&1
if errorlevel 1 (
    echo [WARN] Telemetry verify failed or API not available
    echo Output saved to reports\telemetry_investigation\telemetry_verify_output.txt
)
echo.

REM Step 5: Evidence summary
echo [Step 5] Evidence collection complete
echo   - RUN_ID: %RUN_ID%
echo   - DB_PATH: %DB_PATH%
echo   - Validation report: reports\telemetry_investigation\validation_report.json
echo   - Telemetry verify output: reports\telemetry_investigation\telemetry_verify_output.txt
echo.

echo =========================================
echo Rehearsal Complete
echo =========================================
