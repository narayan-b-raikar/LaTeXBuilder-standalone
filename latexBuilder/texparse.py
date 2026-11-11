# -*- coding: utf-8 -*-
"""Light-weight LaTeX source analysis. No NVDA / wx imports, so it is testable anywhere."""

import re

LEVELS = {
	"part": -1,
	"chapter": 0,
	"section": 1,
	"subsection": 2,
	"subsubsection": 3,
	"paragraph": 4,
	"subparagraph": 5,
}

HEADING_RE = re.compile(
	r"^\s*\\(part|chapter|section|subsection|subsubsection|paragraph|subparagraph)(\*?)\s*(?:\[[^\]]*\])?\s*\{(.*)$"
)
BEGIN_RE = re.compile(r"\\begin\{([A-Za-z*]+)\}")
END_RE = re.compile(r"\\end\{([A-Za-z*]+)\}")

NAV_KINDS = {
	"footnote": re.compile(r"\\(?:footnote|endnote)\s*(?:\[[^\]]*\])?\{"),
	"environment": re.compile(r"\\begin\{(?!document\b)[A-Za-z*]+\}"),
	"math": re.compile(r"(?:\\begin\{(?:equation|align|gather|multline|eqnarray)\*?\})|(?:^\s*\\\[)|(?:^\s*\$\$)"),
	"comment": re.compile(r"^\s*%"),
}


class Heading(object):
	__slots__ = ("line", "level", "kind", "title", "starred", "number")

	def __init__(self, line, level, kind, title, starred):
		self.line = line
		self.level = level
		self.kind = kind
		self.title = title
		self.starred = starred
		self.number = ""

	def label(self):
		"""Spoken/visible label, e.g. '1.2 Introduction'."""
		return ("%s %s" % (self.number, self.title)).strip()

	def kind_name(self):
		return self.kind + ("*" if self.starred else "")


def strip_comment(line):
	"""Remove an unescaped % comment from a line."""
	out = []
	i = 0
	while i < len(line):
		c = line[i]
		if c == "\\":
			out.append(line[i:i + 2])
			i += 2
			continue
		if c == "%":
			break
		out.append(c)
		i += 1
	return "".join(out)


def _balanced(rest):
	"""Return text up to the brace that closes an already opened group."""
	depth = 1
	buf = []
	i = 0
	while i < len(rest):
		c = rest[i]
		if c == "\\" and i + 1 < len(rest):
			buf.append(rest[i:i + 2])
			i += 2
			continue
		if c == "{":
			depth += 1
		elif c == "}":
			depth -= 1
			if depth == 0:
				return "".join(buf)
		buf.append(c)
		i += 1
	return "".join(buf)


def find_headings(lines):
	heads = []
	for i, raw in enumerate(lines):
		if raw.lstrip().startswith("%"):
			continue
		m = HEADING_RE.match(strip_comment(raw))
		if not m:
			continue
		kind, star, rest = m.group(1), m.group(2), m.group(3)
		heads.append(Heading(i, LEVELS[kind], kind, _balanced(rest).strip(), bool(star)))
	_number(heads)
	return heads


def _number(heads):
	has_chapter = any(h.kind == "chapter" for h in heads)
	counters = [0] * 6
	for h in heads:
		if h.level < 0 or h.starred:
			continue
		lv = h.level
		counters[lv] += 1
		for j in range(lv + 1, 6):
			counters[j] = 0
		first = 0 if has_chapter else 1
		if lv >= 4:
			continue  # paragraphs are not numbered by default
		parts = [str(counters[j]) for j in range(first, lv + 1)]
		h.number = ".".join(parts)


def heading_at(heads, line):
	"""Last heading that starts on or before ``line``."""
	cur = None
	for h in heads:
		if h.line <= line:
			cur = h
		else:
			break
	return cur


def heading_path(heads, line):
	"""Chain of headings (outermost first) containing ``line``."""
	cur = heading_at(heads, line)
	if cur is None:
		return []
	path = [cur]
	lvl = cur.level
	for h in reversed(heads):
		if h.line >= cur.line:
			continue
		if h.level < lvl:
			path.append(h)
			lvl = h.level
			if lvl <= -1:
				break
	path.reverse()
	return path


def next_heading(heads, line, backwards=False, same_or_higher_than=None):
	"""Find next/previous heading. ``same_or_higher_than`` is a level number."""
	cands = heads
	if same_or_higher_than is not None:
		cands = [h for h in heads if h.level <= same_or_higher_than]
	if backwards:
		for h in reversed(cands):
			if h.line < line:
				return h
		return None
	for h in cands:
		if h.line > line:
			return h
	return None


def open_environments(lines, line):
	"""Stack of environments (innermost last) open at the start of ``line`` inclusive."""
	stack = []
	for i in range(0, min(line, len(lines) - 1) + 1):
		text = strip_comment(lines[i])
		events = [(m.start(), "b", m.group(1)) for m in BEGIN_RE.finditer(text)]
		events += [(m.start(), "e", m.group(1)) for m in END_RE.finditer(text)]
		events.sort()
		for _pos, typ, name in events:
			if typ == "b":
				stack.append(name)
			else:
				for k in range(len(stack) - 1, -1, -1):
					if stack[k] == name:
						del stack[k:]
						break
	return [n for n in stack if n != "document"]


def find_kind_lines(lines, kind):
	rx = NAV_KINDS[kind]
	return [i for i, t in enumerate(lines) if rx.search(t if kind == "comment" else strip_comment(t))]


def next_in(sorted_lines, line, backwards=False):
	if backwards:
		for n in reversed(sorted_lines):
			if n < line:
				return n
		return None
	for n in sorted_lines:
		if n > line:
			return n
	return None


