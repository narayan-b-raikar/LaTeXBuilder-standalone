@echo off
rem Makes installer_output\LaTeXBuilder-Setup-1.6.0.exe from dist\LaTeXBuilder (run build_exe.bat first).
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
  echo Inno Setup 6 was not found. Install it from https://jrsoftware.org/isdl.php and run this again.
  pause
  exit /b 1
)
%ISCC% installer.iss
echo.
echo Done. The installer is in installer_output
pause
