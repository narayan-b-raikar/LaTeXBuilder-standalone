# -*- coding: utf-8 -*-
"""Catalogue of everything the user can insert quickly. Pure data, no GUI."""

import re

CURSOR = "\u2038"  # marks where the caret ends up (replaced by the selection if there is one)


class Snippet(object):
	def __init__(self, key, category, label, tpl="", block=False, pkgs=(), action=None, shortcut=None):
		self.key = key
		self.category = category
		self.label = label
		self.tpl = tpl
		self.block = block
		self.pkgs = pkgs  # tuples (name, options)
		self.action = action  # name of special handler in the editor
		self.shortcut = shortcut


H = "Headings"
F = "Text formatting"
L = "Lists and blocks"
N = "Notes, poems, header and footer"
D = "Document parts"
R = "References, links, images, tables"
M = "Mathematics"
A = "Alignment"

CATEGORIES = [H, F, A, L, N, D, R, M]


def _head(key, name, label, shortcut=None, star=False):
	star_s = "*" if star else ""
	return Snippet(key, H, label, "\\%s%s{%s}\n" % (name, star_s, CURSOR), block=True, shortcut=shortcut)


SNIPPETS = [
	# ---- headings
	_head("part", "part", "Part", None),
	_head("chapter", "chapter", "Chapter", "Ctrl+Shift+1"),
	_head("section", "section", "Section (heading)", "Ctrl+1"),
	_head("subsection", "subsection", "Subsection (sub-heading)", "Ctrl+2"),
	_head("subsubsection", "subsubsection", "Subsubsection (sub-sub-heading)", "Ctrl+3"),
	_head("paragraph", "paragraph", "Paragraph heading", "Ctrl+4"),
	_head("subparagraph", "subparagraph", "Subparagraph heading"),
	_head("chapter_star", "chapter", "Chapter without number", star=True),
	_head("section_star", "section", "Section without number", star=True),
	_head("subsection_star", "subsection", "Subsection without number", star=True),
	_head("subsubsection_star", "subsubsection", "Subsubsection without number", star=True),

	# ---- text formatting (inline)
	Snippet("bold", F, "Bold", "\\textbf{%s}" % CURSOR, shortcut="Ctrl+B"),
	Snippet("italic", F, "Italic", "\\textit{%s}" % CURSOR, shortcut="Ctrl+I"),
	Snippet("underline", F, "Underline", "\\underline{%s}" % CURSOR, shortcut="Ctrl+U"),
	Snippet("emph", F, "Emphasis", "\\emph{%s}" % CURSOR, shortcut="Ctrl+Shift+I"),
	Snippet("mono", F, "Monospace (typewriter)", "\\texttt{%s}" % CURSOR, shortcut="Ctrl+Shift+T"),
	Snippet("smallcaps", F, "Small capitals", "\\textsc{%s}" % CURSOR),
	Snippet("strike", F, "Strike through", "\\sout{%s}" % CURSOR, pkgs=(("ulem", "normalem"),)),
	Snippet("super", F, "Superscript (text)", "\\textsuperscript{%s}" % CURSOR),
	Snippet("sub", F, "Subscript (text)", "\\textsubscript{%s}" % CURSOR),
	Snippet("small", F, "Smaller text", "{\\small %s}" % CURSOR),
	Snippet("large", F, "Larger text", "{\\large %s}" % CURSOR),
	Snippet("Large", F, "Large text", "{\\Large %s}" % CURSOR),
	Snippet("huge", F, "Huge text", "{\\huge %s}" % CURSOR),
	Snippet("quote_text", F, "Quotation marks (LaTeX style)", "``%s''" % CURSOR),
	Snippet("linebreak", F, "Line break", " \\\\\n", shortcut="Shift+Enter"),

	# ---- alignment
	Snippet("flushleft", A, "Left aligned text", "\\begin{flushleft}\n%s\n\\end{flushleft}\n" % CURSOR, block=True, shortcut="Ctrl+L"),
	Snippet("center", A, "Centered text", "\\begin{center}\n%s\n\\end{center}\n" % CURSOR, block=True, shortcut="Ctrl+E"),
	Snippet("flushright", A, "Right aligned text", "\\begin{flushright}\n%s\n\\end{flushright}\n" % CURSOR, block=True, shortcut="Ctrl+R"),
	Snippet("justify", A, "Justified text", "\\begin{justify}\n%s\n\\end{justify}\n" % CURSOR, block=True, pkgs=(("ragged2e", ""),), shortcut="Ctrl+J"),
	Snippet("align_left_par", A, "Left align this paragraph only", "{\\raggedright %s\\par}" % CURSOR),
	Snippet("align_center_par", A, "Centre this paragraph only", "{\\centering %s\\par}" % CURSOR),
	Snippet("align_right_par", A, "Right align this paragraph only", "{\\raggedleft %s\\par}" % CURSOR),
	Snippet("indent", A, "Indent the next paragraph", "\\hspace*{1.5em}"),
	Snippet("noindent", A, "No indent for this paragraph", "\\noindent "),

	# ---- lists and blocks
	Snippet("itemize", L, "Bulleted list", "\\begin{itemize}\n\t\\item %s\n\\end{itemize}\n" % CURSOR, block=True, shortcut="Ctrl+Shift+B"),
	Snippet("enumerate", L, "Numbered list", "\\begin{enumerate}\n\t\\item %s\n\\end{enumerate}\n" % CURSOR, block=True, shortcut="Ctrl+Shift+N"),
	Snippet("description", L, "Description list", "\\begin{description}\n\t\\item[%s] \n\\end{description}\n" % CURSOR, block=True),
	Snippet("item", L, "New list item", "\\item %s" % CURSOR, block=True, shortcut="Ctrl+Shift+L"),
	Snippet("quote", L, "Quote block", "\\begin{quote}\n%s\n\\end{quote}\n" % CURSOR, block=True, shortcut="Ctrl+Shift+Q"),
	Snippet("quotation", L, "Long quotation block", "\\begin{quotation}\n%s\n\\end{quotation}\n" % CURSOR, block=True),
	Snippet("verbatim", L, "Verbatim (code) block", "\\begin{verbatim}\n%s\n\\end{verbatim}\n" % CURSOR, block=True),
	Snippet("abstract", L, "Abstract", "\\begin{abstract}\n%s\n\\end{abstract}\n" % CURSOR, block=True),

	# ---- notes, poem, header/footer
	Snippet("footnote", N, "Footnote", "\\footnote{%s}" % CURSOR, shortcut="Ctrl+Shift+F"),
	Snippet("endnote", N, "Endnote", "\\endnote{%s}" % CURSOR, pkgs=(("endnotes", ""),), shortcut="Ctrl+Shift+E"),
	Snippet("theendnotes", N, "Print all endnotes here", "\\theendnotes\n", block=True, pkgs=(("endnotes", ""),)),
	Snippet("marginnote", N, "Margin note", "\\marginpar{%s}" % CURSOR),
	Snippet("poem", N, "Poem (selected lines become verse)", action="poem", shortcut="Ctrl+Shift+V"),
	Snippet("headerfooter", N, "Header and footer...", action="headerfooter", shortcut="Ctrl+Shift+H"),
	Snippet("notesetup", N, "Footnote and endnote settings...", action="notesetup"),
	Snippet("pagenumber", N, "Current page number", "\\thepage"),

	# ---- document parts
	Snippet("titlepage", D, "Title page from a template...", action="titlepage", shortcut="Ctrl+7"),
	Snippet("toc", D, "Table of contents", "\\tableofcontents\n", block=True, shortcut="Ctrl+5"),
	Snippet("lof", D, "List of figures", "\\listoffigures\n", block=True),
	Snippet("lot", D, "List of tables", "\\listoftables\n", block=True),
	Snippet("newpage", D, "New page", "\\newpage\n", block=True, shortcut="Ctrl+6"),
	Snippet("clearpage", D, "Clear page (flush floats)", "\\clearpage\n", block=True),
	Snippet("appendix", D, "Start appendices", "\\appendix\n", block=True),
	Snippet("vspace", D, "Vertical space", "\\vspace{%s1em}\n" % CURSOR, block=True),
	Snippet("hfill", D, "Fill horizontal space", "\\hfill "),
	Snippet("linespacing", D, "Line spacing", "\\setstretch{%s1.5}\n" % CURSOR, block=True, pkgs=(("setspace", ""),)),
	Snippet("comment", D, "Comment line (not printed)", "%% %s" % CURSOR, block=True, shortcut="Ctrl+Q"),
	Snippet("packages", D, "LaTeX packages...", action="packages", shortcut="Ctrl+Shift+U"),
	Snippet("input", D, "Include another .tex file...", action="input"),
	Snippet("newdoc", D, "New document skeleton...", action="newdoc"),

	# ---- references, links, images, tables
	Snippet("label", R, "Label", "\\label{%s}" % CURSOR, shortcut="Ctrl+Shift+J"),
	Snippet("ref", R, "Reference to label", "\\ref{%s}" % CURSOR, shortcut="Ctrl+Shift+R"),
	Snippet("pageref", R, "Page reference", "\\pageref{%s}" % CURSOR),
	Snippet("cite", R, "Citation", "\\cite{%s}" % CURSOR, shortcut="Ctrl+Shift+X"),
	Snippet("bibliography", R, "Bibliography (manual list)", "\\begin{thebibliography}{99}\n\\bibitem{%s} \n\\end{thebibliography}\n" % CURSOR, block=True),
	Snippet("hyperlink", R, "Hyperlink...", action="hyperlink", pkgs=(("hyperref", ""),), shortcut="Ctrl+Shift+K"),
	Snippet("image", R, "Image (picture file)...", action="image", pkgs=(("graphicx", ""),), shortcut="Ctrl+Shift+G"),
	Snippet("table", R, "Table...", action="table", shortcut="Ctrl+Shift+A"),

	# ---- mathematics
	Snippet("math_inline", M, "Inline math", "$%s$" % CURSOR, shortcut="Ctrl+Shift+M"),
	Snippet("math_display", M, "Display math", "\\[\n%s\n\\]\n" % CURSOR, block=True, shortcut="Ctrl+Shift+D"),
	Snippet("equation", M, "Numbered equation", "\\begin{equation}\n%s\n\\end{equation}\n" % CURSOR, block=True),
	Snippet("align", M, "Aligned equations", "\\begin{align}\n%s &= \n\\end{align}\n" % CURSOR, block=True, pkgs=(("amsmath", ""),)),
	Snippet("frac", M, "Fraction", "\\frac{%s}{}" % CURSOR),
	Snippet("sqrt", M, "Square root", "\\sqrt{%s}" % CURSOR),
	Snippet("msub", M, "Subscript", "_{%s}" % CURSOR),
	Snippet("msup", M, "Superscript (power)", "^{%s}" % CURSOR),
	Snippet("symbols", M, "Symbols and Greek letters...", action="symbols", shortcut="Ctrl+Shift+Y"),
]

