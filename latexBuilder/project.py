# -*- coding: utf-8 -*-
"""Project model (several .tex files -> one document) and LaTeX skeleton generation."""

import io
import json
import os
import re

CLASSES = ["article", "report", "book"]
FONT_SIZES = ["8", "9", "10", "11", "12", "14", "17", "20"]
PAPERS = ["a4paper", "a5paper", "a3paper", "a6paper", "b5paper", "b4paper", "letterpaper", "legalpaper", "executivepaper", "custom"]
PAPER_LABELS = {
	"a4paper": "A4 (210 x 297 mm)", "a5paper": "A5 (148 x 210 mm)", "a3paper": "A3 (297 x 420 mm)",
	"a6paper": "A6 (105 x 148 mm)", "b5paper": "B5 (176 x 250 mm)", "b4paper": "B4 (250 x 353 mm)",
	"letterpaper": "US Letter", "legalpaper": "US Legal", "executivepaper": "Executive",
	"custom": "Custom size (type width and height)",
}
ORIENTATIONS = ["portrait", "landscape"]
ENGINES = ["auto", "pdflatex", "xelatex", "lualatex"]
LINE_SPACINGS = ["1", "1.15", "1.25", "1.5", "2"]
PAGE_NUMBERINGS = ["arabic", "roman", "Roman", "alph", "Alph", "none"]
PAGE_NUMBERING_LABELS = {
	"arabic": "1, 2, 3", "roman": "i, ii, iii", "Roman": "I, II, III",
	"alph": "a, b, c", "Alph": "A, B, C", "none": "No page numbers",
}

# language -> (script for fontspec, polyglossia name or None, polyglossia digits option or None, default font)
LANG_INFO = [
	("English", None, "english", None, ""),
	("Kannada", "Kannada", "kannada", "kannada", "Nirmala UI"),
	("Hindi", "Devanagari", "hindi", "devanagari", "Nirmala UI"),
	("Sanskrit", "Devanagari", "sanskrit", "devanagari", "Nirmala UI"),
	("Marathi", "Devanagari", "marathi", "devanagari", "Nirmala UI"),
	("Nepali", "Devanagari", "nepali", "devanagari", "Nirmala UI"),
	("Konkani (Devanagari script)", "Devanagari", None, None, "Nirmala UI"),
	("Tamil", "Tamil", "tamil", "tamil", "Nirmala UI"),
	("Telugu", "Telugu", "telugu", "telugu", "Nirmala UI"),
	("Malayalam", "Malayalam", "malayalam", "malayalam", "Nirmala UI"),
	("Bengali", "Bengali", "bengali", "bengali", "Nirmala UI"),
	("Assamese", "Bengali", "assamese", "bengali", "Nirmala UI"),
	("Gujarati", "Gujarati", "gujarati", "gujarati", "Nirmala UI"),
	("Punjabi (Gurmukhi)", "Gurmukhi", "punjabi", "gurmukhi", "Nirmala UI"),
	("Odia", "Oriya", None, None, "Nirmala UI"),
	("Urdu (right to left, experimental)", "Arabic", "urdu", None, "Urdu Typesetting"),
]
LANG_CODES = {
	"Kannada": "kn-IN", "Hindi": "hi-IN", "Sanskrit": "sa-IN", "Marathi": "mr-IN", "Nepali": "ne-NP",
	"Konkani (Devanagari script)": "kok-IN", "Tamil": "ta-IN", "Telugu": "te-IN", "Malayalam": "ml-IN",
	"Bengali": "bn-IN", "Assamese": "as-IN", "Gujarati": "gu-IN", "Punjabi (Gurmukhi)": "pa-IN",
	"Odia": "or-IN", "Urdu (right to left, experimental)": "ur-IN",
}
LANGUAGES = [l[0] for l in LANG_INFO]
LANG_BY_NAME = dict((l[0], l) for l in LANG_INFO)

