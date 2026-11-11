# LaTeX Builder User Manual

Version 1.6.0. The same program is available as an NVDA add-on and as a stand-alone Windows program. Where the two differ, this manual says so.

## 1. What LaTeX Builder is

LaTeX Builder is an accessible place to read, write, navigate and build LaTeX documents. It gives you:

- An editor window that screen readers read like any normal edit field, with menus for everything.
- Quick insert commands for headings, bold, italic, alignment, lists, poems, footnotes, endnotes, headers and footers, tables, pictures, links and mathematics.
- A list and manager of LaTeX packages.
- Navigation by headings, footnotes and environments.
- Projects that join several .tex files into one document, and an importer for projects made in other editors.
- A builder that runs MiKTeX to make PDF, and Pandoc to make Word, OpenDocument, HTML, EPUB, RTF, Markdown and plain text.
- English and the major Indian languages, with a chooser for every installed font.
- Customizable keyboard shortcuts, crash recovery, logs, and a built-in manual.

LaTeX Builder does not replace MiKTeX or Pandoc. It writes LaTeX for you, runs those programs and reports the results in an accessible way.

## 2. Requirements and installation

### 2.1 What you need

- MiKTeX, which provides pdflatex and xelatex. It is needed for PDF output and for every language except English.
- Pandoc, needed only for Word, OpenDocument, RTF, HTML, EPUB, Markdown and text output.
- For the add-on: NVDA 2025.1 or later.

### 2.2 Installing the NVDA add-on

1. Press Enter on the file latexBuilder-1.6.0.nvda-addon in File Explorer.
2. Choose Yes when NVDA asks to install it, and restart NVDA.

To update, install the newer file the same way. Settings, shortcuts and projects are kept.

### 2.3 Installing the stand-alone program

Run the installer LaTeXBuilder-Setup-1.6.0.exe, or copy the program folder anywhere and run LaTeXBuilder.exe. Settings, shortcuts, logs and recovery copies are kept in the folder %APPDATA%\LaTeXBuilder. The stand-alone program speaks its extra messages through NVDA, JAWS or SAPI when the optional speech helper is present; menus and dialogs are read by any screen reader as usual.

## 3. Opening the editor and the two most useful keys

In NVDA press **NVDA+Control+Shift+L**, or open the NVDA menu, Tools, LaTeX Builder. The gesture can be changed in NVDA's Input Gestures dialog, category LaTeX Builder. The stand-alone program simply opens its window.

The title of the window shows the file name, whether it has unsaved changes, and the project name. To leave, press Alt+F4 or choose File, Exit editor.

- **Control+K** opens the command list. Type part of any command name, such as footnote, bold or build, press Down arrow, and press Enter. You never need to remember a shortcut.
- **F1** opens this manual in a window. Type in its search box to search the whole manual, press Down arrow to choose a section, and press Enter to read it.

## 4. The editor window

The window has a menu bar (File, Edit, Insert, Navigate, View, Project, Build, Help) and one large text area. The Tab key inserts a tab character, so it never takes you out of your text. Long lines wrap onto the next line, so Up and Down arrow move one screen line at a time. You can switch wrapping off in the View menu.

### 4.1 Working with several documents

- **Control+PgDn** and **Control+PgUp**: next and previous document. NVDA says the file name and position.
- **Control+Shift+W**: list of open documents.
- **Control+N** new, **Control+O** open, **Control+S** save, **Control+Shift+S** save as, **Control+F2** save all, **Control+W** close the document.

Files are read as UTF-8, with a fallback for older Windows encodings, and always saved as UTF-8, which Kannada, Hindi and other Indian-language text needs.

### 4.2 Finding and replacing

- **Control+F** find, **F3** next, **Shift+F3** previous. NVDA says Search wrapped when the search passes the end.
- **Control+H** replace all. **Control+G** go to a line number.

## 5. Inserting LaTeX quickly

