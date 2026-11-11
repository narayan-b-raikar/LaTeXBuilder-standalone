# -*- coding: utf-8 -*-
"""Common LaTeX packages: (style file name, category, what it does). Pure data."""

PAGE = "Page layout and structure"
FONTS = "Fonts and encodings"
LANG = "Languages"
TEXT = "Text and paragraphs"
TABLES = "Lists and tables"
GRAPHICS = "Graphics and colour"
MATH = "Mathematics and science"
REFS = "References, links and indexes"
NOTES = "Headers, footnotes and floats"
CODE = "Code and verbatim"
DOCS = "Large documents and special documents"
TOOLS = "Programming and tools"

CATALOG = [
	# page layout
	("geometry", PAGE, "Page size and margins"),
	("fancyhdr", PAGE, "Headers and footers"),
	("setspace", PAGE, "Line spacing: single, one and a half, double"),
	("multicol", PAGE, "Several text columns, balanced on the last page"),
	("pdflscape", PAGE, "Landscape pages inside a portrait document, rotated in the PDF"),
	("lscape", PAGE, "Landscape pages (simple version)"),
	("titlesec", PAGE, "Change the look of chapter, section and sub-section headings"),
	("titling", PAGE, "Customise the title block (\\title, \\author, \\date)"),
	("parskip", PAGE, "Space between paragraphs instead of first-line indent"),
	("indentfirst", PAGE, "Indent the first paragraph after a heading too"),
	("microtype", PAGE, "Fine typographic improvements: spacing, hyphenation, margin kerning"),
	("ragged2e", PAGE, "Better left, right, centred and justified text (environment justify)"),
	("changepage", PAGE, "Change margins and text width for part of a page"),
	("tocloft", PAGE, "Customise the table of contents and lists of figures and tables"),
	("titletoc", PAGE, "Customise the table of contents entries"),
	("appendix", PAGE, "More control over appendices"),
	("emptypage", PAGE, "No page numbers or headers on blank pages before chapters"),
	("afterpage", PAGE, "Run a command after the current page ends"),
	("pdfpages", PAGE, "Insert pages of other PDF files into your document"),
	("lipsum", PAGE, "Dummy filler text for tests"),
	("eso-pic", PAGE, "Put pictures or text on the page background or foreground"),
	("draftwatermark", PAGE, "Add a watermark such as DRAFT to every page"),
	("layouts", PAGE, "Show the page layout dimensions"),
	# fonts
	("fontspec", FONTS, "Use any installed font (XeLaTeX or LuaLaTeX); needed for Indian languages"),
	("unicode-math", FONTS, "Unicode mathematics fonts (XeLaTeX or LuaLaTeX)"),
	("lmodern", FONTS, "Latin Modern fonts, a good default for pdfLaTeX"),
	("fontenc", FONTS, "Font encoding such as T1 for accented letters (pdfLaTeX)"),
	("inputenc", FONTS, "Input encoding such as utf8 (pdfLaTeX)"),
	("textcomp", FONTS, "Extra text symbols such as the euro and degree signs"),
	("eurosym", FONTS, "The euro sign"),
	("newtxtext", FONTS, "Times-like text font"),
	("newtxmath", FONTS, "Times-like mathematics font"),
	("mathptmx", FONTS, "Times Roman text and math"),
	("helvet", FONTS, "Helvetica-like sans-serif font"),
	("courier", FONTS, "Courier typewriter font"),
	("kpfonts", FONTS, "Palatino-like fonts with math"),
	("libertinus", FONTS, "Libertinus serif font family"),
	("pifont", FONTS, "Dingbats and decorative symbols"),
	("fontawesome5", FONTS, "Icons"),
	# languages
	("babel", LANG, "Language support for pdfLaTeX: hyphenation and names such as Chapter"),
	("polyglossia", LANG, "Language support for XeLaTeX and LuaLaTeX, including Indian languages"),
	("csquotes", LANG, "Quotation marks that follow the language rules"),
	("hyphenat", LANG, "Control hyphenation"),
	# text
	("soul", TEXT, "Highlight, underline, strike through and letter-spacing"),
	("ulem", TEXT, "Underlines that break across lines, and strike through"),
	("xspace", TEXT, "Add the right space after commands you define"),
	("enumitem", TEXT, "Customise lists: spacing, labels and resuming numbers"),
	("paralist", TEXT, "Compact lists and in-paragraph lists"),
	("verse", TEXT, "Poetry with numbered lines"),
	("epigraph", TEXT, "Quotations at the start of chapters"),
	("lettrine", TEXT, "Large first letter of a paragraph (drop cap)"),
	("textcase", TEXT, "Change case of text safely"),
	("comment", TEXT, "Comment out large blocks of text"),
	("calc", TEXT, "Arithmetic with lengths and counters"),
	("fmtcount", TEXT, "Print numbers as words, such as first or twenty-one"),
	("datetime2", TEXT, "Format dates and times"),
	("relsize", TEXT, "Relative font sizes"),
	# tables
	("tabularx", TABLES, "Tables whose columns fill a given width"),
	("longtable", TABLES, "Tables that continue over several pages"),
	("booktabs", TABLES, "Professional looking horizontal table rules"),
	("array", TABLES, "Extended column formats for tables"),
	("multirow", TABLES, "Table cells spanning several rows"),
	("makecell", TABLES, "Line breaks and formatting inside table cells"),
	("colortbl", TABLES, "Coloured table rows, columns and cells"),
	("supertabular", TABLES, "Multi-page tables (older alternative to longtable)"),
	("diagbox", TABLES, "Diagonal lines in table header cells"),
	# graphics
	("graphicx", GRAPHICS, "Include pictures with \\includegraphics"),
	("xcolor", GRAPHICS, "Colours for text, backgrounds and rules"),
	("tikz", GRAPHICS, "Draw diagrams and figures with code"),
	("pgfplots", GRAPHICS, "Plots and charts drawn from data"),
	("subcaption", GRAPHICS, "Sub-figures and sub-tables with their own captions"),
	("caption", GRAPHICS, "Customise captions of figures and tables"),
	("float", GRAPHICS, "Force figure position with the H option"),
	("wrapfig", GRAPHICS, "Wrap text around a figure"),
	("adjustbox", GRAPHICS, "Resize, trim and align boxes and pictures"),
	("tcolorbox", GRAPHICS, "Coloured boxes with titles"),
	("mdframed", GRAPHICS, "Frames that can break across pages"),
	("framed", GRAPHICS, "Simple frames and shaded blocks"),
	("rotating", GRAPHICS, "Rotate text, tables and figures"),
	("transparent", GRAPHICS, "Transparent colours"),
	# math
	("amsmath", MATH, "Main mathematics package: aligned equations and more"),
	("amssymb", MATH, "Extra mathematical symbols"),
	("amsthm", MATH, "Theorem, lemma and proof environments"),
	("mathtools", MATH, "Improvements and extensions to amsmath"),
	("bm", MATH, "Bold math symbols"),
	("siunitx", MATH, "Numbers and units, correctly spaced"),
	("physics", MATH, "Shortcuts for physics notation"),
	("cancel", MATH, "Cross out terms in equations"),
	("nicefrac", MATH, "Slanted fractions such as 1/2"),
	("mathrsfs", MATH, "Script math letters"),
	("empheq", MATH, "Boxed and decorated equations"),
	("braket", MATH, "Dirac bra-ket notation"),
	("mhchem", MATH, "Chemical formulas and equations"),
	("chemfig", MATH, "Draw chemical structures"),
	("algorithm2e", MATH, "Typeset algorithms"),
	("algpseudocode", MATH, "Pseudocode in the algorithmicx style"),
	("algorithm", MATH, "Floating algorithm environment"),
	# references
	("hyperref", REFS, "Clickable links, PDF bookmarks and PDF information; load it last"),
	("url", REFS, "Typeset web addresses with line breaking"),
	("natbib", REFS, "Author-year and numeric citations with BibTeX"),
	("biblatex", REFS, "Modern bibliographies; build runs biber automatically"),
	("cite", REFS, "Compress numeric citations such as [1-3]"),
	("cleveref", REFS, "Smart cross references such as figure 3 and tables 2 and 4"),
	("varioref", REFS, "References with page hints, such as on the next page"),
	("makeidx", REFS, "Create a subject index"),
	("imakeidx", REFS, "Index with more control"),
	("glossaries", REFS, "Glossary, list of symbols and acronyms"),
	("nomencl", REFS, "List of symbols (nomenclature)"),
	("hypcap", REFS, "Make links to figures and tables land on the figure"),
	# notes and floats
	("footmisc", NOTES, "Customise footnotes: symbols, layout, per-page numbering"),
	("endnotes", NOTES, "Endnotes at the end of the document"),
	("lastpage", NOTES, "Know the total number of pages, as in Page 3 of 12"),
	("placeins", NOTES, "FloatBarrier stops figures moving past a point"),
	("marginnote", NOTES, "Notes in the margin that work everywhere"),
	("todonotes", NOTES, "To-do notes in the margin and in the text"),
	("footnotehyper", NOTES, "Footnotes inside tables with hyperref"),
	# code
	("listings", CODE, "Source code listings"),
	("minted", CODE, "Syntax highlighted code (needs Python and Pygments; run with shell escape)"),
	("fancyvrb", CODE, "Verbatim text with extra options"),
	("verbatim", CODE, "Improved verbatim environment and file inclusion"),
	# documents
	("subfiles", DOCS, "Each chapter file can be built on its own or as part of the main document"),
	("standalone", DOCS, "Small documents that can also be included in a larger one"),
	("import", DOCS, "Include files from other folders with the right relative paths"),
	("pdfx", DOCS, "PDF/A and archival PDF output"),
	("tagpdf", DOCS, "Tagged, accessible PDF output (experimental, needs a recent LaTeX)"),
	# tools
	("etoolbox", TOOLS, "Programming tools for package and class authors"),
	("ifthen", TOOLS, "If-then-else in documents"),
	("xstring", TOOLS, "String manipulation"),
	("xparse", TOOLS, "Define commands with flexible arguments"),
	("iftex", TOOLS, "Detect which TeX engine is running"),
	("kvoptions", TOOLS, "Key-value options for packages"),
	("luacode", TOOLS, "Lua code inside documents (LuaLaTeX)"),
	("pgf", TOOLS, "Basic drawing system used by TikZ"),
]

CATEGORIES = [PAGE, FONTS, LANG, TEXT, TABLES, GRAPHICS, MATH, REFS, NOTES, CODE, DOCS, TOOLS]
BY_NAME = dict((n, (n, c, d)) for n, c, d in CATALOG)