DEFAULT_OPTIONS = {
	# document
	"documentclass": "article", "title": "", "author": "", "date": "\\today",
	"maketitle": True, "toc": False, "twoside": False, "columns": "1", "columnsep": "", "columnrule": False,
	# language and fonts
	"language": "English", "use_polyglossia": False, "native_digits": False,
	"mainfont": "", "sansfont": "", "monofont": "", "fontsize": "12", "font_scale": "1",
	"fake_bold": "", "fake_italic": "", "letterspace": "",
	"bold_font": "", "italic_font": "", "bolditalic_font": "",
	# page
	"paper": "a4paper", "orientation": "portrait", "paper_width": "", "paper_height": "",
	"margin_all": "2.5cm", "margin_top": "", "margin_bottom": "", "margin_left": "", "margin_right": "",
	"bindingoffset": "", "headsep": "", "footskip": "",
	# text layout
	"spacing": "1", "parindent": "", "parskip": "", "pagenumbering": "arabic", "firstpage": "",
	# packages
	"amsmath": True, "graphicx": True, "hyperref": True, "extra_preamble": "",
	# advanced (set by the importer)
	"class_extra": "", "class_line": "", "use_geometry": True, "geometry_raw": "",
	"script_fontfamily": True, "legacy_fonts": True,
	# title page design
	"titlepage_template": "standard", "tp_subtitle": "", "tp_institution": "", "tp_department": "", "tp_extra": "", "tp_logo": "",
	# footnotes
	"fn_numbering": "continuous", "fn_style": "arabic", "fn_size": "", "fn_font": "", "fn_layout": "standard",
	"fn_rule": True, "fn_bottom": False, "fn_sep": "",
	# endnotes
	"en_use": False, "en_title": "", "en_size": "", "en_style": "arabic", "en_numbering": "continuous", "en_auto": True,
}

TITLEPAGE_TEMPLATES = [
	("standard", "Standard: title, author and date at the top, text follows on the same page"),
	("centered", "Centered: title page on its own page, everything centered"),
	("book", "Book cover: title between two rules, author, publisher and year at the bottom"),
	("thesis", "Thesis or report: institution, department, title between rules, degree line, author"),
	("left", "Minimal: left aligned with a short rule"),
	("boxed", "Boxed: title, author and date inside a frame"),
]
FN_NUMBERINGS = [
	("continuous", "Continue through the whole document"),
	("page", "Restart on every page"),
	("chapter", "Restart in every chapter (in articles: every section)"),
	("section", "Restart in every section"),
]
EN_NUMBERINGS = [FN_NUMBERINGS[0], FN_NUMBERINGS[2], FN_NUMBERINGS[3]]
NOTE_STYLES = [
	("arabic", "Numbers: 1, 2, 3"), ("roman", "Small roman: i, ii, iii"), ("Roman", "Capital roman: I, II, III"),
	("alph", "Letters: a, b, c"), ("Alph", "Capital letters: A, B, C"),
	("fnsymbol", "Symbols: * and dagger, double dagger, section, paragraph... (nine symbols; best with restart on every page)"),
]
NOTE_SIZES = [
	("", "Default size"), ("scriptsize", "Very small"), ("footnotesize", "Small"), ("small", "Medium small"),
	("normalsize", "Same size as the text"), ("large", "Large"),
]
FN_LAYOUTS = [
	("standard", "Standard: first line indented"),
	("hang", "Hanging: the lines after the first are indented under the text"),
	("flushmargin", "Flush with the margin, no indent"),
]


def normalize_options(opts):
	"""Merge with defaults and migrate options saved by version 1.0."""
	src = dict(opts or {})
	o = dict(DEFAULT_OPTIONS)
	o.update(src)
	if "margin" in src and "margin_all" not in src:
		o["margin_all"] = src["margin"]
	o.pop("margin", None)
	o["fontsize"] = re.sub(r"[^0-9]", "", str(o.get("fontsize", "12"))) or "12"
	lang = str(o.get("language", "English"))
	if lang not in LANG_BY_NAME:
		lang = next((n for n in LANGUAGES if lang.lower().startswith(n.split(" ")[0].lower())), "English")
	o["language"] = lang
	if o.get("paper") not in PAPERS:
		o["paper"] = "a4paper"
	return o