All insert commands are in the Insert menu, grouped by purpose, and in the command list (Control+K).

### 5.1 How every insert command behaves

- With no text selected, the command inserts its code and puts the caret inside the braces, so you can type at once.
- With text selected, the command wraps the selection. Select the word Introduction on its own line, press Control+1, and it becomes a section heading.
- Blocks such as headings and lists always start on their own line, and no extra blank line is created.
- If a command needs a package, it is added to the preamble automatically and NVDA tells you.
- NVDA confirms each insertion. In View, Speech and sound options you can make confirmations short or switch them off.

### 5.2 Headings and sub-headings

Chapter, section, subsection, subsubsection, paragraph and subparagraph headings, and unnumbered versions, are in Insert, Headings. The article class has no chapters; choose report or book in the project settings if you want chapters.

### 5.3 Formatting text

Bold, italic, underline, emphasis, monospace, small capitals, strike through, superscript and subscript text, text sizes, LaTeX quotation marks and line break are in Insert, Format text.

### 5.4 Alignment

Insert, Alignment has:

- Left aligned text, Centered text, Right aligned text and Justified text. They use the same keys as word processors: **Control+L**, **Control+E**, **Control+R** and **Control+J**.
- With text selected, the command wraps the selection in the alignment. With nothing selected, an empty block is inserted and the caret is placed inside.
- Left, centre and right align this paragraph only, which wrap just the paragraph without a block.
- Indent the next paragraph, and no indent for this paragraph.

Justified text uses the ragged2e package, which is added automatically. Alignment also survives conversion to Word (section 14).

### 5.5 Lists and blocks

Bulleted list, numbered list, description list, new list item, quote, long quotation, verbatim (code) block and abstract are in Insert, Lists and blocks. Press **Control+Shift+L** at the end of a list line to add the next item.

### 5.6 Footnotes, endnotes and margin notes

- Footnote: **Control+Shift+F**. The caret is placed inside the note; type its text.
- Endnote: **Control+Shift+E**. The endnotes package is added. In a project build the list of endnotes is printed at the end for you. In a single document use Insert, Notes, Print all endnotes here.
- **Footnote and endnote settings** (Insert, Footnote and endnote settings) lets you decide how notes look and are numbered; see section 5.7.

### 5.7 Footnote and endnote settings

The settings form is the same one used in Project settings (groups Footnotes and Endnotes). In a document with a preamble, the settings are added to the preamble. In a part file of a project they are saved in the project settings.

**Footnotes**

- **Numbering:** continue through the whole document, restart on every page, restart in every chapter (in an article, every section), or restart in every section.
- **Number style:** 1 2 3, i ii iii, I II III, a b c, A B C, or symbols (an asterisk, dagger and so on; nine symbols, so best with restart on every page).
- **Text size:** very small, small, medium small, same as the text, or large.
- **Font:** any installed font for the notes, chosen from the list (this uses XeLaTeX automatically).
- **Layout:** standard, hanging (later lines indented under the text), or flush with the margin.
- **Line above the notes** on or off, notes always at the bottom of the page, and the space between notes.

**Endnotes**

- Use endnotes for every footnote, so all notes go to the end.
- The heading above the endnotes, for example Notes or a heading in your own language.
- Text size, number style, and numbering (continue, restart in every chapter, or restart in every section).
- Whether the endnotes are printed automatically at the end of a project.

### 5.8 Poems

Type or paste the poem as plain lines, with a blank line between stanzas. Select the lines and press **Control+Shift+V**. They are wrapped in a verse environment with the line breaks added. With nothing selected, an empty poem is inserted; press **Shift+Enter** at the end of each line.

### 5.9 Headers, footers and page numbers

**Control+Shift+H** asks for the left, centre and right text of the header and of the footer, and whether to draw a line under the header. The footer centre is filled with \thepage, the page number. The code is added to the preamble.

### 5.10 Title, contents and other parts