BY_KEY = dict((s.key, s) for s in SNIPPETS)

SYMBOLS = [
	("alpha", "\\alpha"), ("beta", "\\beta"), ("gamma", "\\gamma"), ("delta", "\\delta"),
	("epsilon", "\\epsilon"), ("zeta", "\\zeta"), ("eta", "\\eta"), ("theta", "\\theta"),
	("iota", "\\iota"), ("kappa", "\\kappa"), ("lambda", "\\lambda"), ("mu", "\\mu"),
	("nu", "\\nu"), ("xi", "\\xi"), ("pi", "\\pi"), ("rho", "\\rho"), ("sigma", "\\sigma"),
	("tau", "\\tau"), ("upsilon", "\\upsilon"), ("phi", "\\phi"), ("chi", "\\chi"),
	("psi", "\\psi"), ("omega", "\\omega"),
	("capital Gamma", "\\Gamma"), ("capital Delta", "\\Delta"), ("capital Theta", "\\Theta"),
	("capital Lambda", "\\Lambda"), ("capital Pi", "\\Pi"), ("capital Sigma", "\\Sigma"),
	("capital Phi", "\\Phi"), ("capital Psi", "\\Psi"), ("capital Omega", "\\Omega"),
	("plus or minus", "\\pm"), ("minus or plus", "\\mp"), ("times", "\\times"), ("divide", "\\div"),
	("dot product", "\\cdot"), ("not equal", "\\neq"), ("approximately equal", "\\approx"),
	("less than or equal", "\\leq"), ("greater than or equal", "\\geq"),
	("much less than", "\\ll"), ("much greater than", "\\gg"), ("equivalent", "\\equiv"),
	("proportional to", "\\propto"), ("infinity", "\\infty"), ("partial derivative", "\\partial"),
	("nabla", "\\nabla"), ("sum", "\\sum"), ("product", "\\prod"), ("integral", "\\int"),
	("double integral", "\\iint"), ("contour integral", "\\oint"), ("limit", "\\lim"),
	("element of", "\\in"), ("not element of", "\\notin"), ("subset", "\\subset"),
	("subset or equal", "\\subseteq"), ("union", "\\cup"), ("intersection", "\\cap"),
	("empty set", "\\emptyset"), ("for all", "\\forall"), ("there exists", "\\exists"),
	("implies", "\\Rightarrow"), ("if and only if", "\\Leftrightarrow"),
	("right arrow", "\\rightarrow"), ("left arrow", "\\leftarrow"), ("maps to", "\\mapsto"),
	("therefore", "\\therefore"), ("because", "\\because"), ("degree", "^{\\circ}"),
	("dots (low)", "\\ldots"), ("dots (centered)", "\\cdots"), ("angle", "\\angle"),
	("perpendicular", "\\perp"), ("parallel", "\\parallel"), ("square root", "\\sqrt{}"),
	("bar over", "\\overline{}"), ("vector", "\\vec{}"), ("hat", "\\hat{}"),
	("section sign", "\\S"), ("paragraph sign", "\\P"), ("copyright", "\\copyright"),
	("dagger", "\\dagger"), ("bullet", "\\textbullet"), ("ellipsis", "\\dots"),
	("en dash", "--"), ("em dash", "---"),
]


def package_insertion(text, name, options=""):
	"""Return (index, string) to insert so that package ``name`` is loaded, or None.

	None means the package is already loaded or the text has no ``\\begin{document}``.
	"""
	rx = re.compile(r"^[^%\n]*\\usepackage(?:\[[^\]]*\])?\{([^}]*)\}", re.M)
	for m in rx.finditer(text):
		names = [n.strip() for n in m.group(1).split(",")]
		if name in names:
			return None
	m = re.search(r"^[ \t]*\\begin\{document\}", text, re.M)
	if not m:
		return None
	opt = "[%s]" % options if options else ""
	return m.start(), "\\usepackage%s{%s}\n" % (opt, name)


def used_packages(text):
	"""Names of packages loaded by \\usepackage or \\RequirePackage in ``text``."""
	names = []
	for m in re.finditer(r"^[^%\n]*\\(?:usepackage|RequirePackage)(?:\[[^\]]*\])?\{([^}]*)\}", text, re.M):
		for n in m.group(1).split(","):
			n = n.strip()
			if n and n not in names:
				names.append(n)
	return names