def language_info(o):
	return LANG_BY_NAME.get(normalize_options(o)["language"], LANG_INFO[0])


def needs_xelatex(opts):
	o = normalize_options(opts)
	return o["language"] != "English" or bool(o["mainfont"].strip() or o["sansfont"].strip() or o["monofont"].strip() or o["fn_font"].strip())


is_kannada = needs_xelatex  # old name kept for compatibility


def _size_and_class(o):
	n = int(o["fontsize"])
	base = o["documentclass"]
	if n in (10, 11, 12):
		return base, n
	allowed = [8, 9, 10, 11, 12, 14, 17, 20]
	n = min(allowed, key=lambda a: abs(a - n))
	if n in (10, 11, 12):
		return base, n
	return "ext" + base, n


def _num(v):
	v = str(v).strip()
	return v if v and v not in ("1", "1.0") else ""


def _fontspec_options(o, script, full):
	opts = []
	if script:
		opts.append("Script=%s" % script)
	if _num(o.get("font_scale")):
		opts.append("Scale=%s" % o["font_scale"].strip())
	if full:
		if str(o.get("fake_bold", "")).strip():
			opts.append("AutoFakeBold=%s" % o["fake_bold"].strip())
		if str(o.get("fake_italic", "")).strip():
			opts.append("AutoFakeSlant=%s" % o["fake_italic"].strip())
		if str(o.get("letterspace", "")).strip():
			opts.append("LetterSpace=%s" % o["letterspace"].strip())
		for key, name in (("bold_font", "BoldFont"), ("italic_font", "ItalicFont"), ("bolditalic_font", "BoldItalicFont")):
			if str(o.get(key, "")).strip():
				opts.append("%s={%s}" % (name, o[key].strip()))
	return "[%s]" % ",".join(opts) if opts else ""


def _geometry(o):
	if o.get("geometry_raw", "").strip():
		return o["geometry_raw"].strip()
	opts = []
	if o["paper"] == "custom":
		w, h = o["paper_width"].strip() or "21cm", o["paper_height"].strip() or "29.7cm"
		opts += ["paperwidth=%s" % w, "paperheight=%s" % h]
	else:
		opts.append(o["paper"])
	if o["orientation"] == "landscape":
		opts.append("landscape")
	uniform = o["margin_all"].strip()
	if uniform:
		opts.append("margin=%s" % uniform)
	left, right = ("inner", "outer") if o["twoside"] else ("left", "right")
	for key, name in (("margin_top", "top"), ("margin_bottom", "bottom"), ("margin_left", left), ("margin_right", right),
					("bindingoffset", "bindingoffset"), ("headsep", "headsep"), ("footskip", "footskip")):
		if o[key].strip():
			opts.append("%s=%s" % (name, o[key].strip()))
	return "\\usepackage[%s]{geometry}" % ",".join(opts)


def _lines(text):
	return [l.strip() for l in str(text).replace("\r", "").split("\n") if l.strip()]