Title page from a template (Control+7, section 5.12), table of contents (Control+5), new page (Control+6), comment line (Control+Q), list of figures and tables, appendix, vertical space, line spacing, and include another .tex file are in Insert, Document parts.

### 5.11 References, links, pictures and tables

- Label (Control+Shift+J), reference (Control+Shift+R), citation (Control+Shift+X), page reference and a manual bibliography list.
- Hyperlink (Control+Shift+K) asks for the address and the link text.
- Image (Control+Shift+G) opens a file chooser and asks for width, caption and label.
- Table (Control+Shift+A) asks for rows, columns, a bold header row, lines between cells and a caption. The caret is placed in the first cell; type an ampersand to move to the next cell.

### 5.12 Title pages from templates

**Insert, Title page from a template** (Control+7) first asks for the title, author and date, then for the design. The designs are:

- **Standard:** the usual title block at the top of the first page, with the text following on the same page.
- **Centered:** a title page on its own page, with everything centered.
- **Book cover:** the title between two rules, the author, and the publisher or place and year at the bottom.
- **Thesis or report:** institution, department, title between rules, an extra lines area for the degree or supervisor, and the author.
- **Minimal:** left aligned with a short rule.
- **Boxed:** title, author and date inside a frame.

You can add a subtitle, an institution or publisher, a department or series, extra lines (one per line) and a logo picture. The finished code is inserted at the caret. If a project is open you are asked whether to use the same design for the whole project. The same fields are in Project settings, group Title page design, and are used when the project is built. A title page is printed only when Print the title block is on in the group Title, author and class.

### 5.13 Mathematics

Inline math (Control+Shift+M), display math (Control+Shift+D), numbered and aligned equations, fraction, square root, subscript and superscript. **Symbols and Greek letters** (Control+Shift+Y) opens a searchable list; the symbol is wrapped in dollar signs automatically when you are not already inside math.

### 5.14 Choosing values from lists

Wherever a value is a number with a unit, such as a margin, a line spacing or a paragraph indent, the box is a list you can open with Alt+Down and choose from, or you can type your own value. Dates are chosen as Today's date, No date, or A date I type. Header and footer positions offer Page number, Page x of y, Chapter or section name, Document title, Author and Date, or your own text. Buttons that choose a file, folder or installed font are placed directly after their text box, so press Tab once to reach them.

## 6. Reading and navigating

- **Alt+Down** and **Alt+Up**: next and previous heading. NVDA says the type, number and title.
- **Alt+Shift+Down** and **Alt+Shift+Up**: next and previous heading of the same or a higher level.
- **Control+Shift+O**: list of all headings with a filter box.
- **F2**: announces the line, the heading path and the environments you are inside.
- **F8** and **Shift+F8**: next and previous footnote or endnote. **F9** and **Shift+F9**: next and previous environment.
- Next and previous math, and next and previous comment, are in the Navigate menu.

## 7. The View menu

- Increase text size (Alt+PgUp), decrease text size (Alt+PgDn), reset (Control+0).
- Toggle word wrap.
- Editor font and Colour theme: change only how the editor window looks. Themes include white, yellow or green on black and black on yellow or white.
- Speech and sound options: confirmations after insertion (full, short, none), tones during builds, and the Still building reminder.
- Document statistics (Control+F3): lines, words, characters, headings of each kind, footnotes and environments.
- Read selection or current section as plain text (Control+F8), current paragraph (Control+F9) and current line (Control+F7): spoken without LaTeX commands. Headings are announced and footnotes are read in brackets.

## 8. LaTeX packages: list and manager

Press **Control+Shift+U**, or choose **Insert, LaTeX packages** or **Build, LaTeX packages**, to open the package list.

### 8.1 The list

The list shows 130 common packages, each with what it does, its group, whether it is installed, and whether your document or project uses it. A Show box chooses:

