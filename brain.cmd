@echo off
setlocal DisableDelayedExpansion
rem Portable second-brain resolver for cmd.exe. Installed copies locate the
rem vault at runtime; they never pin a checkout and never modify shell config.

set "BRAIN_CLI_VAULT="
set "BRAIN_VAULT_COUNT=0"
set "BRAIN_SCAN_NEEDS_VALUE=0"
set "BRAIN_SCAN_OPTIONS=1"
:brain_scan
if "%1"=="" goto brain_scan_done
if "%BRAIN_SCAN_NEEDS_VALUE%"=="1" (
  if "%~1"=="" call :brain_error "--vault requires a non-empty path" 2
  if "%~1"=="" exit /b 2
  set "BRAIN_CLI_VAULT=%~1"
  set /a BRAIN_VAULT_COUNT+=1
  set "BRAIN_SCAN_NEEDS_VALUE=0"
  shift
  goto brain_scan
)
if "%BRAIN_SCAN_OPTIONS%"=="0" (
  shift
  goto brain_scan
)
if "%~1"=="--" (
  set "BRAIN_SCAN_OPTIONS=0"
  shift
  goto brain_scan
)
if /I "%~1"=="--vault" (
  set "BRAIN_SCAN_NEEDS_VALUE=1"
  shift
  goto brain_scan
)
set "BRAIN_SCAN_ARG=%~1"
call :brain_scan_equals
if errorlevel 1 exit /b %ERRORLEVEL%
shift
goto brain_scan

:brain_scan_done
if "%BRAIN_SCAN_NEEDS_VALUE%"=="1" call :brain_error "--vault requires a path" 2
if errorlevel 1 exit /b %ERRORLEVEL%
if not "%BRAIN_VAULT_COUNT%"=="0" if not "%BRAIN_VAULT_COUNT%"=="1" call :brain_error "multiple --vault options are ambiguous" 2
if errorlevel 1 exit /b %ERRORLEVEL%

if "%BRAIN_VAULT_COUNT%"=="1" goto brain_use_cli_vault
if defined BRAIN_VAULT goto brain_use_environment_vault
set "BRAIN_CANDIDATE=%CD%"
call :brain_walk_up
if errorlevel 1 exit /b %ERRORLEVEL%
goto brain_candidate_ready

:brain_use_cli_vault
set "BRAIN_CANDIDATE=%BRAIN_CLI_VAULT%"
goto brain_candidate_ready

:brain_use_environment_vault
set "BRAIN_CANDIDATE=%BRAIN_VAULT%"

:brain_candidate_ready