def titlepage_code(opts):
	"""LaTeX for the chosen title page design, or None for the standard \\maketitle."""
	o = normalize_options(opts)
	t = o["titlepage_template"]
	if t == "standard":
		return None
	title, sub, author, date = o["title"], o["tp_subtitle"].strip(), o["author"], o["date"].strip()
	inst, dept = o["tp_institution"].strip(), o["tp_department"].strip()
	extra = " \\\\\n".join(_lines(o["tp_extra"]))
	logo = o["tp_logo"].strip().replace("\\", "/")
	L = ["\\begin{titlepage}"]

	def add(*x):
		L.extend(x)

	logo_line = "\\includegraphics[height=3cm]{%s}\\par\\vspace{1cm}" % logo if logo else ""
	if t == "centered":
		add("\\centering")
		if logo_line:
			add("\\vspace*{1cm}", logo_line)
		add("\\vspace*{\\fill}", "{\\Huge\\bfseries %s\\par}" % title)
		if sub:
			add("\\vspace{0.6cm}", "{\\Large %s\\par}" % sub)
		if author:
			add("\\vspace{1.5cm}", "{\\Large %s\\par}" % author)
		if date:
			add("\\vspace{0.5cm}", "{\\large %s\\par}" % date)
		add("\\vspace*{\\fill}")
		for part in (inst, dept, extra):
			if part:
				add("{\\large %s\\par}" % part)
	elif t == "book":
		add("\\centering", "\\vspace*{2cm}", "\\rule{\\textwidth}{1.5pt}\\par", "\\vspace{0.8cm}",
			"{\\fontsize{34}{40}\\selectfont\\bfseries %s\\par}" % title)
		if sub:
			add("\\vspace{0.4cm}", "{\\LARGE\\itshape %s\\par}" % sub)
		add("\\vspace{0.8cm}", "\\rule{\\textwidth}{1.5pt}\\par")
		if author:
			add("\\vspace{2cm}", "{\\Huge %s\\par}" % author)
		add("\\vfill")
		for part in (inst, dept, extra, date):
			if part:
				add("{\\Large %s\\par}" % part)
	elif t == "thesis":
		add("\\centering")
		if logo_line:
			add(logo_line)
		if inst:
			add("{\\Large\\scshape %s\\par}" % inst, "\\vspace{0.3cm}")
		if dept:
			add("{\\large %s\\par}" % dept)
		add("\\vspace{2cm}", "\\rule{\\textwidth}{0.8pt}\\par", "\\vspace{0.4cm}", "{\\huge\\bfseries %s\\par}" % title)
		if sub:
			add("\\vspace{0.2cm}", "{\\Large %s\\par}" % sub)
		add("\\rule{\\textwidth}{0.8pt}\\par")
		if extra:
			add("\\vspace{1.5cm}", "{\\large %s\\par}" % extra)
		if author:
			add("\\vspace{1cm}", "{\\Large\\bfseries %s\\par}" % author)
		add("\\vfill")
		if date:
			add("{\\large %s\\par}" % date)
	elif t == "left":
		add("\\raggedright", "\\vspace*{3cm}", "{\\Huge\\bfseries %s\\par}" % title)
		if sub:
			add("\\vspace{0.4cm}", "{\\Large %s\\par}" % sub)
		add("\\vspace{0.4cm}", "\\rule{0.4\\textwidth}{1pt}\\par", "\\vspace{0.6cm}")
		if author:
			add("{\\large %s\\par}" % author)
		if date:
			add("{\\large %s\\par}" % date)
		add("\\vfill")
		block = " \\\\\n".join(x for x in (inst, dept, extra) if x)
		if block:
			add("{\\large %s\\par}" % block)
	elif t == "boxed":
		add("\\centering", "\\vspace*{\\fill}", "\\fbox{\\parbox{0.85\\textwidth}{\\centering\\vspace{1cm}",
			"{\\Huge\\bfseries %s\\par}" % title)
		if sub:
			add("\\vspace{0.4cm}", "{\\Large %s\\par}" % sub)
		if author:
			add("\\vspace{0.8cm}", "{\\large %s\\par}" % author)
		if date:
			add("\\vspace{0.3cm}", "{\\large %s\\par}" % date)
		add("\\vspace{1cm}}}", "\\vspace*{\\fill}")
		for part in (inst, dept, extra):
			if part:
				add("{\\large %s\\par}" % part)
	else:
		return None
	add("\\end{titlepage}")
	return "\n".join(L) + "\n"


