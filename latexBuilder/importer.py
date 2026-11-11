# -*- coding: utf-8 -*-
"""Import an existing LaTeX project (a main .tex file made in any editor).

The preamble is analysed: settings that LaTeX Builder understands (class, font size, paper, margins,
fonts, language, title, author, date, line spacing and so on) become project settings. Every other
preamble line is kept word for word as 'extra preamble', so nothing is lost. The body of the main
file is kept as a template in which \\input / \\include / \\subfile commands point to project files.
"""

import os
import re

from . import project as P
from . import texparse as T

PART_RE = re.compile(r"\\(input|include|subfile)\s*\{([^{}]+)\}")
TOKEN_RE = re.compile(r"\{\{(INPUT|INCLUDE|SUBFILE):(\d+)\}\}")

PAPER_WORDS = set(P.PAPERS) - {"custom"}


class ImportProblem(Exception):
	pass


class ImportResult(object):
	def __init__(self):
		self.options = P.normalize_options({})
		self.files = []
		self.missing = []
		self.body_template = None
		self.notes = []
		self.recognised = []
		self.kept = []
		self.root = ""
		self.main = ""
		self.engine = "auto"

	def report(self):
		out = ["Import report for %s" % self.main, ""]
		out.append("Folder of the project: %s" % self.root)
		out.append("Build engine: %s" % self.engine)
		out.append("")
		out.append("Recognised and converted into project settings (%d):" % len(self.recognised))
		out += ["  " + r for r in self.recognised] or ["  nothing"]
		out.append("")
		extra = [l for l in self.options.get("extra_preamble", "").split("\n") if l.strip()]
		out.append("Kept word for word as extra preamble: %d line(s)." % len(extra))
		out.append("")
		out.append("Files of the project, in the order they are used (%d):" % len(self.files))
		out += ["  %d. %s" % (i + 1, os.path.relpath(f, self.root) if self._inside(f) else f) for i, f in enumerate(self.files)] or ["  none found"]
		if self.missing:
			out.append("")
			out.append("Files that were mentioned but were not found (%d):" % len(self.missing))
			out += ["  " + m for m in self.missing]
		if self.notes:
			out.append("")
			out.append("Notes:")
			out += ["  " + n for n in self.notes]
		return "\n".join(out)

	def _inside(self, f):
		try:
			return not os.path.relpath(f, self.root).startswith("..")
		except ValueError:
			return False


# ------------------------------------------------------------------ small parsing helpers

def _comment_index(line):
	i = 0
	while i < len(line):
		if line[i] == "\\":
			i += 2
			continue
		if line[i] == "%":
			return i
		i += 1
	return -1


def _strip_comments(text):
	out = []
	for ln in text.split("\n"):
		c = _comment_index(ln)
		out.append(ln[:c] if c >= 0 else ln)
	return "\n".join(out)


def _balanced_at(s, i):
	"""s[i] is '{'. Return (content, index after the closing brace) or (None, i)."""
	depth = 0
	j = i
	while j < len(s):
		c = s[j]
		if c == "\\":
			j += 2
			continue
		if c == "{":
			depth += 1
		elif c == "}":
			depth -= 1
			if depth == 0:
				return s[i + 1:j], j + 1
		j += 1
	return None, i


def _stmt_re(name):
	return re.compile(r"\\" + name + r"(?![A-Za-z])\s*(?:\[([^\]]*)\])?\s*\{")


def _take(s, name):
	"""Remove the first \\name[opt]{content} from s. Returns (content, opt, new_s) or None."""
	m = _stmt_re(name).search(s)
	if not m:
		return None
	content, j = _balanced_at(s, m.end() - 1)
	if content is None:
		return None
	return content, m.group(1), s[:m.start()] + s[j:]


def _parse_kv(opt):
	"""'a=1, b={x,y}, c' -> [('a','1'), ('b','x,y'), ('c', None)]"""
	parts, depth, cur = [], 0, []
	for ch in opt or "":
		if ch == "{":
			depth += 1
		elif ch == "}":
			depth -= 1
		if ch == "," and depth == 0:
			parts.append("".join(cur))
			cur = []
		else:
			cur.append(ch)
	parts.append("".join(cur))
	out = []
	for p in parts:
		p = p.strip()
		if not p:
			continue
		if "=" in p:
			k, v = p.split("=", 1)
			v = v.strip()
			if v.startswith("{") and v.endswith("}"):
				v = v[1:-1]
			out.append((k.strip(), v))
		else:
			out.append((p, None))
	return out