def poem_from_lines(text):
	"""Convert plain lines to the body of a LaTeX verse environment."""
	rows = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
	while rows and not rows[-1].strip():
		rows.pop()
	while rows and not rows[0].strip():
		rows.pop(0)
	out = []
	for i, r in enumerate(rows):
		r = r.rstrip()
		nxt = rows[i + 1].strip() if i + 1 < len(rows) else ""
		if r.strip() and nxt:
			out.append(r + " \\\\")
		else:
			out.append(r)
	return "\n".join(out)


# ---------------------------------------------------------------- build log parsing

FILE_LINE_RE = re.compile(r"^(?P<file>.+?\.(?:tex|sty|cls|ltx|def|cfg|bbl)):(?P<line>\d+):\s*(?P<msg>.*)$", re.I)
BANG_RE = re.compile(r"^!\s*(?P<msg>.*)$")
LNUM_RE = re.compile(r"^l\.(?P<line>\d+)\s*(?P<ctx>.*)$")
WARN_RE = re.compile(r"^(?:LaTeX|Package \S+|Class \S+) Warning:\s*(?P<msg>.*)$")


class LogIssue(object):
	def __init__(self, severity, message, file=None, line=None):
		self.severity = severity
		self.message = message
		self.file = file
		self.line = line

	def describe(self):
		where = ""
		if self.file:
			import os
			where = os.path.basename(self.file)
			if self.line:
				where += " line %d" % self.line
			where = " (" + where + ")"
		return "%s: %s%s" % (self.severity.capitalize(), self.message, where)


def parse_log(text):
	issues = []
	lines = text.splitlines()
	i = 0
	seen = set()
	while i < len(lines):
		ln = lines[i]
		m = FILE_LINE_RE.match(ln)
		if m:
			key = (m.group("file"), m.group("line"), m.group("msg"))
			if key not in seen:
				seen.add(key)
				issues.append(LogIssue("error", m.group("msg").strip(), m.group("file"), int(m.group("line"))))
			i += 1
			continue
		m = BANG_RE.match(ln)
		if m and not ln.startswith("!!"):
			msg = m.group("msg").strip()
			line_no = None
			for j in range(i + 1, min(i + 8, len(lines))):
				ml = LNUM_RE.match(lines[j])
				if ml:
					line_no = int(ml.group("line"))
					break
			key = (None, line_no, msg)
			if key not in seen:
				seen.add(key)
				issues.append(LogIssue("error", msg, None, line_no))
			i += 1
			continue
		m = WARN_RE.match(ln)
		if m:
			msg = m.group("msg").strip()
			ml = re.search(r"on input line (\d+)", msg)
			issues.append(LogIssue("warning", re.sub(r"\s+", " ", msg), None, int(ml.group(1)) if ml else None))
		i += 1
	return issues


# ---------------------------------------------------------------- reading helpers

_HEAD_CMD = re.compile(r"\\(?:part|chapter|section|subsection|subsubsection|paragraph|subparagraph)\*?(?:\[[^\]]*\])?\s*\{")


def _notes_inline(t):
	out, i = [], 0
	rx = re.compile(r"\\(?:footnote|endnote)\s*\{")
	while True:
		m = rx.search(t, i)
		if not m:
			out.append(t[i:])
			break
		out.append(t[i:m.start()])
		inner = _balanced(t[m.end():])
		out.append(" (note: %s) " % inner)
		i = m.end() + len(inner) + 1
	return "".join(out)


def plain_text(src):
	"""LaTeX source -> text that is pleasant to hear (commands removed)."""
	t = "\n".join(strip_comment(l) for l in src.split("\n"))
	t = _HEAD_CMD.sub("\nHeading: ", t)
	t = re.sub(r"\\(?:begin|end)\{[^}]*\}(?:\[[^\]]*\])?", " ", t)
	t = re.sub(r"\\item(?:\[([^\]]*)\])?", lambda m: "\nItem " + (m.group(1) + ": " if m.group(1) else ""), t)
	t = _notes_inline(t)
	t = t.replace("\\\\", "\n")
	t = re.sub(r"\\([%&#$_{}])", r"\1", t)
	t = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?", " ", t)
	t = t.replace("~", " ").replace("$", " ")
	t = t.replace("{", "").replace("}", "")
	t = re.sub(r"[ \t]+", " ", t)
	t = re.sub(r"(?:\n[ \t]*){2,}", "\n\n", t)
	return t.strip()


def section_range(lines, line):
	"""(start, end) line indexes of the text under the heading at/before ``line`` (end exclusive)."""
	heads = find_headings(lines)
	cur = heading_at(heads, line)
	start = cur.line if cur else 0
	end = len(lines)
	for h in heads:
		if h.line > start:
			end = h.line
			break
	return start, end


def paragraph_range(lines, line):
	"""(start, end) of the blank-line separated paragraph containing ``line``."""
	n = len(lines)
	line = max(0, min(line, n - 1))
	s = line
	while s > 0 and lines[s - 1].strip():
		s -= 1
	e = line + 1
	while e < n and lines[e].strip():
		e += 1
	return s, e


def statistics(text):
	lines = text.split("\n")
	heads = find_headings(lines)
	body = plain_text(text)
	counts = {}
	for h in heads:
		counts[h.kind] = counts.get(h.kind, 0) + 1
	return {
		"lines": len(lines),
		"words": len(body.split()),
		"characters": len(text),
		"headings": counts,
		"notes": len(find_kind_lines(lines, "footnote")),
		"environments": len(find_kind_lines(lines, "environment")),
	}