for %%I in ("%BRAIN_CANDIDATE%") do set "BRAIN_ROOT=%%~fI"
if not exist "%BRAIN_ROOT%\AGENTS.md" call :brain_error "vault root is missing AGENTS.md" 2
if errorlevel 1 exit /b %ERRORLEVEL%
if exist "%BRAIN_ROOT%\AGENTS.md\" call :brain_error "AGENTS.md is not a regular file" 2
if errorlevel 1 exit /b %ERRORLEVEL%
if not exist "%BRAIN_ROOT%\10_Agents\" call :brain_error "vault tool path is invalid" 2
if errorlevel 1 exit /b %ERRORLEVEL%
if not exist "%BRAIN_ROOT%\10_Agents\tools\" call :brain_error "vault tool path is invalid" 2
if errorlevel 1 exit /b %ERRORLEVEL%
if not exist "%BRAIN_ROOT%\10_Agents\tools\brain\" call :brain_error "vault tool path is invalid" 2
if errorlevel 1 exit /b %ERRORLEVEL%
if not exist "%BRAIN_ROOT%\10_Agents\tools\brain\brain.py" call :brain_error "vault root is missing brain.py" 2
if errorlevel 1 exit /b %ERRORLEVEL%
if exist "%BRAIN_ROOT%\10_Agents\tools\brain\brain.py\" call :brain_error "brain.py is not a regular file" 2
if errorlevel 1 exit /b %ERRORLEVEL%
where fsutil >nul 2>nul
if errorlevel 1 goto brain_find_python
fsutil reparsepoint query "%BRAIN_ROOT%" >nul 2>nul
if errorlevel 1 goto brain_check_agents_reparse
call :brain_error "vault root must not be a reparse point" 2
exit /b %ERRORLEVEL%
:brain_check_agents_reparse
fsutil reparsepoint query "%BRAIN_ROOT%\AGENTS.md" >nul 2>nul
if errorlevel 1 goto brain_check_tool_reparse
call :brain_error "AGENTS.md must not be a reparse point" 2
exit /b %ERRORLEVEL%
:brain_check_tool_reparse
fsutil reparsepoint query "%BRAIN_ROOT%\10_Agents" >nul 2>nul
if errorlevel 1 goto brain_check_tools_dir_reparse
call :brain_error "vault tool path must not contain a reparse point" 2
exit /b %ERRORLEVEL%
:brain_check_tools_dir_reparse
fsutil reparsepoint query "%BRAIN_ROOT%\10_Agents\tools" >nul 2>nul
if errorlevel 1 goto brain_check_brain_dir_reparse
call :brain_error "vault tool path must not contain a reparse point" 2
exit /b %ERRORLEVEL%
:brain_check_brain_dir_reparse
fsutil reparsepoint query "%BRAIN_ROOT%\10_Agents\tools\brain" >nul 2>nul
if errorlevel 1 goto brain_check_brain_file_reparse
call :brain_error "vault tool path must not contain a reparse point" 2
exit /b %ERRORLEVEL%
:brain_check_brain_file_reparse
fsutil reparsepoint query "%BRAIN_ROOT%\10_Agents\tools\brain\brain.py" >nul 2>nul
if errorlevel 1 goto brain_find_python
call :brain_error "brain.py must not be a reparse point" 2
exit /b %ERRORLEVEL%

:brain_find_python
where py >nul 2>nul
if not errorlevel 1 goto brain_run_py
where python3 >nul 2>nul
if not errorlevel 1 goto brain_run_python3
where python >nul 2>nul
if not errorlevel 1 goto brain_run_python
call :brain_error "Python 3 is unavailable" 127
exit /b %ERRORLEVEL%

:brain_run_py
py -3 "%BRAIN_ROOT%\10_Agents\tools\brain\brain.py" %*
exit /b %ERRORLEVEL%

:brain_run_python3
python3 "%BRAIN_ROOT%\10_Agents\tools\brain\brain.py" %*
exit /b %ERRORLEVEL%

:brain_run_python
python "%BRAIN_ROOT%\10_Agents\tools\brain\brain.py" %*
exit /b %ERRORLEVEL%

:brain_scan_equals
if /I not "%BRAIN_SCAN_ARG:~0,8%"=="--vault=" exit /b 0
set "BRAIN_CLI_VAULT=%BRAIN_SCAN_ARG:~8%"
if not defined BRAIN_CLI_VAULT call :brain_error "--vault requires a non-empty path" 2
if errorlevel 1 exit /b %ERRORLEVEL%
set /a BRAIN_VAULT_COUNT+=1
exit /b 0

:brain_walk_up
if exist "%BRAIN_CANDIDATE%\AGENTS.md" if exist "%BRAIN_CANDIDATE%\10_Agents\tools\brain\brain.py" exit /b 0
for %%I in ("%BRAIN_CANDIDATE%\..") do set "BRAIN_PARENT=%%~fI"
if /I "%BRAIN_PARENT%"=="%BRAIN_CANDIDATE%" call :brain_error "no vault found from the current directory upward" 1
if errorlevel 1 exit /b %ERRORLEVEL%
set "BRAIN_CANDIDATE=%BRAIN_PARENT%"
goto brain_walk_up

:brain_error
>&2 echo brain: %~1
exit /b %~2