def title_block(opts):
	"""Code that prints the title: the chosen design, or \\maketitle."""
	o = normalize_options(opts)
	if not (o.get("maketitle") and (o.get("title") or o.get("author"))):
		return ""
	return titlepage_code(o) or "\\maketitle\n"


def notes_preamble(opts, xe=False):
	"""Preamble lines for footnote and endnote numbering, style, size, font and layout."""
	o = normalize_options(opts)
	lines = []
	has_chapter = o["documentclass"] in ("report", "book")
	fm = []
	if o["fn_numbering"] == "page":
		fm.append("perpage")
	if o["fn_layout"] in ("hang", "flushmargin"):
		fm.append(o["fn_layout"])
	if not o["fn_rule"]:
		fm.append("norule")
	if o["fn_bottom"]:
		fm.append("bottom")
	font = o["fn_font"].strip()
	use_hook = bool(o["fn_size"] or (font and xe))
	if fm or use_hook:
		lines.append("\\usepackage[%s]{footmisc}" % ",".join(fm) if fm else "\\usepackage{footmisc}")
	if o["fn_numbering"] in ("chapter", "section"):
		unit = o["fn_numbering"] if (o["fn_numbering"] == "section" or has_chapter) else "section"
		lines += ["\\usepackage{chngcntr}", "\\counterwithin*{footnote}{%s}" % unit]
	if o["fn_style"] != "arabic":
		form = "\\fnsymbol{footnote}" if o["fn_style"] == "fnsymbol" else "\\%s{footnote}" % o["fn_style"]
		lines.append("\\renewcommand{\\thefootnote}{%s}" % form)
	if use_hook:
		parts = ""
		if font and xe:
			lines.append("\\newfontfamily\\lbnotefont{%s}" % font)
			parts += "\\lbnotefont"
		if o["fn_size"]:
			parts += "\\" + o["fn_size"]
		lines.append("\\renewcommand{\\footnotelayout}{%s}" % parts)
	if o["fn_sep"].strip():
		lines.append("\\setlength{\\footnotesep}{%s}" % o["fn_sep"].strip())
	# endnotes
	if o["en_use"] or o["en_title"].strip() or o["en_size"] or o["en_style"] != "arabic" or o["en_numbering"] != "continuous":
		lines.append("\\usepackage{endnotes}")
		if o["en_use"]:
			lines.append("\\let\\footnote=\\endnote")
		if o["en_title"].strip():
			lines.append("\\renewcommand{\\notesname}{%s}" % o["en_title"].strip())
		if o["en_size"]:
			lines.append("\\renewcommand{\\enotesize}{\\%s}" % o["en_size"])
		if o["en_style"] != "arabic":
			form = "\\fnsymbol{endnote}" if o["en_style"] == "fnsymbol" else "\\%s{endnote}" % o["en_style"]
			lines.append("\\renewcommand{\\theendnote}{%s}" % form)
		if o["en_numbering"] in ("chapter", "section"):
			unit = o["en_numbering"] if (o["en_numbering"] == "section" or has_chapter) else "section"
			lines += ["\\usepackage{chngcntr}", "\\counterwithin*{endnote}{%s}" % unit]
	return lines


def _loads(extra, names):
	return bool(re.search(r"\\usepackage(?:\[[^\]]*\])?\{[^}]*\b(?:%s)\b" % "|".join(names), extra))


