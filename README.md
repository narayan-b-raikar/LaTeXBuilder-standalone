# LaTeX Builder (stand-alone)

The same editor, navigator and builder as the NVDA add-on, as an ordinary Windows program. It does not need NVDA.
It still needs MiKTeX (PDF) and Pandoc (Word, HTML and other formats) installed on the computer.

## Running it
1. Install Python 3.10 or later from python.org (tick "Add python.exe to PATH").
2. Open a command prompt in this folder and run: `python -m pip install wxPython accessible-output2`
3. Start it with `run_from_source.bat`, or `python app.py`. You can add a .tex or .texproj file name after it.

## Making LaTeXBuilder.exe and an installer
Run `build_exe.bat`. The program appears in `dist\LaTeXBuilder\LaTeXBuilder.exe`. Copy that whole folder anywhere.

To make a proper installer, install Inno Setup 6 (https://jrsoftware.org/isdl.php) and run `build_installer.bat`. It uses `installer.iss` and creates `installer_output\LaTeXBuilder-Setup-1.6.0.exe`. The installer installs for the current user without administrator rights (or for all users if you choose), adds a Start menu shortcut, an optional desktop shortcut, optional file types (.texproj and an Open with entry for .tex), an uninstaller, and tells you at the end if MiKTeX or Pandoc is missing. Silent install: `LaTeXBuilder-Setup-1.6.0.exe /VERYSILENT /SUPPRESSMSGS`.
No Windows PC with Python? Upload this folder to a GitHub repository, open Actions, run "Build Windows program and installer", and download the result.

## Speech
Menus, dialogs and the text area are read by any screen reader as usual. The extra spoken messages (what was inserted, build finished, and so on)
are sent to NVDA, JAWS or SAPI when the optional package `accessible-output2` is installed. With NVDA you can instead put
`nvdaControllerClient64.dll` (from NV Access) next to the program. The last message is always shown in the status bar too.

## Where things are kept
Settings, shortcuts, logs and crash-recovery copies are in `%APPDATA%\LaTeXBuilder`.
Everything else works exactly as described in the user manual (the NVDA parts of the manual do not apply).