- Common LaTeX packages.
- Packages used in this document or project.
- Only installed packages, or only packages that are not installed.
- All MiKTeX packages (names only), when MiKTeX's mpm tool is found. The first time can take a minute.

Type in the filter box to narrow the list, and press Down arrow to move into it.

### 8.2 The buttons

- **Add to document:** adds a use package line to the preamble. If the file has no preamble (a part of a project), the line is added to the extra preamble of the project instead. NVDA says where it went, or that the package is already loaded.
- **Add with options:** asks for options such as a4paper,margin=2cm.
- **Install:** installs a package that is not installed. With MiKTeX this lets MiKTeX fetch whatever provides the package; in the All MiKTeX packages view it uses mpm. It runs in the background and NVDA announces the result.
- **Details:** what the package does, its status, and the output of the last installation.
- **Update all packages:** asks first, then updates every installed package. It needs an internet connection and can take several minutes.
- **Refresh status:** checks again which packages are installed.

MiKTeX also installs missing packages automatically the first time a build needs them, if that is allowed in Build, Settings. Installed status is found with MiKTeX's kpsewhich tool. With TeX Live, install and update use tlmgr, which has had less testing.

## 9. Projects: several files, one document

### 9.1 Creating a project

Project, New project opens one dialog for the project name, the folder where the project file is saved (type it, or choose Browse for folder) and whether to add the open saved documents. The project file has the extension .texproj. When you choose OK, the project file list opens.

Other commands: Open project (Control+Shift+P), Open last project, Open the main file of the project, Save project, and Add this document to project (Control+F4). Changes are saved automatically.

**What happens when you open a project.** If no file is open yet (only the empty starting document), LaTeX Builder opens the main file of the project: the imported main file, or otherwise the first file in the project. If you already have files open, nothing is opened for you. You can choose in Build, Settings whether to open the main file or to open no file and leave the editor empty.

### 9.2 The project file list

Press **F4**. The list shows the files in the order they appear in the final document. Buttons: Add files, Add open documents, Remove (the file is not deleted), Move up, Move down, Open in editor, Settings, Build.

### 9.3 How a project is built

A build writes a main file and a copy of each part into a folder named build next to the project file. The main file has the preamble made from your settings, the title block, the optional table of contents, one \input command for each part and the end of the document. Your own files are never changed. Part files should contain only text and commands, not a \documentclass; if a file is a complete document, only its body is used.

The finished file is saved next to the project file, named after the project.

### 9.4 Project settings

Press **Shift+F4**. One window shows the groups of settings as buttons side by side. Press Tab to move between them, and Space or Enter to open one. A read-only box shows the current values of all groups. Choose Apply changes to keep everything; Cancel asks before discarding. The same window is used by File, New document from template.

- **Project name and building:** name, LaTeX engine (auto, pdflatex, xelatex, lualatex), new page for each file, use a file's own preamble, and for imported projects the two options in section 10.
- **Title, author and document class:** article, report or book; title, author, date; title block; table of contents.
- **Title page design:** the template, subtitle, institution, department, extra lines and logo (section 5.12).
- **Language and main font:** language, font from the installed fonts, size 8 to 20 points, polyglossia, native digits.
- **Font fine tuning:** scale, fake bold, fake italic, letter spacing, real bold and italic font names.
- **Sans and mono fonts.**
- **Page size and columns:** A3 to A6, B4, B5, Letter, Legal, Executive or custom size; landscape; two-sided printing; one or two columns; column gap and line; and whether the geometry package controls page size and margins.
- **Margins:** all sides, top, bottom, left or inner, right or outer, binding space, header and footer distance.
- **Spacing and page numbers:** line spacing, paragraph indent and spacing, page number style, first page number.
- **Footnotes** and **Endnotes:** numbering, style, size, font, layout and heading (section 5.7).
- **Packages and extras:** math, images and links packages, the standard font packages for pdfLaTeX, and a box for extra preamble lines with a header and footer helper.