def build_preamble(opts):
	o = normalize_options(opts)
	info = LANG_BY_NAME[o["language"]]
	script = info[1]
	extra_text = (o.get("extra_preamble") or "")
	xe = needs_xelatex(o) or _loads(extra_text, ("fontspec", "polyglossia", "unicode-math"))
	cls, size = _size_and_class(o)
	copts = ["%dpt" % size]
	if not o["use_geometry"] and not o["geometry_raw"].strip():
		if o["paper"] != "custom":
			copts.append(o["paper"])
		if o["orientation"] == "landscape":
			copts.append("landscape")
	if o["twoside"]:
		copts.append("twoside")
	if str(o["columns"]) == "2":
		copts.append("twocolumn")
	if o["class_extra"].strip():
		copts.append(o["class_extra"].strip())
	if o["class_line"].strip():
		lines = [o["class_line"].strip()]
	else:
		lines = ["\\documentclass[%s]{%s}" % (",".join(copts), cls)]
	main = o["mainfont"].strip() or info[4]
	fl = []
	if xe:
		if not _loads(extra_text, ("fontspec",)):
			fl.append("\\usepackage{fontspec}")
		poly = bool(o["use_polyglossia"] and info[2] and info[0] != "English")
		if poly:
			fl.append("\\usepackage{polyglossia}")
			dig = "[numerals=%s]" % info[3] if (o["native_digits"] and info[3]) else ""
			fl.append("\\setmainlanguage%s{%s}" % (dig, info[2]))
			fl.append("\\setotherlanguage{english}")
		if main:
			fl.append("\\setmainfont%s{%s}" % (_fontspec_options(o, script, True), main))
			if poly and script and o["script_fontfamily"]:
				fl.append("\\newfontfamily\\%sfont%s{%s}" % (script.lower(), _fontspec_options(o, script, True), main))
		if o["sansfont"].strip():
			fl.append("\\setsansfont%s{%s}" % (_fontspec_options(o, script, False), o["sansfont"].strip()))
		if o["monofont"].strip():
			fl.append("\\setmonofont%s{%s}" % (_fontspec_options(o, None, False), o["monofont"].strip()))
	elif o["legacy_fonts"]:
		lines += ["\\usepackage[T1]{fontenc}", "\\usepackage[utf8]{inputenc}", "\\usepackage{lmodern}"]
	defer_fonts = _loads(extra_text, ("fontspec",))
	if not defer_fonts:
		lines += fl
	if o["use_geometry"] or o["geometry_raw"].strip():
		lines.append(_geometry(o))
	if str(o["spacing"]).strip() not in ("", "1"):
		lines += ["\\usepackage{setspace}", "\\setstretch{%s}" % o["spacing"].strip()]
	if o["parindent"].strip():
		lines.append("\\setlength{\\parindent}{%s}" % o["parindent"].strip())
	if o["parskip"].strip():
		lines.append("\\setlength{\\parskip}{%s}" % o["parskip"].strip())
	if str(o["columns"]) == "2":
		if o["columnsep"].strip():
			lines.append("\\setlength{\\columnsep}{%s}" % o["columnsep"].strip())
		if o["columnrule"]:
			lines.append("\\setlength{\\columnseprule}{0.4pt}")
	if o["pagenumbering"] == "none":
		lines.append("\\pagestyle{empty}")
	if o["amsmath"]:
		lines.append("\\usepackage{amsmath,amssymb}")
	if o["graphicx"] or o["tp_logo"].strip():
		lines.append("\\usepackage{graphicx}")
	extra = (o.get("extra_preamble") or "").strip("\n")
	if extra:
		lines.append(extra)
	if defer_fonts:
		lines += fl
	lines += notes_preamble(o, xe)
	if o["hyperref"]:
		lines.append("\\usepackage{hyperref}")
	if o["title"]:
		lines.append("\\title{%s}" % o["title"])
	if o["author"]:
		lines.append("\\author{%s}" % o["author"])
	if o["title"] or o["author"]:
		lines.append("\\date{%s}" % (o.get("date") or ""))
	return "\n".join(lines) + "\n"


def body_start(opts):
	"""Lines placed right after \\begin{document}."""
	o = normalize_options(opts)
	out = []
	if o["pagenumbering"] not in ("arabic", "none"):
		out.append("\\pagenumbering{%s}" % o["pagenumbering"])
	if o["firstpage"].strip().lstrip("-").isdigit():
		out.append("\\setcounter{page}{%s}" % o["firstpage"].strip())
	return out