def _lang_for_script(script):
	for info in P.LANG_INFO:
		if info[1] == script:
			return info[0]
	return None


# ------------------------------------------------------------------ main entry

def import_main(path, read=P.read_text_file):
	res = ImportResult()
	path = os.path.abspath(path)
	res.main = path
	res.root = os.path.dirname(path)
	try:
		raw = read(path)
	except (IOError, OSError) as exc:
		raise ImportProblem("Could not read %s: %s" % (path, exc))
	pre, body, _off = P.split_document(raw)
	if pre is None or "\\documentclass" not in pre:
		raise ImportProblem("This file has no \\documentclass and \\begin{document}, so it is not a complete main file.")

	o = res.options
	notes, rec = res.notes, res.recognised
	for k in ("margin_all",):
		o[k] = ""
	o.update({"amsmath": False, "graphicx": False, "hyperref": False, "legacy_fonts": False,
		"maketitle": "\\maketitle" in body, "toc": "\\tableofcontents" in body, "date": "\\today", "paper": "letterpaper"})

	# engine from magic comments or hints
	m = re.search(r"%\s*!\s*TEX\s+(?:TS-)?program\s*=\s*(\w+)", raw, re.I)
	if m and m.group(1).lower() in ("pdflatex", "xelatex", "lualatex"):
		res.engine = m.group(1).lower()
		rec.append("Engine from the magic comment: %s" % res.engine)

	s = _strip_comments(pre)

	# ---- document class
	m = re.search(r"\\documentclass\s*(?:\[([^\]]*)\])?\s*\{([^}]*)\}", s)
	cls = m.group(2).strip()
	opts = [x.strip() for x in (m.group(1) or "").split(",") if x.strip()]
	base = cls[3:] if cls.startswith("ext") and cls[3:] in P.CLASSES else cls
	if base in P.CLASSES:
		o["documentclass"] = base
		keep = []
		for op in opts:
			if re.fullmatch(r"\d+pt", op):
				o["fontsize"] = op[:-2]
			elif op in PAPER_WORDS:
				o["paper"] = op
			elif op == "twoside":
				o["twoside"] = True
			elif op == "twocolumn":
				o["columns"] = "2"
			elif op == "landscape":
				o["orientation"] = "landscape"
			elif op in ("oneside", "onecolumn"):
				pass
			else:
				keep.append(op)
		o["class_extra"] = ",".join(keep)
		rec.append("Document class %s, %s points, paper %s%s" % (base, o["fontsize"], o["paper"], (", extra options " + o["class_extra"]) if keep else ""))
		if cls.startswith("ext"):
			notes.append("The extsizes class %s was converted to %s with a larger font size." % (cls, base))
	else:
		o["class_line"] = m.group(0)
		rec.append("Document class %s (kept as the original \\documentclass line)" % cls)
		notes.append("The document class %s is not article, report or book, so the original \\documentclass line is used as it is and the font size and two-sided/columns settings are not applied." % cls)
	s = s[:m.start()] + s[m.end():]

	# ---- geometry
	geo = []
	for rx in (re.compile(r"\\usepackage\s*(?:\[([^\]]*)\])?\s*\{geometry\}"), re.compile(r"\\geometry\s*\{([^{}]*)\}")):
		for mm in rx.finditer(s):
			geo.append(mm)
	if geo:
		ok = True
		parsed = []
		for mm in geo:
			parsed += _parse_kv(mm.group(1) or "")
		for k, v in parsed:
			if k in PAPER_WORDS or k in ("landscape", "portrait"):
				continue
			if k in ("margin", "top", "bottom", "left", "right", "inner", "outer", "bindingoffset", "headsep", "footskip", "paperwidth", "paperheight") and v and "," not in v and "{" not in v:
				continue
			ok = False
		if ok:
			o["use_geometry"] = True
			for k, v in parsed:
				if k in PAPER_WORDS:
					o["paper"] = k
				elif k == "landscape":
					o["orientation"] = "landscape"
				elif k == "margin":
					o["margin_all"] = v
				elif k in ("top", "bottom"):
					o["margin_" + k] = v
				elif k in ("left", "inner"):
					o["margin_left"] = v
					if k == "inner":
						o["twoside"] = True
				elif k in ("right", "outer"):
					o["margin_right"] = v
				elif k in ("bindingoffset", "headsep", "footskip"):
					o[k] = v
				elif k == "paperwidth":
					o["paper_width"] = v
				elif k == "paperheight":
					o["paper_height"] = v
			if o["paper_width"] and o["paper_height"]:
				o["paper"] = "custom"
			rec.append("Page size and margins from the geometry package")
		else:
			o["use_geometry"] = True
			o["geometry_raw"] = "\n".join(mm.group(0) for mm in geo)
			notes.append("The geometry settings use options that the settings dialog cannot show, so the original geometry lines are kept as they are.")
			rec.append("Geometry lines kept as they are")
		for mm in sorted(geo, key=lambda x: -x.start()):
			s = s[:mm.start()] + s[mm.end():]
	else:
		o["use_geometry"] = False
		rec.append("No geometry package: the LaTeX class defaults for page size and margins are kept")

	# ---- polyglossia language
	poly = re.search(r"\\usepackage\s*(?:\[[^\]]*\])?\s*\{polyglossia\}", s)
	ml = _stmt_re("setmainlanguage").search(s)
	if poly and ml:
		content, j = _balanced_at(s, ml.end() - 1)
		name = (content or "").strip().lower()
		info = next((i for i in P.LANG_INFO if i[2] == name and i[0] != "English"), None)
		kv = _parse_kv(ml.group(1) or "")
		simple = all(k == "numerals" for k, _v in kv)
		if info and simple:
			o["language"] = info[0]
			o["use_polyglossia"] = True
			o["native_digits"] = any(k == "numerals" and v and v != "western" for k, v in kv)
			s = s[:ml.start()] + s[j:]
			poly = re.search(r"\\usepackage\s*(?:\[[^\]]*\])?\s*\{polyglossia\}", s)
			s = s[:poly.start()] + s[poly.end():]
			s = re.sub(r"\\setotherlanguage\s*\{english\}", "", s)
			rec.append("Language %s with polyglossia%s" % (info[0], " and native digits" if o["native_digits"] else ""))
			script = info[1]
			if script:
				fm = re.search(r"\\newfontfamily\s*\\" + script.lower() + r"font\s*(?:\[([^\]]*)\])?\s*\{([^}]*)\}", s)
				if fm:
					fopts = _parse_kv(fm.group(1) or "")
					if all(k in ("Script", "Scale", "AutoFakeBold", "AutoFakeSlant", "LetterSpace") for k, _v in fopts):
						if not o["mainfont"]:
							o["mainfont"] = fm.group(2).strip()
						s = s[:fm.start()] + s[fm.end():]
					else:
						o["script_fontfamily"] = False
						notes.append("A \\newfontfamily line for the %s font uses special options, so it is kept as it is." % script)
		else:
			notes.append("The polyglossia language setup could not be converted and is kept as extra preamble.")

	# ---- fonts
	main_font_scale = ""
	for cmd, key in (("setmainfont", "mainfont"), ("setsansfont", "sansfont"), ("setmonofont", "monofont")):
		mm = _stmt_re(cmd).search(s)
		if not mm:
			continue
		content, j = _balanced_at(s, mm.end() - 1)
		kv = _parse_kv(mm.group(1) or "")
		name = (content or "").strip()
		if key == "mainfont":
			allowed = ("Script", "Scale", "AutoFakeBold", "AutoFakeSlant", "LetterSpace", "BoldFont", "ItalicFont", "BoldItalicFont")
			good = bool(name) and not name.startswith("\\") and all(k in allowed and v is not None for k, v in kv)
		else:
			good = bool(name) and not name.startswith("\\") and not kv and not main_font_scale
		if not good:
			notes.append("\\%s has options the settings dialog cannot show, so it is kept as it is." % cmd)
			continue
		if key == "mainfont":
			o["mainfont"] = name
			for k, v in kv:
				if k == "Script":
					lang = _lang_for_script(v)
					if lang and o["language"] == "English":
						o["language"] = lang
				elif k == "Scale":
					o["font_scale"] = v
					main_font_scale = v
				elif k == "AutoFakeBold":
					o["fake_bold"] = v
				elif k == "AutoFakeSlant":
					o["fake_italic"] = v
				elif k == "LetterSpace":
					o["letterspace"] = v
				elif k == "BoldFont":
					o["bold_font"] = v
				elif k == "ItalicFont":
					o["italic_font"] = v
				elif k == "BoldItalicFont":
					o["bolditalic_font"] = v
		else:
			o[key] = name
		s = s[:mm.start()] + s[j:]
		rec.append("%s: %s" % ({"mainfont": "Main font", "sansfont": "Sans-serif font", "monofont": "Monospace font"}[key], name))

	# ---- title, author, date
	for cmd in ("title", "author", "date"):
		t = _take(s, cmd)
		if t:
			content, _opt, s = t
			o[cmd] = content.strip() if cmd != "date" else content.strip()
			rec.append("%s: %s" % (cmd.capitalize(), content.strip() or "empty"))

	# ---- line spacing, paragraph settings
	t = _take(s, "setstretch")
	if t:
		o["spacing"], s = t[0].strip(), t[2]
		rec.append("Line spacing %s" % o["spacing"])
	for word, val in (("onehalfspacing", "1.5"), ("doublespacing", "2"), ("singlespacing", "1")):
		if re.search(r"\\" + word + r"(?![A-Za-z])", s):
			o["spacing"] = val
			s = re.sub(r"\\" + word + r"(?![A-Za-z])", "", s)
			rec.append("Line spacing %s" % val)
	for dim, key in (("parindent", "parindent"), ("parskip", "parskip"), ("columnsep", "columnsep")):
		mm = re.search(r"\\setlength\s*\{\\" + dim + r"\}\s*\{([^{}]*)\}", s)
		if mm:
			o[key] = mm.group(1).strip()
			s = s[:mm.start()] + s[mm.end():]
			rec.append("%s %s" % (dim, o[key]))

	# ---- simple packages
	stmts = list(re.finditer(r"\\usepackage\s*(\[[^\]]*\])?\s*\{([^{}]*)\}", s))
	groups = {"amsmath": {"amsmath", "amssymb"}, "graphicx": {"graphicx"}, "hyperref": {"hyperref"}}
	for flag, names in groups.items():
		involved = [mm for mm in stmts if set(n.strip() for n in mm.group(2).split(",")) & names]
		if not involved:
			continue
		if all(not mm.group(1) and set(n.strip() for n in mm.group(2).split(",")) <= names for mm in involved):
			o[flag] = True
			rec.append("Package %s" % "/".join(sorted(set(n.strip() for mm in involved for n in mm.group(2).split(",")))))
			for mm in sorted(involved, key=lambda x: -x.start()):
				s = s[:mm.start()] + s[mm.end():]
			stmts = list(re.finditer(r"\\usepackage\s*(\[[^\]]*\])?\s*\{([^{}]*)\}", s))

	# ---- extra preamble: everything that was not recognised
	lines = [ln.rstrip() for ln in s.split("\n")]
	lines = [ln for ln in lines if ln.strip()]
	if any(re.search(r"\\includeonly", ln) for ln in lines):
		lines = [ln for ln in lines if "\\includeonly" not in ln]
		notes.append("An \\includeonly line was removed because the parts are renamed during a build.")
	o["extra_preamble"] = "\n".join(lines)
	if lines:
		rec_kept = len(lines)
		res.kept = lines
		notes.append("Comments in the preamble were not imported. %d other preamble line(s) were kept as extra preamble." % rec_kept)

	# engine hints
	if res.engine == "auto":
		blob = o["extra_preamble"] + raw[:2000]
		if re.search(r"luacode|\\directlua|luatex|lualatex", blob, re.I):
			res.engine = "lualatex"
			rec.append("Engine lualatex (the preamble uses Lua)")
		elif re.search(r"fontspec|polyglossia|unicode-math", blob):
			res.engine = "xelatex"
			rec.append("Engine xelatex (the preamble uses fontspec or polyglossia)")

	# ---- body: parts and template
	files, index = [], {}
	tmpl_lines = []
	for ln in body.split("\n"):
		c = _comment_index(ln)
		code, tail = (ln[:c], ln[c:]) if c >= 0 else (ln, "")

		def sub(mm, files=files, index=index):
			kind, name = mm.group(1), mm.group(2).strip().strip('"')
			if any(ch in name for ch in "\\#~$"):
				notes.append("%s{%s} uses a macro and is left as it is." % ("\\" + kind, name))
				return mm.group(0)
			cand = os.path.normpath(os.path.join(res.root, name))
			full = cand if os.path.isfile(cand) else (cand + ".tex" if os.path.isfile(cand + ".tex") else None)
			if full is None:
				full = cand if os.path.splitext(cand)[1] else cand + ".tex"
				if full not in res.missing:
					res.missing.append(full)
			if full not in index:
				index[full] = len(files)
				files.append(full)
			return "{{%s:%d}}" % (kind.upper(), index[full])

		tmpl_lines.append(PART_RE.sub(sub, code) + tail)
	res.files = files
	res.body_template = "\n".join(tmpl_lines).strip("\n") + "\n"
	if not files:
		notes.append("No \\input, \\include or \\subfile commands were found in the body, so the project has no separate files. The whole body is kept in the layout template.")
	rec.append("Body of the main file kept as the project layout (%d part file(s))" % len(files))
	return res