## 10. Importing a project made in another editor

Project, Import existing project from a main .tex file. Choose the main file (the one with \documentclass and \begin{document}, often main.tex) of a project made in TeXstudio, TeXworks, VS Code, Overleaf or any other editor. A dialog asks for a project name and an import mode. The project file is saved in the folder of the main file, and an import report opens.

### 10.1 What is read

- Document class and options, font size, paper, two-sided, columns. Other classes such as memoir are kept as the original line.
- Page size and margins from geometry. Options the dialog cannot show are kept as the original lines.
- Fonts set with \setmainfont, \setsansfont and \setmonofont, including scale and fake bold and italic. Fonts with special options, such as a Path, are kept as they are.
- Language set with polyglossia, with native digits.
- Title, author, date, line spacing, paragraph indent and spacing.
- Packages amsmath, amssymb, graphicx and hyperref when loaded without options.
- Everything else in the preamble is kept word for word as extra preamble: footnote setup, custom commands, other packages, header and footer setup. Comments in the preamble are not imported.
- The engine, from a magic comment such as % !TEX program = xelatex, or from the packages used.

### 10.2 The body and the parts

The body of the main file is kept as the project layout. The title command, table of contents, appendix, bibliography commands and everything else stay where they are. The files named in \input, \include and \subfile become the project files in order. If you reorder the files, the parts change places. Extra files are added at the end. In Project settings, group Project name and building, you can turn the layout off to use the title block and contents settings instead.

### 10.3 The two modes

- **Convert (recommended):** the settings become editable and builds are generated from them.
- **Keep the main file as it is:** your original main file is compiled untouched; the project settings are not used. This is the safest for unusual projects. You can switch later in Project settings.

### 10.4 Bibliographies and resources

BibTeX and biber bibliographies run automatically during a build, and the build then uses at least three passes. The folder of the main file is searched for pictures, .bib, .bst, .sty and .cls files.

## 11. Indian languages and fonts

Supported languages: English, Kannada, Hindi, Sanskrit, Marathi, Nepali, Konkani (Devanagari), Tamil, Telugu, Malayalam, Bengali, Assamese, Gujarati, Punjabi (Gurmukhi), Odia and Urdu (right to left, experimental). Type text directly with your normal Windows keyboard.

Any language other than English is built with XeLaTeX and fontspec with the correct script. The default font is Nirmala UI, which comes with Windows. In Language and main font choose Choose font from installed fonts to see every font on the computer; fonts suggested for the script come first.

- **Use polyglossia** adds language-specific hyphenation and translated words such as Chapter and Contents. It is not available for Konkani and Odia.
- **Print native digits** prints numbers in the digits of the language where supported.
- If a font has no bold or italic, use fake bold and fake italic in Font fine tuning.

A recipe for a Kannada book: create a project, choose book, choose Kannada, pick a font, set font size 12 or 14, set the margins, apply, and build with F5. Odia and Urdu have had less testing.

## 12. Building

### 12.1 The build dialog

Press **F5**. Choose the output format (PDF, Word .docx, .odt, .rtf, .html, .epub, .md, .txt), the current document or the whole project, the engine (PDF only), and whether to open the result. **F6** builds again with the last choices, **Control+F5** opens the last result, **F7** shows errors and warnings, **Shift+F7** shows the full log.

### 12.2 During a build

Modified documents are saved first. The build runs in the background. A short beep starts it, a high beep means success and a low beep means failure; NVDA says Still building every 15 seconds. LaTeX runs twice so that contents and references are right, and bibliography tools run when needed.

### 12.3 Where files go

For a project, the output is next to the project file and working files are in the folder build. For a single document, the PDF is next to the .tex file and working files are in the folder _latexbuild. A file without \documentclass is built with a default preamble.

### 12.4 When a build fails

