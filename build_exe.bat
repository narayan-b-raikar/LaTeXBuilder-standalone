@echo off
rem Builds LaTeXBuilder.exe on Windows. Needs Python 3.10 or later (python.org), with "Add python.exe to PATH" ticked.
python -m pip install --upgrade pip
python -m pip install wxPython pyinstaller accessible-output2
python -m PyInstaller --noconfirm --clean --windowed --name LaTeXBuilder --collect-all accessible_output2 --add-data "latexBuilder\manual;latexBuilder\manual" app.py
echo.
echo Done. The program is in dist\LaTeXBuilder\LaTeXBuilder.exe
echo To make an installer, install Inno Setup 6 (jrsoftware.org) and run build_installer.bat
echo Optional: copy nvdaControllerClient64.dll (from NV Access) next to LaTeXBuilder.exe so confirmations are spoken by NVDA.
pause