def build_skeleton(opts):
	"""Complete small document used by 'New document'."""
	o = normalize_options(opts)
	out = [build_preamble(o), "\\begin{document}\n"]
	bs = body_start(o)
	if bs:
		out.append("\n".join(bs) + "\n")
	tb = title_block(o)
	if tb:
		out.append(tb)
	if o.get("toc"):
		out.append("\\tableofcontents\n\\newpage\n")
	first = "chapter" if o["documentclass"] in ("report", "book") else "section"
	out.append("\\%s{}\n" % first)
	out.append("\n\\end{document}\n")
	return "\n".join(out)


class Project(object):
	def __init__(self, path=None):
		self.path = path
		self.name = "Untitled project"
		self.files = []  # absolute paths, in order
		self.options = normalize_options({})
		self.engine = "auto"
		self.use_include = False  # True -> \include (each part on a new page)
		self.own_preamble = False  # True -> use preamble found in the first part that has one
		self.main_file = ""  # an imported main .tex file
		self.root_dir = ""  # folder of the imported project (relative \\input paths start here)
		self.build_original = False  # True -> compile main_file as it is
		self.body_template = None  # body of the imported main file with {{INPUT:n}} markers
		self.use_body_template = True

	# ------------------------------------------------------------ persistence
	def folder(self):
		return os.path.dirname(self.path) if self.path else os.getcwd()

	def to_json(self):
		base = self.folder()
		rel = []
		for f in self.files:
			try:
				rel.append(os.path.relpath(f, base))
			except ValueError:
				rel.append(f)
		return {
			"name": self.name,
			"files": rel,
			"options": self.options,
			"engine": self.engine,
			"use_include": self.use_include,
			"own_preamble": self.own_preamble,
			"main_file": self._rel(self.main_file),
			"root_dir": self._rel(self.root_dir),
			"build_original": self.build_original,
			"body_template": self.body_template,
			"use_body_template": self.use_body_template,
		}

	def _rel(self, f):
		if not f:
			return ""
		try:
			return os.path.relpath(f, self.folder())
		except ValueError:
			return f

	def save(self, path=None):
		if path:
			self.path = path
		with io.open(self.path, "w", encoding="utf-8") as fh:
			json.dump(self.to_json(), fh, ensure_ascii=False, indent=2)

	@classmethod
	def load(cls, path):
		with io.open(path, "r", encoding="utf-8") as fh:
			data = json.load(fh)
		p = cls(path)
		p.name = data.get("name", os.path.splitext(os.path.basename(path))[0])
		base = os.path.dirname(path)
		p.files = [os.path.normpath(f if os.path.isabs(f) else os.path.join(base, f)) for f in data.get("files", [])]
		p.options = normalize_options(data.get("options", {}))
		p.engine = data.get("engine", "auto")
		p.use_include = bool(data.get("use_include", False))
		p.own_preamble = bool(data.get("own_preamble", False))

		def absolute(v):
			return os.path.normpath(v if os.path.isabs(v) else os.path.join(base, v)) if v else ""

		p.main_file = absolute(data.get("main_file", ""))
		p.root_dir = absolute(data.get("root_dir", ""))
		p.build_original = bool(data.get("build_original", False))
		p.body_template = data.get("body_template")
		p.use_body_template = bool(data.get("use_body_template", True))
		return p


def read_text_file(path):
	for enc in ("utf-8-sig", "cp1252", "latin-1"):
		try:
			with io.open(path, "r", encoding=enc, newline="") as fh:
				return fh.read().replace("\r\n", "\n").replace("\r", "\n")
		except UnicodeDecodeError:
			continue
		except FileNotFoundError:
			raise
	return ""


def write_text_file(path, text):
	with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
		fh.write(text)


def split_document(text):
	"""Return (preamble, body, line_offset) if text is a full document, else (None, text, 0)."""
	m = re.search(r"^[ \t]*\\begin\{document\}[ \t]*\n?", text, re.M)
	if not m:
		return None, text, 0
	pre = text[:m.start()]
	rest = text[m.end():]
	e = re.search(r"^[ \t]*\\end\{document\}", rest, re.M)
	body = rest[:e.start()] if e else rest
	return pre, body, text[:m.end()].count("\n")