NVDA says how many errors occurred and reads the first one. A list opens with each problem, its file and line. Press Enter on an item to open the right file at that line, even in a project. The Show full log button shows the whole output. Typical messages: Undefined control sequence means a misspelled command or a missing package; Missing $ inserted means math used outside math; File not found means a wrong path.

## 13. Word and other formats through Pandoc

Pandoc reads your LaTeX and converts the content. Version 1.4 improves this in several ways:

- **Citations and bibliography.** Pandoc does not read \bibliography by itself. LaTeX Builder finds the .bib files named by \bibliography or \addbibresource, and when the document has citations it lets Pandoc format them, so citations and the list of references appear in the Word file. Natbib and biblatex commands are supported. A notice tells you which .bib files were used, or that none was found. In Build, Settings you can choose a citation style file (.csl) and the heading above the references.
- **Alignment.** Centered, left, right and justified blocks become real alignment in Word (and in HTML).
- **Fonts and language.** For projects, the Word file uses the project's main font and size, and the language of the text, so Kannada, Hindi and other scripts show in the right font and spelling language. If you choose a Word template in Settings, its styles are used instead.
- **Endnotes** become footnotes in Word.
- **Heading numbers** follow LaTeX numbering in Word, ODT, HTML and EPUB; you can switch this off in Settings.
- **HTML** is made as one self-contained file, with mathematics in MathML.

Word output cannot copy LaTeX page layout, margins, headers and footers. Use PDF when exact layout matters.

## 14. Crash recovery

Unsaved text is copied to a recovery folder every 15 seconds (change it in Build, Settings; 0 switches it off). If the program or NVDA crashes or is closed with unsaved work, the next time you open LaTeX Builder it offers to recover those documents. Recovered documents are marked as modified with their original names; save them to keep the changes. Saving or closing a document removes its copy.

## 15. Settings

Build, Settings (Shift+F5):

- The folder of the MiKTeX programs and the path of pandoc.exe, if they are not found automatically.
- Number of LaTeX passes, and automatic installation of missing MiKTeX packages.
- What to do when a project is opened with no file open.
- The citation style file, the heading for references, a Word template, and numbering of headings for Pandoc output.
- The safety copy interval.

## 16. Customizing keyboard shortcuts

Help, Customize keyboard shortcuts (Control+F1). Type part of a command name in the filter box, press Down arrow, and press Enter on a command or use the Change shortcut button. Type the new shortcut, such as Ctrl+Shift+X, Alt+Down or F7. If it is used by another command you are asked whether to move it. A shortcut must include Ctrl or Alt, or be a function key. Ctrl+C, Ctrl+X, Ctrl+V and Ctrl+A are reserved. Remove, Reset this command and Reset all to defaults are also available. Choices are kept when you update.

## 17. Logs and getting help

The Help menu has View add-on log (Shift+F1) with system information and the latest events, newest at the end; Copy add-on log to the clipboard, to paste into a message; View NVDA log entries about LaTeX Builder; Open the folder with the log files; and Clear add-on log. After a freeze, restart and read the last lines: they show the last command or dialog opened. When an error happens inside a command, you hear a message pointing you to the log.

## 18. Troubleshooting

**MiKTeX or Pandoc cannot be found.** Install them, or enter their locations in Build, Settings. If you installed them while the program was running, restart it.

**The build waits a long time.** MiKTeX may be downloading a package. Make sure automatic installation is on and you are online. A build is stopped after ten minutes.

**The font cannot be found.** Choose a font that exists with Choose font from installed fonts, or clear the box.

**Indian-language text prints as boxes.** The font does not contain that script. Choose a font suggested for the language. Nirmala UI covers most scripts.

**The PDF does not open.** Close it in your viewer before building again; some viewers lock the file.

**Citations show as keys in Word.** The .bib file was not found. Check that it is in the folder of the project or main file, and read the notice after the build.