def fwd(path):
	"""Path formatted for \\input / \\includegraphics (forward slashes)."""
	return os.path.abspath(path).replace("\\", "/")


def prepare_project_build(project, build_dir, read=read_text_file):
	"""Write main.tex and part files into build_dir.

	Returns (main_path, mapping, notes, offsets). mapping: build file basename -> original path;
	offsets: build file basename -> number of lines to add to get the original line number.
	"""
	os.makedirs(build_dir, exist_ok=True)
	mapping = {}
	offsets = {}
	notes = []
	bodies = []
	found_pre = None
	for idx, src in enumerate(project.files, 1):
		try:
			text = read(src)
		except (IOError, OSError):
			notes.append("File not found, skipped: %s" % src)
			continue
		pre, body, off = split_document(text)
		if pre is not None:
			if found_pre is None and re.search(r"\\documentclass", pre):
				found_pre = pre
			notes.append("%s is a complete document; only its body is used." % os.path.basename(src))
		name = "part%02d" % idx
		bodies.append((name, body, src))
		offsets[name + ".tex"] = off
	if project.own_preamble and found_pre:
		preamble = found_pre.rstrip("\n") + "\n"
	else:
		preamble = build_preamble(project.options)
	alltext = "\n".join(b for _n, b, _s in bodies)
	_o = normalize_options(project.options)
	uses_end = "\\endnote" in alltext or _o["en_use"]
	if uses_end and not re.search(r"\\usepackage(\[[^\]]*\])?\{[^}]*endnotes", preamble):
		preamble += "\\usepackage{endnotes}\n"
	main = [preamble, "\\begin{document}\n"]
	o = normalize_options(project.options)
	use_template = bool(project.body_template and project.use_body_template)
	if use_template:
		alltext += "\n" + project.body_template
	if not use_template:
		if not project.own_preamble and body_start(o):
			main.append("\n".join(body_start(o)) + "\n")
		if not project.own_preamble:
			tb = title_block(o)
			if tb:
				main.append(tb)
		if o.get("toc"):
			main.append("\\tableofcontents\n\\newpage\n")
	cmd = "include" if project.use_include else "input"
	names_by_index = {}
	for name, body, src in bodies:
		fname = name + ".tex"
		write_text_file(os.path.join(build_dir, fname), body if body.endswith("\n") else body + "\n")
		mapping[fname] = src
		names_by_index[int(name[4:]) - 1] = name
		if not use_template:
			main.append("%% ---- %s\n\\%s{%s}\n" % (os.path.basename(src), cmd, name))
	if use_template:
		used = set()

		def sub(m):
			k = int(m.group(2))
			if k >= len(project.files):
				return ""
			used.add(k)
			if k not in names_by_index:
				return "%% missing file"
			return "\\%s{%s}" % ("include" if m.group(1) == "INCLUDE" else "input", names_by_index[k])

		rendered = re.sub(r"\{\{(INPUT|INCLUDE|SUBFILE):(\d+)\}\}", sub, project.body_template)
		main.append(rendered if rendered.endswith("\n") else rendered + "\n")
		for k in sorted(names_by_index):
			if k not in used and not re.search(r"\{\{[A-Z]+:%d\}\}" % k, project.body_template):
				main.append("%% ---- %s (added to the project)\n\\input{%s}\n" % (os.path.basename(project.files[k]), names_by_index[k]))
	if uses_end and _o["en_auto"] and "\\theendnotes" not in alltext:
		main.append("\\theendnotes\n")
	main.append("\\end{document}\n")
	main_path = os.path.join(build_dir, "main.tex")
	write_text_file(main_path, "\n".join(main))
	mapping["main.tex"] = main_path
	return main_path, mapping, notes, offsets