**F1 shows an error.** This was a fault in version 1.4 and is fixed in 1.5. If it happens again, read the end of the log (Help, View add-on log) and send it.

**Something freezes.** Restart, then open Help, View add-on log and read the last lines.

**The add-on is rejected after an NVDA update.** Install the newest version of the add-on.

## 19. Limits of this version

- The interface and messages are in English.
- There is no live PDF preview; build, then open the result.
- There is no spell checking in the editor.
- Word output is a conversion by Pandoc and does not copy the PDF layout.
- Odia and Urdu have had less testing than other languages.
- The package manager has been tested mainly with MiKTeX; TeX Live support is basic.
- Parts of the window and dialogs have had limited testing in every setup. Please report anything that does not behave as this manual describes, together with the log.

## 20. Keyboard shortcut reference

### File

- New empty document: Ctrl+N
- New document from template...: no default shortcut
- Open...: Ctrl+O
- Save: Ctrl+S
- Save as...: Ctrl+Shift+S
- Save all documents: Ctrl+F2
- Close document: Ctrl+W
- Next document: Ctrl+PgDn
- Previous document: Ctrl+PgUp
- Open documents list...: Ctrl+Shift+W
- Exit editor: no default shortcut

### Edit

- Undo: Ctrl+Z
- Redo: Ctrl+Y
- Find...: Ctrl+F
- Find next: F3
- Find previous: Shift+F3
- Replace all...: Ctrl+H
- Go to line...: Ctrl+G
- Command list...: Ctrl+K

### Insert Headings

- Part: no default shortcut
- Chapter: Ctrl+Shift+1
- Section (heading): Ctrl+1
- Subsection (sub-heading): Ctrl+2
- Subsubsection (sub-sub-heading): Ctrl+3
- Paragraph heading: Ctrl+4
- Subparagraph heading: no default shortcut
- Chapter without number: no default shortcut
- Section without number: no default shortcut
- Subsection without number: no default shortcut
- Subsubsection without number: no default shortcut

### Insert Format text

- Bold: Ctrl+B
- Italic: Ctrl+I
- Underline: Ctrl+U
- Emphasis: Ctrl+Shift+I
- Monospace (typewriter): Ctrl+Shift+T
- Small capitals: no default shortcut
- Strike through: no default shortcut
- Superscript (text): no default shortcut
- Subscript (text): no default shortcut
- Smaller text: no default shortcut
- Larger text: no default shortcut
- Large text: no default shortcut
- Huge text: no default shortcut
- Quotation marks (LaTeX style): no default shortcut
- Line break: Shift+Enter

### Insert Alignment

- Left aligned text: Ctrl+L
- Centered text: Ctrl+E
- Right aligned text: Ctrl+R
- Justified text: Ctrl+J
- Left align this paragraph only: no default shortcut
- Centre this paragraph only: no default shortcut
- Right align this paragraph only: no default shortcut
- Indent the next paragraph: no default shortcut
- No indent for this paragraph: no default shortcut

### Insert Lists and blocks

- Bulleted list: Ctrl+Shift+B
- Numbered list: Ctrl+Shift+N
- Description list: no default shortcut
- New list item: Ctrl+Shift+L
- Quote block: Ctrl+Shift+Q
- Long quotation block: no default shortcut
- Verbatim (code) block: no default shortcut
- Abstract: no default shortcut

### Insert Notes, poems, headers

- Footnote: Ctrl+Shift+F
- Endnote: Ctrl+Shift+E
- Print all endnotes here: no default shortcut
- Margin note: no default shortcut
- Poem (selected lines become verse): Ctrl+Shift+V
- Header and footer...: Ctrl+Shift+H
- Footnote and endnote settings...: no default shortcut
- Current page number: no default shortcut

### Insert Document parts

- Title page from a template...: Ctrl+7
- Table of contents: Ctrl+5
- List of figures: no default shortcut
- List of tables: no default shortcut
- New page: Ctrl+6
- Clear page (flush floats): no default shortcut
- Start appendices: no default shortcut
- Vertical space: no default shortcut
- Fill horizontal space: no default shortcut
- Line spacing: no default shortcut
- Comment line (not printed): Ctrl+Q
- LaTeX packages...: Ctrl+Shift+U
- Include another .tex file...: no default shortcut
- New document skeleton...: no default shortcut

### Insert References, links, images, tables

- Label: Ctrl+Shift+J
- Reference to label: Ctrl+Shift+R
- Page reference: no default shortcut
- Citation: Ctrl+Shift+X
- Bibliography (manual list): no default shortcut
- Hyperlink...: Ctrl+Shift+K
- Image (picture file)...: Ctrl+Shift+G
- Table...: Ctrl+Shift+A

### Insert Math

- Inline math: Ctrl+Shift+M
- Display math: Ctrl+Shift+D
- Numbered equation: no default shortcut
- Aligned equations: no default shortcut
- Fraction: no default shortcut
- Square root: no default shortcut
- Subscript: no default shortcut
- Superscript (power): no default shortcut
- Symbols and Greek letters...: Ctrl+Shift+Y

### Insert

- LaTeX packages...: no default shortcut
- Title page from a template...: no default shortcut
- Footnote and endnote settings...: no default shortcut

### Navigate

- Next heading: Alt+Down
- Previous heading: Alt+Up
- Next heading, same or higher level: Alt+Shift+Down
- Previous heading, same or higher level: Alt+Shift+Up
- Document structure list...: Ctrl+Shift+O
- Announce where I am: F2
- Next footnote or endnote: F8
- Previous footnote or endnote: Shift+F8
- Next environment: F9
- Previous environment: Shift+F9
- Next math: no default shortcut
- Previous math: no default shortcut
- Next comment: no default shortcut
- Previous comment: no default shortcut

### View

- Increase text size: Alt+PgUp
- Decrease text size: Alt+PgDn
- Reset text size: Ctrl+0
- Toggle word wrap: no default shortcut
- Editor font...: no default shortcut
- Colour theme...: no default shortcut
- Speech and sound options...: no default shortcut
- Document statistics: Ctrl+F3
- Read selection or section as plain text: Ctrl+F8
- Read paragraph as plain text: Ctrl+F9
- Read line as plain text: Ctrl+F7

### Project

- New project...: no default shortcut
- Open project...: Ctrl+Shift+P
- Open last project: no default shortcut
- Import project from main .tex file...: no default shortcut
- Project files...: F4
- Open project main file: no default shortcut
- Project settings...: Shift+F4
- Add this document to project: Ctrl+F4
- Save project: no default shortcut

### Build

- Build document...: F5
- Build again: F6
- Show errors and warnings: F7
- View full build log: Shift+F7
- Open last result: Ctrl+F5
- LaTeX packages...: no default shortcut
- Settings...: Shift+F5

### Help

- User manual: F1
- User manual in web browser: no default shortcut
- Keyboard shortcuts list: Ctrl+Shift+F1
- Customize keyboard shortcuts...: Ctrl+F1
- View add-on log...: Shift+F1
- Copy add-on log: no default shortcut
- View NVDA log entries...: no default shortcut
- Open log folder: no default shortcut
- Clear add-on log: no default shortcut
- About: no default shortcut


## 21. Quick start card

- Open: NVDA+Control+Shift+L. Find any command: Control+K. This manual: F1.
- Heading: Control+1 (select the text first). Bold, italic: Control+B, Control+I.
- Align: Control+L, Control+E, Control+R, Control+J.
- Footnote, endnote: Control+Shift+F, Control+Shift+E. Poem: select the lines, Control+Shift+V.
- Packages: Control+Shift+U.
- Move by heading: Alt+Down, Alt+Up.
- Project files: F4. Project settings: Shift+F4. Build: F5. Errors: F7.
