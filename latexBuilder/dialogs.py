# -*- coding: utf-8 -*-
"""wx dialogs. Labels always come directly before their control so NVDA announces them."""

import os
import re
import threading

import ui
import wx

from . import builder
from . import logger
from . import packages_catalog
from . import project as projmod
from . import snippets


def focus_dialog(dlg, widget=None, speak=None):
	"""Make sure a dialog opened from a callback really gets keyboard focus and is announced."""
	def go():
		try:
			dlg.Raise()
			try:
				import winUser
				winUser.setForegroundWindow(dlg.GetHandle())
			except Exception:
				pass
			if widget is not None:
				widget.SetFocus()
			if speak:
				ui.message(speak)
		except Exception:
			logger.exc("focus_dialog failed")
	wx.CallLater(250, go)


class FormDialog(wx.Dialog):
	"""Generic label + control form.

	fields: dicts with key, type (text|multiline|choice|combo|check), label, default, choices and an optional button (label, callback) placed right after the control.
	"""

	def __init__(self, parent, title, fields, intro=None, validator=None, extra_buttons=()):
		super().__init__(parent, title=title)
		used = set()

		def uniq(label):
			"""Keep each Alt+letter mnemonic only once in a dialog."""
			m = re.search(r"&(\w)", label)
			if not m:
				return label
			ch = m.group(1).lower()
			if ch in used:
				return label.replace("&" + m.group(1), m.group(1), 1)
			used.add(ch)
			return label

		fields = [dict(f, label=uniq(f["label"]), **({"button": (uniq(f["button"][0]), f["button"][1])} if f.get("button") else {})) for f in fields]
		self.fields = fields
		self.ctrls = {}
		self.validator = validator
		main = wx.BoxSizer(wx.VERTICAL)
		if intro:
			main.Add(wx.StaticText(self, label=intro), 0, wx.ALL, 8)
		first = None
		for f in fields:
			typ = f.get("type", "text")
			if typ == "check":
				c = wx.CheckBox(self, label=f["label"])
				c.SetValue(bool(f.get("default")))
				main.Add(c, 0, wx.ALL, 6)
			else:
				main.Add(wx.StaticText(self, label=f["label"]), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
				if typ == "choice":
					c = wx.Choice(self, choices=list(f["choices"]))
					c.SetSelection(int(f.get("default", 0)))
				elif typ == "combo":
					c = wx.ComboBox(self, value=str(f.get("default", "")), choices=list(f["choices"]), style=wx.CB_DROPDOWN, size=(480, -1))
				elif typ == "multiline":
					c = wx.TextCtrl(self, value=f.get("default", ""), style=wx.TE_MULTILINE, size=(480, 130))
				else:
					c = wx.TextCtrl(self, value=str(f.get("default", "")), size=(480, -1))
				main.Add(c, 0, wx.EXPAND | wx.ALL, 6)
				if f.get("button"):
					label, cb = f["button"]
					b = wx.Button(self, label=label)
					b.Bind(wx.EVT_BUTTON, lambda evt, cb=cb: cb(self))
					main.Add(b, 0, wx.LEFT | wx.BOTTOM, 6)
			self.ctrls[f["key"]] = c
			if first is None:
				first = c
		if extra_buttons:
			row = wx.BoxSizer(wx.HORIZONTAL)
			for label, cb in extra_buttons:
				b = wx.Button(self, label=label)
				b.Bind(wx.EVT_BUTTON, lambda evt, cb=cb: cb(self))
				row.Add(b, 0, wx.ALL, 4)
			main.Add(row, 0, wx.ALL, 4)
		btns = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
		main.Add(btns, 0, wx.EXPAND | wx.ALL, 8)
		self.SetSizerAndFit(main)
		self.FindWindowById(wx.ID_OK).SetDefault()
		self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
		self.CentreOnScreen()
		if first is not None:
			first.SetFocus()

	def _on_ok(self, evt):
		if self.validator:
			err = self.validator(self.values())
			if err:
				wx.MessageBox(err, "Please check", wx.OK | wx.ICON_WARNING, self)
				return
		evt.Skip()

	def values(self):
		out = {}
		for f in self.fields:
			c = self.ctrls[f["key"]]
			typ = f.get("type", "text")
			if typ == "check":
				out[f["key"]] = c.GetValue()
			elif typ == "choice":
				out[f["key"]] = c.GetSelection()
			else:
				out[f["key"]] = c.GetValue()
		return out


def ask(parent, title, fields, intro=None, validator=None, extra_buttons=()):
	logger.log("dialog: %s" % title)
	dlg = FormDialog(parent, title, fields, intro, validator, extra_buttons)
	try:
		if dlg.ShowModal() == wx.ID_OK:
			return dlg.values()
		return None
	finally:
		dlg.Destroy()


class FilterListDialog(wx.Dialog):
	"""Type to filter, arrow down to move into the list, Enter to choose."""

	def __init__(self, parent, title, items, prompt="&Filter (type to narrow the list):", initial=0, extra_buttons=(), show_filter=True):
		super().__init__(parent, title=title)
		self.all_items = items  # list of (text, data)
		self.shown = list(items)
		self.result = None
		main = wx.BoxSizer(wx.VERTICAL)
		self.filter = None
		if show_filter:
			main.Add(wx.StaticText(self, label=prompt), 0, wx.ALL, 6)
			self.filter = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
			main.Add(self.filter, 0, wx.EXPAND | wx.ALL, 6)
			self.filter.Bind(wx.EVT_TEXT, self._on_filter)
			self.filter.Bind(wx.EVT_KEY_DOWN, self._on_filter_key)
			self.filter.Bind(wx.EVT_TEXT_ENTER, self._on_filter_enter)
		main.Add(wx.StaticText(self, label="&Items:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
		self.list = wx.ListBox(self, choices=[it[0] for it in self.shown], size=(560, 320))
		main.Add(self.list, 1, wx.EXPAND | wx.ALL, 6)
		if extra_buttons:
			row = wx.BoxSizer(wx.HORIZONTAL)
			for label, cb in extra_buttons:
				b = wx.Button(self, label=label)
				b.Bind(wx.EVT_BUTTON, lambda evt, cb=cb: cb(self))
				row.Add(b, 0, wx.ALL, 4)
			main.Add(row, 0, wx.ALL, 4)
		main.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
		self.SetSizerAndFit(main)
		self.list.Bind(wx.EVT_LISTBOX_DCLICK, lambda e: self._accept())
		self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
		if self.shown:
			self.list.SetSelection(min(max(initial, 0), len(self.shown) - 1))
		self.FindWindowById(wx.ID_OK).SetDefault()
		self.CentreOnScreen()
		if self.filter is not None:
			self.filter.SetFocus()
		else:
			self.list.SetFocus()

	def _on_filter(self, evt):
		words = self.filter.GetValue().lower().split()
		self.shown = [it for it in self.all_items if all(w in (it[0] + " " + (it[2] if len(it) > 2 else "")).lower() for w in words)]
		self.list.Set([it[0] for it in self.shown])
		if self.shown:
			self.list.SetSelection(0)
		evt.Skip()

	def _on_filter_key(self, evt):
		if evt.GetKeyCode() == wx.WXK_DOWN and self.shown:
			self.list.SetFocus()
			if self.list.GetSelection() == wx.NOT_FOUND:
				self.list.SetSelection(0)
			return
		evt.Skip()

	def _on_filter_enter(self, evt):
		self._accept()

	def _accept(self):
		self._on_ok(None)

	def _on_ok(self, evt):
		sel = self.list.GetSelection()
		if sel == wx.NOT_FOUND and self.shown:
			sel = 0
		if sel == wx.NOT_FOUND:
			wx.Bell()
			return
		self.result = self.shown[sel][1]
		self.EndModal(wx.ID_OK)

	def selected_data(self):
		sel = self.list.GetSelection()
		if sel == wx.NOT_FOUND:
			return None
		return self.shown[sel][1]


def choose(parent, title, items, **kw):
	"""Show FilterListDialog and return chosen data or None."""
	logger.log("dialog: %s" % title)
	dlg = FilterListDialog(parent, title, items, **kw)
	try:
		if dlg.ShowModal() == wx.ID_OK:
			return dlg.result
		return None
	finally:
		dlg.Destroy()


def show_text(parent, title, text, caret_end=False):
	logger.log("dialog: %s" % title)
	dlg = wx.Dialog(parent, title=title)
	main = wx.BoxSizer(wx.VERTICAL)
	main.Add(wx.StaticText(dlg, label="&Text (read-only):"), 0, wx.ALL, 6)
	tc = wx.TextCtrl(dlg, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, size=(720, 420))
	main.Add(tc, 1, wx.EXPAND | wx.ALL, 6)
	main.Add(dlg.CreateStdDialogButtonSizer(wx.CLOSE), 0, wx.EXPAND | wx.ALL, 8)
	dlg.SetEscapeId(wx.ID_CLOSE)
	dlg.Bind(wx.EVT_BUTTON, lambda e: dlg.EndModal(wx.ID_CLOSE), id=wx.ID_CLOSE)
	dlg.SetSizerAndFit(main)
	dlg.CentreOnScreen()
	tc.SetFocus()
	tc.SetInsertionPoint(tc.GetLastPosition() if caret_end else 0)
	try:
		dlg.ShowModal()
	finally:
		dlg.Destroy()


# ------------------------------------------------------------------ ready-made lists for typed values

MARGIN_CHOICES = ["", "1.5cm", "2cm", "2.5cm", "3cm", "1in", "1.25in", "1.5in"]
SMALL_DIM_CHOICES = ["", "0pt", "0.5cm", "1cm", "1.5cm", "2cm"]
PARINDENT_CHOICES = ["", "0pt", "1em", "1.5em", "2em"]
PARSKIP_CHOICES = ["", "0pt", "0.5ex", "1ex", "1em"]
SCALE_CHOICES = ["1", "0.9", "1.1", "1.2", "1.3"]
FAKEBOLD_CHOICES = ["", "1", "2", "3"]
FAKEITALIC_CHOICES = ["", "0.1", "0.2", "0.3"]
LETTERSPACE_CHOICES = ["", "1", "2", "5"]
FIRSTPAGE_CHOICES = ["", "1", "2", "3", "5", "10"]
NOTESEP_CHOICES = ["", "0.5ex", "1ex", "2ex"]
PAPERSIZE_CHOICES = ["", "15cm", "21cm", "29.7cm"]
SPACING_CHOICES = ["1", "1.15", "1.25", "1.5", "2"]
DATE_MODES = ["Today's date (changes every day)", "No date", "A date I type below"]
HF_CHOICES = ["(nothing)", "Page number", "Page x of y", "Chapter or section name", "Document title", "Author", "Date"]


def date_fields(current):
	if current == "\\today":
		mode, text = 0, ""
	elif not current:
		mode, text = 1, ""
	else:
		mode, text = 2, current
	return [
		{"key": "date_mode", "type": "choice", "label": "&Date:", "choices": DATE_MODES, "default": mode},
		{"key": "date_text", "label": "Date to print (used only for: A date I type):", "default": text},
	]


def date_from_values(v):
	return ["\\today", "", v["date_text"].strip()][v["date_mode"]]


def browse_file(key, wildcard="All files (*.*)|*.*"):
	def run(dlg):
		d = wx.FileDialog(dlg, "Choose a file", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
		try:
			if d.ShowModal() == wx.ID_OK:
				dlg.ctrls[key].SetValue(d.GetPath())
				ui.message(os.path.basename(d.GetPath()))
		finally:
			d.Destroy()
	return run


def browse_dir(key):
	def run(dlg):
		d = wx.DirDialog(dlg, "Choose a folder", defaultPath=dlg.ctrls[key].GetValue(), style=wx.DD_DEFAULT_STYLE)
		try:
			if d.ShowModal() == wx.ID_OK:
				dlg.ctrls[key].SetValue(d.GetPath())
				ui.message(d.GetPath())
		finally:
			d.Destroy()
	return run


# ------------------------------------------------------------------ fonts

RECOMMENDED_FONTS = {
	"Kannada": ["Nirmala UI", "Tunga", "Noto Serif Kannada", "Noto Sans Kannada", "Lohit Kannada", "Kedage", "Sampige", "Akshar Unicode", "Baloo Tamma 2"],
	"Devanagari": ["Nirmala UI", "Mangal", "Kokila", "Aparajita", "Utsaah", "Sanskrit Text", "Noto Serif Devanagari", "Noto Sans Devanagari",
		"Annapurna SIL", "Lohit Devanagari", "Tiro Devanagari Hindi", "Tiro Devanagari Sanskrit", "Tiro Devanagari Marathi",
		"Sahitya", "Siddhanta", "Chandas", "Shobhika", "Sarala", "Eczar", "Kalam"],
	"Tamil": ["Nirmala UI", "Latha", "Vijaya", "Noto Serif Tamil", "Noto Sans Tamil", "Lohit Tamil"],
	"Telugu": ["Nirmala UI", "Gautami", "Vani", "Noto Serif Telugu", "Noto Sans Telugu", "Lohit Telugu"],
	"Malayalam": ["Nirmala UI", "Kartika", "Noto Serif Malayalam", "Noto Sans Malayalam", "Lohit Malayalam", "Rachana", "Meera", "Manjari"],
	"Bengali": ["Nirmala UI", "Vrinda", "Shonar Bangla", "Noto Serif Bengali", "Noto Sans Bengali", "Lohit Bengali"],
	"Gujarati": ["Nirmala UI", "Shruti", "Noto Serif Gujarati", "Noto Sans Gujarati", "Lohit Gujarati"],
	"Gurmukhi": ["Nirmala UI", "Raavi", "Noto Serif Gurmukhi", "Noto Sans Gurmukhi", "Lohit Gurmukhi"],
	"Oriya": ["Nirmala UI", "Kalinga", "Noto Sans Oriya", "Lohit Odia"],
	"Arabic": ["Urdu Typesetting", "Noto Nastaliq Urdu", "Jameel Noori Nastaleeq", "Arial", "Times New Roman", "Segoe UI"],
}


def installed_fonts():
	try:
		names = wx.FontEnumerator().GetFacenames()
	except Exception:
		names = []
	return sorted({n for n in names if n and not n.startswith("@")}, key=lambda x: x.lower())


def choose_font(parent, script, current=""):
	"""Let the user pick an installed font. Returns the name, "" for 'language default', or None if cancelled."""
	fonts = installed_fonts()
	lower = dict((f.lower(), f) for f in fonts)
	rec = []
	for name in RECOMMENDED_FONTS.get(script or "", []):
		if name.lower() in lower:
			rec.append(lower[name.lower()])
	items = [("Use the default font of the language (clear this box)", "")]
	for n in rec:
		items.append(("%s (suggested for %s)" % (n, script), n))
	items += [(n, n) for n in fonts if n not in rec]
	initial = 0
	for i, (_t, d) in enumerate(items):
		if current and d.lower() == current.lower():
			initial = i
			break
	return choose(parent, "Choose a font (%d installed fonts found)" % len(fonts), items, prompt="&Type part of the font name:", initial=initial)


# ------------------------------------------------------------------ settings editor (categories)

def _idx(lst, val):
	return lst.index(val) if val in lst else 0


def _script_of(lang_name):
	return projmod.LANG_BY_NAME.get(lang_name, projmod.LANG_INFO[0])[1]


def _cat_title(parent, w):
	fields = [
		{"key": "documentclass", "type": "choice", "label": "&Document class (article, report or book):", "choices": projmod.CLASSES, "default": _idx(projmod.CLASSES, w["documentclass"])},
		{"key": "title", "label": "Document &title:", "default": w["title"]},
		{"key": "author", "label": "&Author:", "default": w["author"]},
		date_fields(w["date"])[0],
		date_fields(w["date"])[1],
		{"key": "maketitle", "type": "check", "label": "Print the title &block at the start", "default": w["maketitle"]},
		{"key": "toc", "type": "check", "label": "Table of &contents after the title", "default": w["toc"]},
	]
	v = ask(parent, "Title, author and document class", fields)
	if v is None:
		return
	w["documentclass"] = projmod.CLASSES[v["documentclass"]]
	for k in ("title", "author"):
		w[k] = v[k].strip()
	w["date"] = date_from_values(v)
	w["maketitle"], w["toc"] = bool(v["maketitle"]), bool(v["toc"])


def _cat_lang(parent, w):
	def pick(dlg):
		lang = projmod.LANGUAGES[dlg.ctrls["language"].GetSelection()]
		cur = dlg.ctrls["mainfont"].GetValue()
		r = choose_font(dlg, _script_of(lang), cur)
		if r is not None:
			dlg.ctrls["mainfont"].SetValue(r)
			ui.message("Main font: %s" % (r or "language default"))

	fields = [
		{"key": "language", "type": "choice", "label": "Main &language of the text:", "choices": projmod.LANGUAGES, "default": _idx(projmod.LANGUAGES, w["language"])},
		{"key": "mainfont", "label": "Main &font (empty = language default):", "default": w["mainfont"], "button": ("Choose from &installed fonts...", pick)},
		{"key": "fontsize", "type": "choice", "label": "Font &size in points:", "choices": projmod.FONT_SIZES, "default": _idx(projmod.FONT_SIZES, w["fontsize"])},
		{"key": "use_polyglossia", "type": "check", "label": "Use &polyglossia (hyphenation and names like Chapter)", "default": w["use_polyglossia"]},
		{"key": "native_digits", "type": "check", "label": "Print &native digits (needs polyglossia)", "default": w["native_digits"]},
	]
	intro = "Languages other than English use XeLaTeX."
	v = ask(parent, "Language and main font", fields, intro=intro)
	if v is None:
		return
	w["language"] = projmod.LANGUAGES[v["language"]]
	w["mainfont"] = v["mainfont"].strip()
	w["fontsize"] = projmod.FONT_SIZES[v["fontsize"]]
	w["use_polyglossia"] = bool(v["use_polyglossia"])
	w["native_digits"] = bool(v["native_digits"])


def _cat_fontfine(parent, w):
	fields = [
		{"key": "font_scale", "type": "combo", "choices": SCALE_CHOICES, "label": "Font &scale (1 = normal):", "default": w["font_scale"]},
		{"key": "fake_bold", "type": "combo", "choices": FAKEBOLD_CHOICES, "label": "&Fake bold, for fonts without bold:", "default": w["fake_bold"]},
		{"key": "fake_italic", "type": "combo", "choices": FAKEITALIC_CHOICES, "label": "Fake &italic, for fonts without italic:", "default": w["fake_italic"]},
		{"key": "letterspace", "type": "combo", "choices": LETTERSPACE_CHOICES, "label": "&Letter spacing:", "default": w["letterspace"]},
		{"key": "bold_font", "label": "Real bold font name or file (optional):", "default": w["bold_font"]},
		{"key": "italic_font", "label": "Real italic font name or file (optional):", "default": w["italic_font"]},
		{"key": "bolditalic_font", "label": "Real bold italic font name or file (optional):", "default": w["bolditalic_font"]},
	]
	v = ask(parent, "Font fine tuning", fields, intro="These apply to the main font.")
	if v is None:
		return
	for k in ("font_scale", "fake_bold", "fake_italic", "letterspace", "bold_font", "italic_font", "bolditalic_font"):
		w[k] = v[k].strip()
	if not w["font_scale"]:
		w["font_scale"] = "1"


def _cat_fontother(parent, w):
	script = _script_of(w["language"])

	def pick(field):
		def run(dlg):
			r = choose_font(dlg, script, dlg.ctrls[field].GetValue())
			if r is not None:
				dlg.ctrls[field].SetValue(r)
				ui.message("%s" % (r or "no font"))
		return run

	fields = [
		{"key": "sansfont", "label": "&Sans-serif font (optional):", "default": w["sansfont"], "button": ("Choose &sans-serif font...", pick("sansfont"))},
		{"key": "monofont", "label": "&Monospace font (optional):", "default": w["monofont"], "button": ("Choose &monospace font...", pick("monofont"))},
	]
	v = ask(parent, "Sans-serif and monospace fonts", fields)
	if v is None:
		return
	w["sansfont"], w["monofont"] = v["sansfont"].strip(), v["monofont"].strip()


def _cat_pagesize(parent, w):
	fields = [
		{"key": "use_geometry", "type": "check", "label": "Use the &geometry package for page size and margins", "default": w["use_geometry"]},
		{"key": "paper", "type": "choice", "label": "&Paper size:", "choices": [projmod.PAPER_LABELS[p] for p in projmod.PAPERS], "default": _idx(projmod.PAPERS, w["paper"])},
		{"key": "paper_width", "type": "combo", "choices": PAPERSIZE_CHOICES, "label": "Custom paper &width (only for custom size, for example 15cm):", "default": w["paper_width"]},
		{"key": "paper_height", "type": "combo", "choices": PAPERSIZE_CHOICES, "label": "Custom paper &height (for example 21cm):", "default": w["paper_height"]},
		{"key": "orientation", "type": "choice", "label": "&Orientation:", "choices": ["Portrait (upright)", "Landscape (sideways)"], "default": _idx(projmod.ORIENTATIONS, w["orientation"])},
		{"key": "twoside", "type": "check", "label": "&Two-sided printing", "default": w["twoside"]},
		{"key": "columns", "type": "choice", "label": "Number of text &columns:", "choices": ["1", "2"], "default": 1 if str(w["columns"]) == "2" else 0},
		{"key": "columnsep", "type": "combo", "choices": SMALL_DIM_CHOICES, "label": "Space between columns (two columns only, for example 1cm):", "default": w["columnsep"]},
		{"key": "columnrule", "type": "check", "label": "Draw a &line between the columns", "default": w["columnrule"]},
	]
	v = ask(parent, "Page size, orientation and columns", fields)
	if v is None:
		return
	w["use_geometry"] = bool(v["use_geometry"])
	w["paper"] = projmod.PAPERS[v["paper"]]
	w["paper_width"], w["paper_height"] = v["paper_width"].strip(), v["paper_height"].strip()
	w["orientation"] = projmod.ORIENTATIONS[v["orientation"]]
	w["twoside"] = bool(v["twoside"])
	w["columns"] = "2" if v["columns"] == 1 else "1"
	w["columnsep"] = v["columnsep"].strip()
	w["columnrule"] = bool(v["columnrule"])


def _cat_margins(parent, w):
	left, right = ("inner", "outer") if w["twoside"] else ("left", "right")
	fields = [
		{"key": "margin_all", "type": "combo", "choices": MARGIN_CHOICES, "label": "Margin on &all sides:", "default": w["margin_all"]},
		{"key": "margin_top", "type": "combo", "choices": MARGIN_CHOICES, "label": "&Top margin (empty = same as all sides):", "default": w["margin_top"]},
		{"key": "margin_bottom", "type": "combo", "choices": MARGIN_CHOICES, "label": "&Bottom margin:", "default": w["margin_bottom"]},
		{"key": "margin_left", "type": "combo", "choices": MARGIN_CHOICES, "label": "&Left margin (inner if two-sided):", "default": w["margin_left"]},
		{"key": "margin_right", "type": "combo", "choices": MARGIN_CHOICES, "label": "&Right margin (outer if two-sided):", "default": w["margin_right"]},
		{"key": "bindingoffset", "type": "combo", "choices": SMALL_DIM_CHOICES, "label": "Extra space for &binding:", "default": w["bindingoffset"]},
		{"key": "headsep", "type": "combo", "choices": SMALL_DIM_CHOICES, "label": "Space between the &header and the text (for example 1cm):", "default": w["headsep"]},
		{"key": "footskip", "type": "combo", "choices": SMALL_DIM_CHOICES, "label": "Distance from the text to the &footer (for example 1.2cm):", "default": w["footskip"]},
	]
	v = ask(parent, "Margins", fields, intro="Units: cm, mm, in or pt.")
	if v is None:
		return
	for k in ("margin_all", "margin_top", "margin_bottom", "margin_left", "margin_right", "bindingoffset", "headsep", "footskip"):
		w[k] = v[k].strip()


def _cat_layout(parent, w):
	fields = [
		{"key": "spacing", "type": "combo", "choices": SPACING_CHOICES, "label": "Line &spacing (1 = single, 1.5, 2 = double):", "default": str(w["spacing"])},
		{"key": "parindent", "type": "combo", "choices": PARINDENT_CHOICES, "label": "&Paragraph indent:", "default": w["parindent"]},
		{"key": "parskip", "type": "combo", "choices": PARSKIP_CHOICES, "label": "Space between pa&ragraphs:", "default": w["parskip"]},
		{"key": "pagenumbering", "type": "choice", "label": "Page &numbers style:", "choices": [projmod.PAGE_NUMBERING_LABELS[p] for p in projmod.PAGE_NUMBERINGS], "default": _idx(projmod.PAGE_NUMBERINGS, w["pagenumbering"])},
		{"key": "firstpage", "type": "combo", "choices": FIRSTPAGE_CHOICES, "label": "&First page number:", "default": w["firstpage"]},
	]
	v = ask(parent, "Line spacing, paragraphs and page numbers", fields)
	if v is None:
		return
	w["spacing"] = v["spacing"].strip() or "1"
	w["parindent"], w["parskip"], w["firstpage"] = v["parindent"].strip(), v["parskip"].strip(), v["firstpage"].strip()
	w["pagenumbering"] = projmod.PAGE_NUMBERINGS[v["pagenumbering"]]


def _choice_fields(key, label, pairs, current):
	keys = [k for k, _l in pairs]
	return {"key": key, "type": "choice", "label": label, "choices": [l for _k, l in pairs], "default": keys.index(current) if current in keys else 0}


def _pick_key(pairs, idx):
	return pairs[idx][0]


def _cat_titlepage(parent, w):
	def browse(dlg):
		d = wx.FileDialog(dlg, "Choose a logo picture", wildcard="Pictures (*.png;*.jpg;*.jpeg;*.pdf)|*.png;*.jpg;*.jpeg;*.pdf|All files (*.*)|*.*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
		try:
			if d.ShowModal() == wx.ID_OK:
				dlg.ctrls["tp_logo"].SetValue(d.GetPath())
				ui.message("Logo: %s" % os.path.basename(d.GetPath()))
		finally:
			d.Destroy()

	fields = [
		_choice_fields("tpl", "Title page &design:", projmod.TITLEPAGE_TEMPLATES, w["titlepage_template"]),
		{"key": "tp_subtitle", "label": "&Subtitle (optional):", "default": w["tp_subtitle"]},
		{"key": "tp_institution", "label": "&Institution, publisher or place (optional):", "default": w["tp_institution"]},
		{"key": "tp_department", "label": "&Department or series (optional):", "default": w["tp_department"]},
		{"key": "tp_extra", "type": "multiline", "label": "E&xtra lines, one per line (optional):", "default": w["tp_extra"]},
		{"key": "tp_logo", "label": "&Logo picture (optional):", "default": w["tp_logo"], "button": ("&Browse for logo...", browse)},
	]
	v = ask(parent, "Title page design", fields, intro="Title, author and date are in the group Title. Print the title block must be on.")
	if v is None:
		return
	w["titlepage_template"] = _pick_key(projmod.TITLEPAGE_TEMPLATES, v["tpl"])
	for k in ("tp_subtitle", "tp_institution", "tp_department", "tp_logo"):
		w[k] = v[k].strip()
	w["tp_extra"] = v["tp_extra"]


def _cat_footnotes(parent, w):
	def pick(dlg):
		r = choose_font(dlg, None, dlg.ctrls["fn_font"].GetValue())
		if r is not None:
			dlg.ctrls["fn_font"].SetValue(r)
			ui.message(r or "no special font for notes")

	fields = [
		_choice_fields("fn_numbering", "Footnote &numbering:", projmod.FN_NUMBERINGS, w["fn_numbering"]),
		_choice_fields("fn_style", "Footnote number &style:", projmod.NOTE_STYLES, w["fn_style"]),
		_choice_fields("fn_size", "Footnote text si&ze:", projmod.NOTE_SIZES, w["fn_size"]),
		{"key": "fn_font", "label": "Footnote &font (empty = text font):", "default": w["fn_font"], "button": ("Choose from &installed fonts...", pick)},
		_choice_fields("fn_layout", "Footnote &layout:", projmod.FN_LAYOUTS, w["fn_layout"]),
		{"key": "fn_rule", "type": "check", "label": "Draw a short &line above the footnotes", "default": w["fn_rule"]},
		{"key": "fn_bottom", "type": "check", "label": "Always put the footnotes at the &bottom of the page", "default": w["fn_bottom"]},
		{"key": "fn_sep", "type": "combo", "choices": NOTESEP_CHOICES, "label": "Space between &footnotes:", "default": w["fn_sep"]},
	]
	v = ask(parent, "Footnotes", fields)
	if v is None:
		return
	w["fn_numbering"] = _pick_key(projmod.FN_NUMBERINGS, v["fn_numbering"])
	w["fn_style"] = _pick_key(projmod.NOTE_STYLES, v["fn_style"])
	w["fn_size"] = _pick_key(projmod.NOTE_SIZES, v["fn_size"])
	w["fn_font"] = v["fn_font"].strip()
	w["fn_layout"] = _pick_key(projmod.FN_LAYOUTS, v["fn_layout"])
	w["fn_rule"], w["fn_bottom"] = bool(v["fn_rule"]), bool(v["fn_bottom"])
	w["fn_sep"] = v["fn_sep"].strip()


def _cat_endnotes(parent, w):
	fields = [
		{"key": "en_use", "type": "check", "label": "Use &endnotes for all notes", "default": w["en_use"]},
		{"key": "en_title", "label": "&Heading above the endnotes (empty = Notes):", "default": w["en_title"]},
		_choice_fields("en_size", "Endnote text si&ze:", projmod.NOTE_SIZES, w["en_size"]),
		_choice_fields("en_style", "Endnote number &style:", projmod.NOTE_STYLES, w["en_style"]),
		_choice_fields("en_numbering", "Endnote &numbering:", projmod.EN_NUMBERINGS, w["en_numbering"]),
		{"key": "en_auto", "type": "check", "label": "Print the endnotes &automatically at the end of the project", "default": w["en_auto"]},
	]
	v = ask(parent, "Endnotes", fields)
	if v is None:
		return
	w["en_use"] = bool(v["en_use"])
	w["en_title"] = v["en_title"].strip()
	w["en_size"] = _pick_key(projmod.NOTE_SIZES, v["en_size"])
	w["en_style"] = _pick_key(projmod.NOTE_STYLES, v["en_style"])
	w["en_numbering"] = _pick_key(projmod.EN_NUMBERINGS, v["en_numbering"])
	w["en_auto"] = bool(v["en_auto"])


def titlepage_form(parent, opts):
	"""One form for the Insert command: title, author, date and the design. Returns updated options or None."""
	w = projmod.normalize_options(opts)
	keep = dict(w)
	fields = [
		{"key": "title", "label": "&Title:", "default": w["title"]},
		{"key": "author", "label": "&Author:", "default": w["author"]},
	] + date_fields(w["date"])
	v = ask(parent, "Title page: text", fields)
	if v is None:
		return None
	w["title"], w["author"], w["date"] = v["title"].strip(), v["author"].strip(), date_from_values(v)
	_cat_titlepage(parent, w)
	if w == dict(keep, title=w["title"], author=w["author"], date=w["date"]) and w["titlepage_template"] == "standard" and not w["title"] and not w["author"]:
		return None
	return w


def notes_form(parent, opts):
	"""Footnote then endnote forms. Returns updated options."""
	w = projmod.normalize_options(opts)
	_cat_footnotes(parent, w)
	_cat_endnotes(parent, w)
	return w


def _cat_packages(parent, w):
	def add_hf(dlg):
		code = header_footer_code(dlg, w)
		if code:
			c = dlg.ctrls["extra_preamble"]
			cur = c.GetValue()
			c.SetValue(cur + ("\n" if cur and not cur.endswith("\n") else "") + code)
			ui.message("Header and footer code added to the extra preamble box")

	fields = [
		{"key": "amsmath", "type": "check", "label": "Math packages (amsmath, amssymb)", "default": w["amsmath"]},
		{"key": "graphicx", "type": "check", "label": "Image support (graphicx)", "default": w["graphicx"]},
		{"key": "hyperref", "type": "check", "label": "Clickable links and PDF bookmarks (hyperref)", "default": w["hyperref"]},
		{"key": "legacy_fonts", "type": "check", "label": "Add standard font packages for pdfLaTeX", "default": w["legacy_fonts"]},
		{"key": "extra_preamble", "type": "multiline", "label": "E&xtra preamble lines:", "default": w["extra_preamble"]},
	]
	v = ask(parent, "Packages and extra preamble", fields, extra_buttons=[("Create &header and footer code...", add_hf)])
	if v is None:
		return
	for k in ("amsmath", "graphicx", "hyperref"):
		w[k] = bool(v[k])
	w["legacy_fonts"] = bool(v["legacy_fonts"])
	w["extra_preamble"] = v["extra_preamble"]


def _cat_general(parent, w):
	fields = [
		{"key": "name", "label": "Project &name (also the name of the output file):", "default": w["_name"]},
		{"key": "engine", "type": "choice", "label": "LaTeX &engine:", "choices": projmod.ENGINES, "default": _idx(projmod.ENGINES, w["_engine"])},
		{"key": "include", "type": "check", "label": "Start each file on a &new page", "default": w["_include"]},
		{"key": "own", "type": "check", "label": "Use the preamble of the first file that has its own \\documentclass instead of these settings", "default": w["_own"]},
	]
	if w.get("_has_template"):
		fields.append({"key": "template", "type": "check", "label": "Keep the &layout of the imported main file", "default": w["_use_template"]})
	if w.get("_has_main"):
		fields.append({"key": "original", "type": "check", "label": "Build the &original main file as it is", "default": w["_build_original"]})
	v = ask(parent, "Project name and building", fields)
	if v is None:
		return
	w["_name"] = v["name"].strip() or w["_name"]
	w["_engine"] = projmod.ENGINES[v["engine"]]
	w["_include"], w["_own"] = bool(v["include"]), bool(v["own"])
	if w.get("_has_template"):
		w["_use_template"] = bool(v["template"])
	if w.get("_has_main"):
		w["_build_original"] = bool(v["original"])


def _s(v, none="not set"):
	return str(v).strip() or none


SHORT = {
	"title": "&Title, author, class", "titlepage": "Title pa&ge design", "lang": "&Language and main font",
	"fontfine": "Font fine t&uning", "fontother": "&Sans and mono fonts", "pagesize": "&Page size, columns",
	"margins": "&Margins", "layout": "Line spacing, page &numbers", "footnotes": "&Footnotes", "endnotes": "&Endnotes",
	"packages": "Pac&kages and extras", "general": "Project name, &building",
}

CATEGORIES = [
	("title", "Title, author and document class", _cat_title,
		lambda w: "%s, title %s, author %s" % (w["documentclass"], _s(w["title"]), _s(w["author"]))),
	("titlepage", "Title page design", _cat_titlepage,
		lambda w: "design %s%s" % (dict(projmod.TITLEPAGE_TEMPLATES)[w["titlepage_template"]].split(":")[0], (", logo " + os.path.basename(w["tp_logo"])) if w["tp_logo"] else "")),
	("lang", "Language and main font", _cat_lang,
		lambda w: "%s, font %s, size %s points" % (w["language"], _s(w["mainfont"], "language default"), w["fontsize"])),
	("fontfine", "Font fine tuning", _cat_fontfine,
		lambda w: "scale %s, fake bold %s, fake italic %s" % (w["font_scale"], _s(w["fake_bold"], "off"), _s(w["fake_italic"], "off"))),
	("fontother", "Sans-serif and monospace fonts", _cat_fontother,
		lambda w: "sans %s, mono %s" % (_s(w["sansfont"], "default"), _s(w["monofont"], "default"))),
	("pagesize", "Page size, orientation and columns", _cat_pagesize,
		lambda w: "%s, %s, %s column(s)%s" % (projmod.PAPER_LABELS[w["paper"]], w["orientation"], w["columns"], ", two-sided" if w["twoside"] else "")),
	("margins", "Margins", _cat_margins,
		lambda w: "all sides %s, top %s, bottom %s, left %s, right %s" % (_s(w["margin_all"], "default"), _s(w["margin_top"], "-"), _s(w["margin_bottom"], "-"), _s(w["margin_left"], "-"), _s(w["margin_right"], "-"))),
	("layout", "Line spacing, paragraphs and page numbers", _cat_layout,
		lambda w: "spacing %s, page numbers %s" % (w["spacing"], projmod.PAGE_NUMBERING_LABELS[w["pagenumbering"]])),
	("footnotes", "Footnotes", _cat_footnotes,
		lambda w: "numbering %s, style %s, size %s, layout %s" % (w["fn_numbering"], w["fn_style"], w["fn_size"] or "default", w["fn_layout"])),
	("endnotes", "Endnotes", _cat_endnotes,
		lambda w: "%s, numbering %s, heading %s" % ("used for all notes" if w["en_use"] else "on request", w["en_numbering"], w["en_title"] or "Notes")),
	("packages", "Packages and extra preamble", _cat_packages,
		lambda w: "math %s, images %s, links %s, extra lines %d" % ("on" if w["amsmath"] else "off", "on" if w["graphicx"] else "off", "on" if w["hyperref"] else "off", len([l for l in w["extra_preamble"].split("\n") if l.strip()]))),
]
GENERAL = ("general", "Project name and building", _cat_general,
	lambda w: "%s, engine %s" % (w["_name"], w["_engine"]))


class SettingsHub(wx.Dialog):
	"""All groups of settings as buttons side by side. Space or Enter opens a group."""

	def __init__(self, parent, title, cats, work, original):
		super().__init__(parent, title=title)
		self.cats, self.work, self.original, self.parent_win = cats, work, original, parent
		main = wx.BoxSizer(wx.VERTICAL)
		main.Add(wx.StaticText(self, label="Press Tab to move between the groups of settings, and Space or Enter to open one. When you are done, choose Apply changes."), 0, wx.ALL, 8)
		grid = wx.GridSizer(0, 3, 6, 6)
		self.buttons = []
		for key, _t, _ed, _sum in cats:
			b = wx.Button(self, label=SHORT[key])
			b.Bind(wx.EVT_BUTTON, lambda e, k=key: self.open_group(k))
			grid.Add(b, 0, wx.EXPAND)
			self.buttons.append(b)
		main.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
		main.Add(wx.StaticText(self, label="Current &values (read only):"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
		self.summary = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(620, 170))
		main.Add(self.summary, 1, wx.EXPAND | wx.ALL, 8)
		main.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
		self.FindWindowById(wx.ID_OK).SetLabel("&Apply changes")
		self.FindWindowById(wx.ID_OK).SetDefault()
		self.Bind(wx.EVT_BUTTON, self.on_cancel, id=wx.ID_CANCEL)
		self.SetSizerAndFit(main)
		self.CentreOnScreen()
		self.refresh()
		self.buttons[0].SetFocus()

	def refresh(self):
		self.summary.SetValue("\n".join("%s: %s" % (t, sm(self.work)) for _k, t, _e, sm in self.cats))

	def open_group(self, key):
		for k, _t, editor, _s in self.cats:
			if k == key:
				logger.log("settings group: %s" % key)
				editor(self, self.work)
		self.refresh()
		ui.message("Changes kept. Current values updated.")

	def on_cancel(self, evt):
		if self.work != self.original and wx.MessageBox("Discard the changes you made?", self.GetTitle(), wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
			return
		self.EndModal(wx.ID_CANCEL)


def edit_options(parent, options, project=None, title="Settings"):
	"""Settings editor. Returns the new options dict (and edits ``project``), or None."""
	logger.log("dialog: %s" % title)
	work = projmod.normalize_options(options)
	if project is not None:
		work.update({"_name": project.name, "_engine": project.engine, "_include": project.use_include, "_own": project.own_preamble,
			"_has_template": bool(project.body_template), "_use_template": project.use_body_template,
			"_has_main": bool(project.main_file), "_build_original": project.build_original})
	original = dict(work)
	cats = ([GENERAL] if project is not None else []) + CATEGORIES
	dlg = SettingsHub(parent, title, cats, work, original)
	try:
		if dlg.ShowModal() != wx.ID_OK:
			return None
	finally:
		dlg.Destroy()
	result = dict((k, v) for k, v in work.items() if not k.startswith("_"))
	if project is not None:
		project.name, project.engine = work["_name"], work["_engine"]
		project.use_include, project.own_preamble = work["_include"], work["_own"]
		project.use_body_template, project.build_original = work["_use_template"], work["_build_original"]
		project.options = result
	return result


def project_settings(parent, project):
	"""Edit project settings. Returns True when applied."""
	return edit_options(parent, project.options, project, "Project settings: %s" % project.name) is not None


def _hf_latex(text, o):
	"""LaTeX for one header or footer position and the extra package it needs (or None)."""
	t = text.strip()
	if t in ("", "(nothing)"):
		return "", None
	if t == "Page number":
		return "\\thepage", None
	if t == "Page x of y":
		return "\\thepage\\ / \\pageref{LastPage}", "lastpage"
	if t == "Chapter or section name":
		return "\\nouppercase{\\leftmark}", None
	if t == "Document title":
		return o.get("title", ""), None
	if t == "Author":
		return o.get("author", ""), None
	if t == "Date":
		return (o.get("date") or "\\today"), None
	return t, None


def header_footer_code(parent, opts=None):
	"""Ask for header and footer contents (choose from a list or type) and return preamble code, or None."""
	o = projmod.normalize_options(opts or {})
	positions = (("hl", "Header, &left:", "(nothing)"), ("hc", "Header, &centre:", "(nothing)"), ("hr", "Header, &right:", "(nothing)"),
		("fl", "Footer, l&eft:", "(nothing)"), ("fc", "Footer, c&entre:", "Page number"), ("fr", "Footer, r&ight:", "(nothing)"))
	fields = [{"key": k, "type": "combo", "choices": HF_CHOICES, "label": lab, "default": d} for k, lab, d in positions]
	fields.append({"key": "rule", "type": "check", "label": "Draw a &line under the header", "default": True})
	v = ask(parent, "Header and footer", fields, intro="Choose from the list, or type your own text.")
	if v is None:
		return None
	lines = ["\\usepackage{fancyhdr}", "\\pagestyle{fancy}", "\\fancyhf{}"]
	needs = []
	for key, cmd in (("hl", "\\fancyhead[L]"), ("hc", "\\fancyhead[C]"), ("hr", "\\fancyhead[R]"),
					("fl", "\\fancyfoot[L]"), ("fc", "\\fancyfoot[C]"), ("fr", "\\fancyfoot[R]")):
		text, pkg = _hf_latex(v[key], o)
		if text:
			lines.append("%s{%s}" % (cmd, text))
		if pkg and pkg not in needs:
			needs.append(pkg)
	lines.append("\\renewcommand{\\headrulewidth}{%s}" % ("0.4pt" if v["rule"] else "0pt"))
	for pkg in needs:
		lines.insert(0, "\\usepackage{%s}" % pkg)
	return "\n".join(lines) + "\n"


def build_dialog(parent, project, last):
	"""Ask what to build. Returns dict(fmt, scope, engine, open_after) or None."""
	has_proj = project is not None and bool(project.files)
	scopes = ["Current document"]
	if has_proj:
		scopes.append("Whole project: %s (%d files)" % (project.name, len(project.files)))
	fmts = [f[1] for f in builder.FORMATS]
	fields = [
		{"key": "fmt", "type": "choice", "label": "Output &format:", "choices": fmts, "default": min(last.get("fmt", 0), len(fmts) - 1)},
		{"key": "scope", "type": "choice", "label": "&What to build:", "choices": scopes, "default": min(last.get("scope", 1 if has_proj else 0), len(scopes) - 1)},
		{"key": "engine", "type": "choice", "label": "LaTeX &engine (only used for PDF):", "choices": projmod.ENGINES, "default": last.get("engine", 0)},
		{"key": "open_after", "type": "check", "label": "&Open the result when finished", "default": last.get("open_after", True)},
	]
	return ask(parent, "Build document", fields)


def settings_dialog(parent, cfg):
	latex = builder.find_tool("pdflatex", os.path.join(cfg.get("latex_dir", ""), "pdflatex.exe") if cfg.get("latex_dir") else "")
	pandoc = builder.find_tool("pandoc", cfg.get("pandoc_path", ""))
	intro = "LaTeX: %s. Pandoc: %s. Leave the path boxes empty to detect them automatically." % (latex or "not found", pandoc or "not found")
	fields = [
		{"key": "latex_dir", "label": "MiKTeX program folder (optional):", "default": cfg.get("latex_dir", ""), "button": ("Browse for &folder...", browse_dir("latex_dir"))},
		{"key": "pandoc_path", "label": "Pandoc program (optional):", "default": cfg.get("pandoc_path", ""), "button": ("Browse for pan&doc...", browse_file("pandoc_path", "Programs (*.exe)|*.exe|All files (*.*)|*.*"))},
		{"key": "passes", "type": "choice", "label": "LaTeX &passes:", "choices": ["1", "2", "3", "4"], "default": max(0, min(3, int(cfg.get("passes", 2)) - 1))},
		{"key": "auto_install", "type": "check", "label": "Let MiKTeX install &missing packages automatically", "default": cfg.get("auto_install", True)},
		{"key": "project_open", "type": "choice", "label": "When I open a project and no file is open:", "choices": ["Open the main file of the project", "Open no file (empty editor)"], "default": 0 if cfg.get("project_open", "main") == "main" else 1},
		{"key": "csl_path", "label": "Citation style file, .csl (optional):", "default": cfg.get("csl_path", ""), "button": ("Browse for &style...", browse_file("csl_path", "Citation styles (*.csl)|*.csl|All files (*.*)|*.*"))},
		{"key": "references_title", "label": "Heading above the references:", "default": cfg.get("references_title", "References")},
		{"key": "reference_docx", "label": "Word template, .docx (optional):", "default": cfg.get("reference_docx", ""), "button": ("Browse for &template...", browse_file("reference_docx", "Word files (*.docx)|*.docx|All files (*.*)|*.*"))},
		{"key": "word_numbering", "type": "check", "label": "&Number headings in Word output", "default": cfg.get("word_numbering", True)},
		{"key": "autosave", "label": "&Safety copy interval in seconds (0 = off):", "default": str(cfg.get("autosave_seconds", 15))},
	]

	def check(v):
		a = v["autosave"].strip()
		if not a.isdigit() or int(a) > 3600:
			return "Safety copy interval must be a number from 0 to 3600."
		return None

	v = ask(parent, "LaTeX Builder settings", fields, intro=intro, validator=check)
	if v is None:
		return False
	cfg["latex_dir"] = v["latex_dir"].strip()
	cfg["pandoc_path"] = v["pandoc_path"].strip()
	cfg["passes"] = v["passes"] + 1
	cfg["auto_install"] = bool(v["auto_install"])
	cfg["autosave_seconds"] = int(v["autosave"].strip())
	cfg["project_open"] = "main" if v["project_open"] == 0 else "none"
	cfg["csl_path"] = v["csl_path"].strip()
	cfg["references_title"] = v["references_title"].strip() or "References"
	cfg["reference_docx"] = v["reference_docx"].strip()
	cfg["word_numbering"] = bool(v["word_numbering"])
	return True


# ------------------------------------------------------------------ keyboard shortcuts

def accel_key(text):
	"""(flags, keycode) of an accelerator string, or None if it is not valid."""
	text = (text or "").strip()
	if not text:
		return None
	e = wx.AcceleratorEntry()
	try:
		ok = e.FromString(text)
	except Exception:
		ok = False
	if not ok:
		return None
	return (e.GetFlags() & (wx.ACCEL_CTRL | wx.ACCEL_ALT | wx.ACCEL_SHIFT), e.GetKeyCode())


def accel_problem(text):
	"""Return a message if the shortcut cannot be used, else None."""
	k = accel_key(text)
	if k is None:
		return "That is not a valid shortcut. Use words like Ctrl+Shift+X, Alt+Down or F7."
	flags, code = k
	is_fkey = wx.WXK_F1 <= code <= wx.WXK_F24
	if not (flags & (wx.ACCEL_CTRL | wx.ACCEL_ALT)) and not is_fkey:
		return "A shortcut needs Ctrl or Alt (or must be a function key), otherwise it would block typing."
	reserved = [(wx.ACCEL_CTRL, ord(c)) for c in "CXVA"]
	if k in reserved:
		return "Ctrl+C, Ctrl+X, Ctrl+V and Ctrl+A are reserved for copy, cut, paste and select all."
	return None


class ShortcutsDialog(wx.Dialog):
	"""List of every command with its shortcut; change, remove or reset them."""

	def __init__(self, frame):
		super().__init__(frame, title="Keyboard shortcuts")
		self.frame = frame
		self.shown = []
		main = wx.BoxSizer(wx.VERTICAL)
		main.Add(wx.StaticText(self, label="&Filter commands (type part of a name):"), 0, wx.ALL, 6)
		self.filter = wx.TextCtrl(self)
		main.Add(self.filter, 0, wx.EXPAND | wx.ALL, 6)
		main.Add(wx.StaticText(self, label="&Commands and their shortcuts:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
		self.list = wx.ListBox(self, size=(640, 300))
		main.Add(self.list, 1, wx.EXPAND | wx.ALL, 6)
		grid = wx.GridSizer(2, 2, 4, 4)
		for label, handler in (
			("&Change shortcut...", self.on_change),
			("&Remove shortcut", self.on_remove),
			("Reset this &command", self.on_reset),
			("Reset &all to defaults", self.on_reset_all),
		):
			b = wx.Button(self, label=label)
			b.Bind(wx.EVT_BUTTON, handler)
			grid.Add(b, 0, wx.EXPAND)
		main.Add(grid, 0, wx.EXPAND | wx.ALL, 6)
		main.Add(self.CreateStdDialogButtonSizer(wx.CLOSE), 0, wx.EXPAND | wx.ALL, 8)
		self.SetEscapeId(wx.ID_CLOSE)
		self.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CLOSE), id=wx.ID_CLOSE)
		self.filter.Bind(wx.EVT_TEXT, lambda e: self.refresh())
		self.filter.Bind(wx.EVT_KEY_DOWN, self._on_filter_key)
		self.list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_change)
		self.SetSizerAndFit(main)
		self.CentreOnScreen()
		self.refresh()
		self.filter.SetFocus()

	def _on_filter_key(self, evt):
		if evt.GetKeyCode() == wx.WXK_DOWN and self.shown:
			self.list.SetFocus()
			return
		evt.Skip()

	def _text(self, key):
		acc = self.frame.effective(key)
		return "%s: %s" % (self.frame.command_labels[key], acc if acc else "no shortcut")

	def refresh(self, keep=None):
		words = self.filter.GetValue().lower().split()
		self.shown = [k for k in self.frame.command_order if all(w in self.frame.command_labels[k].lower() for w in words)]
		self.list.Set([self._text(k) for k in self.shown])
		if self.shown:
			sel = self.shown.index(keep) if keep in self.shown else 0
			self.list.SetSelection(sel)

	def _current(self):
		i = self.list.GetSelection()
		return self.shown[i] if i != wx.NOT_FOUND else None

	def on_change(self, evt):
		key = self._current()
		if key is None:
			return
		label = self.frame.command_labels[key]

		def check(v):
			return accel_problem(v["s"])

		v = ask(self, "Change shortcut", [{"key": "s", "label": "New shortcut for %s (for example Ctrl+Shift+X, Alt+Down, F7):" % label, "default": self.frame.effective(key)}], validator=check)
		if v is None:
			return
		new = v["s"].strip()
		nk = accel_key(new)
		for other in self.frame.command_order:
			if other != key and accel_key(self.frame.effective(other)) == nk:
				if wx.MessageBox("%s is already used by %s. Move it to %s?" % (new, self.frame.command_labels[other], label), "Shortcut in use", wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
					return
				self.frame.set_shortcut(other, "")
		self.frame.set_shortcut(key, new)
		self.refresh(key)
		self.list.SetFocus()
		ui.message("%s now has the shortcut %s" % (label, new))

	def on_remove(self, evt):
		key = self._current()
		if key is None:
			return
		self.frame.set_shortcut(key, "")
		self.refresh(key)
		self.list.SetFocus()
		ui.message("Shortcut removed")

	def on_reset(self, evt):
		key = self._current()
		if key is None:
			return
		default = self.frame.defaults.get(key, "")
		nk = accel_key(default)
		if nk is not None:
			for other in self.frame.command_order:
				if other != key and accel_key(self.frame.effective(other)) == nk:
					self.frame.set_shortcut(other, "")
		self.frame.set_shortcut(key, None)
		self.refresh(key)
		self.list.SetFocus()
		ui.message("Reset to %s" % (default or "no shortcut"))

	def on_reset_all(self, evt):
		if wx.MessageBox("Reset every shortcut to its default?", "Keyboard shortcuts", wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
			return
		self.frame.reset_shortcuts()
		self.refresh()
		self.list.SetFocus()
		ui.message("All shortcuts reset")


# ------------------------------------------------------------------ small forms

def new_project_dialog(parent, default_name, default_folder, open_docs):
	"""One dialog for project name, folder and whether to add the open documents.

	Returns dict(name, folder, add_open) or None.
	"""
	def browse(dlg):
		d = wx.DirDialog(dlg, "Choose the folder for the project file", defaultPath=dlg.ctrls["folder"].GetValue(), style=wx.DD_DEFAULT_STYLE)
		try:
			if d.ShowModal() == wx.ID_OK:
				dlg.ctrls["folder"].SetValue(d.GetPath())
				ui.message("Folder: %s" % d.GetPath())
		finally:
			d.Destroy()

	def check(v):
		name = v["name"].strip()
		if not name:
			return "Please type a project name."
		if any(c in name for c in '<>:"/\\|?*'):
			return "The project name cannot contain any of these characters: < > : \" / \\ | ? *"
		folder = v["folder"].strip()
		if not folder or not os.path.isdir(folder):
			return "The folder does not exist. Type an existing folder or use Browse."
		return None

	fields = [
		{"key": "name", "label": "Project &name:", "default": default_name},
		{"key": "folder", "label": "&Folder where the project file is saved:", "default": default_folder, "button": ("&Browse for folder...", browse)},
	]
	if open_docs:
		fields.append({"key": "add_open", "type": "check", "label": "&Add the %d open saved document(s) to the project" % open_docs, "default": True})
	v = ask(parent, "New project", fields, validator=check)
	if v is None:
		return None
	v.setdefault("add_open", False)
	v["name"], v["folder"] = v["name"].strip(), v["folder"].strip()
	return v


def speech_options(parent, cfg):
	fields = [
		{"key": "confirm", "type": "choice", "label": "Confirmations after &inserting something:", "choices": ["Full (what was inserted and what to do next)", "Short (name only)", "None"],
			"default": {"full": 0, "short": 1, "none": 2}.get(cfg.get("confirm", "full"), 0)},
		{"key": "beeps", "type": "check", "label": "Play &tones when a build starts, succeeds or fails", "default": cfg.get("beeps", True)},
		{"key": "reminders", "type": "check", "label": "Say \"Still building\" every 15 &seconds during a long build", "default": cfg.get("reminders", True)},
	]
	v = ask(parent, "Speech and sound options", fields)
	if v is None:
		return False
	cfg["confirm"] = ["full", "short", "none"][v["confirm"]]
	cfg["beeps"] = bool(v["beeps"])
	cfg["reminders"] = bool(v["reminders"])
	return True


def editor_font_dialog(parent, face, size):
	"""Returns (face, size) or None."""
	def pick(dlg):
		r = choose_font(dlg, None, dlg.ctrls["face"].GetValue())
		if r is not None:
			dlg.ctrls["face"].SetValue(r)
			ui.message(r or "system default font")

	def check(v):
		if not v["size"].strip().isdigit() or not (8 <= int(v["size"]) <= 72):
			return "The size must be a number from 8 to 72."
		return None

	fields = [
		{"key": "face", "label": "&Font used in the editor (empty = system default):", "default": face, "button": ("Choose from &installed fonts...", pick)},
		{"key": "size", "label": "Font &size in points (8 to 72):", "default": str(size)},
	]
	v = ask(parent, "Editor font", fields, validator=check,
		intro="This changes only the editor window, not your document.")
	if v is None:
		return None
	return v["face"].strip(), int(v["size"])


def import_project_dialog(parent, main_path, default_name, summary):
	"""Ask how to import an existing main .tex file. Returns dict(name, mode, keep_body) or None."""
	def check(v):
		name = v["name"].strip()
		if not name or any(c in name for c in '<>:"/\\|?*'):
			return "Please type a project name without the characters < > : \" / \\ | ? *"
		return None

	fields = [
		{"key": "name", "label": "Project &name:", "default": default_name},
		{"key": "mode", "type": "choice", "label": "&How to import:", "choices": [
			"Convert into editable settings (recommended)",
			"Keep the main file as it is"], "default": 0},
		{"key": "keep_body", "type": "check", "label": "Keep the &layout of the main file body", "default": True},
	]
	v = ask(parent, "Import existing LaTeX project", fields, intro="Main file: %s. %s" % (main_path, summary), validator=check)
	if v is None:
		return None
	v["name"] = v["name"].strip()
	return v


# ------------------------------------------------------------------ user manual

def manual_dir():
	return os.path.join(os.path.dirname(os.path.abspath(__file__)), "manual")


def manual_sections(md):
	"""Split the markdown manual into (level, title, body) sections."""
	secs = []
	cur = None
	for ln in md.split("\n"):
		m = re.match(r"^(#{1,3})\s+(.*)$", ln)
		if m:
			if cur:
				secs.append(cur)
			cur = [len(m.group(1)), m.group(2).strip(), []]
		elif cur:
			cur[2].append(ln)
	if cur:
		secs.append(cur)
	out = []
	for level, title, body in secs:
		text = "\n".join(body).strip()
		text = re.sub(r"\*\*|`", "", text)
		out.append((level, title, text))
	return out


def show_manual(parent):
	path = os.path.join(manual_dir(), "manual.md")
	try:
		with open(path, encoding="utf-8") as fh:
			md = fh.read()
	except OSError:
		wx.MessageBox("The user manual file was not found: %s" % path, "User manual", wx.OK | wx.ICON_ERROR, parent)
		return
	secs = [x for x in manual_sections(md) if x[0] >= 2]
	items = []
	for level, title, text in secs:
		items.append(("%s%s" % ("    " * (level - 2), title), (title, text or "See the sections that follow this one."), text))
	while True:
		r = choose(parent, "User manual: choose a section (type to search the whole manual)", items, prompt="&Search the manual:")
		if r is None:
			return
		show_text(parent, r[0], r[1])


def open_manual_in_browser():
	path = os.path.join(manual_dir(), "manual.html")
	if not os.path.isfile(path):
		return False
	try:
		os.startfile(path)
		return True
	except (OSError, AttributeError):
		return False


# ------------------------------------------------------------------ package manager

class PackageManagerDialog(wx.Dialog):
	"""List of LaTeX packages: add \\usepackage lines, check what is installed, install and update."""

	def __init__(self, frame):
		super().__init__(frame, title="LaTeX packages")
		self.frame = frame
		self.cfg = frame.plugin.cfg
		self.info = builder.package_system(self.cfg)
		self.used = frame.packages_in_use()
		self.status = {}
		self.mpm = None
		self.busy = False
		self.alive = True
		self.views = ["Common LaTeX packages", "Packages used in this document or project", "Only installed packages", "Only packages that are not installed"]
		if self.info["mpm"]:
			self.views.append("All MiKTeX packages (names only)")
		main = wx.BoxSizer(wx.VERTICAL)
		main.Add(wx.StaticText(self, label="&Show:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
		self.view = wx.Choice(self, choices=self.views)
		self.view.SetSelection(0)
		main.Add(self.view, 0, wx.EXPAND | wx.ALL, 6)
		main.Add(wx.StaticText(self, label="&Filter (type part of a name or description):"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
		self.filter = wx.TextCtrl(self)
		main.Add(self.filter, 0, wx.EXPAND | wx.ALL, 6)
		main.Add(wx.StaticText(self, label="&Packages:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
		self.list = wx.ListBox(self, size=(760, 300))
		main.Add(self.list, 1, wx.EXPAND | wx.ALL, 6)
		grid = wx.GridSizer(0, 3, 4, 4)
		self.buttons = {}
		for key, label, handler in (
			("add", "&Add to document", self.on_add),
			("opts", "Add with &options...", self.on_add_options),
			("install", "&Install", self.on_install),
			("details", "&Details", self.on_details),
			("update", "&Update all packages", self.on_update),
			("refresh", "&Refresh status", self.on_refresh),
		):
			b = wx.Button(self, label=label)
			b.Bind(wx.EVT_BUTTON, handler)
			grid.Add(b, 0, wx.EXPAND)
			self.buttons[key] = b
		main.Add(grid, 0, wx.EXPAND | wx.ALL, 6)
		main.Add(self.CreateStdDialogButtonSizer(wx.CLOSE), 0, wx.EXPAND | wx.ALL, 8)
		self.buttons["add"].SetDefault()
		self.SetEscapeId(wx.ID_CLOSE)
		self.Bind(wx.EVT_BUTTON, self.on_close, id=wx.ID_CLOSE)
		self.Bind(wx.EVT_CLOSE, self.on_close)
		self.view.Bind(wx.EVT_CHOICE, self.on_view)
		self.filter.Bind(wx.EVT_TEXT, lambda e: self.refresh())
		self.filter.Bind(wx.EVT_KEY_DOWN, self._filter_key)
		self.list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_add)
		self.SetSizerAndFit(main)
		self.CentreOnScreen()
		self.refresh()
		logger.log("dialog: LaTeX packages (%s)" % (self.info["kind"] or "no TeX system found"))
		focus_dialog(self, self.list, "LaTeX packages. Checking which are installed.")
		self.start_status_check()

	def on_close(self, evt):
		self.alive = False
		self.EndModal(wx.ID_CLOSE)

	def _filter_key(self, evt):
		if evt.GetKeyCode() == wx.WXK_DOWN:
			self.list.SetFocus()
			return
		evt.Skip()

	# ---- data
	def _status_text(self, name):
		st = self.status.get(name)
		return "installed" if st else ("not installed" if st is False else "status unknown")

	def _entries(self):
		mode = self.view.GetSelection()
		words = self.filter.GetValue().lower().split()
		out = []
		if self.views[mode].startswith("All MiKTeX"):
			for name, inst in (self.mpm or []):
				text = "%s, %s" % (name, "installed" if inst else ("not installed" if inst is False else "status unknown"))
				if all(w in text.lower() for w in words):
					out.append((text, name))
			return out
		cat = list(packages_catalog.CATALOG)
		known = set(n for n, _c, _d in cat)
		for u in self.used:
			if u not in known:
				cat.append((u, "Used in your document", "Not in the common list"))
		for name, category, desc in cat:
			in_use = name in self.used
			st = self.status.get(name)
			if mode == 1 and not in_use:
				continue
			if mode == 2 and not st:
				continue
			if mode == 3 and st is not False:
				continue
			text = "%s: %s. %s. %s%s" % (name, desc, category, self._status_text(name), ", in use" if in_use else "")
			if all(w in text.lower() for w in words):
				out.append((text, name))
		return out

	def refresh(self, keep=None):
		self.entries = self._entries()
		self.list.Set([t for t, _n in self.entries])
		if self.entries:
			idx = [n for _t, n in self.entries].index(keep) if keep in [n for _t, n in self.entries] else 0
			self.list.SetSelection(idx)

	def current(self):
		i = self.list.GetSelection()
		return self.entries[i][1] if i != wx.NOT_FOUND and i < len(self.entries) else None

	def on_view(self, evt):
		if self.views[self.view.GetSelection()].startswith("All MiKTeX") and self.mpm is None:
			self.run_bg("Loading the list of all MiKTeX packages. This can take a minute.",
				lambda: builder.mpm_package_list(self.cfg, self.info),
				self._mpm_loaded)
			return
		self.refresh()
		ui.message("%d packages shown" % len(self.entries))

	def _mpm_loaded(self, result):
		self.mpm = result or []
		for n, inst in self.mpm:
			if inst is not None:
				self.status[n] = inst
		self.refresh()
		ui.message("%d MiKTeX packages loaded" % len(self.mpm))

	# ---- background work
	def run_bg(self, start_message, func, done):
		if self.busy:
			ui.message("Please wait, another operation is still running")
			return
		self.busy = True
		ui.message(start_message)
		logger.log("packages: %s" % start_message)

		def worker():
			try:
				result = func()
			except Exception:
				logger.exc("package operation failed")
				result = None
			wx.CallAfter(self._finish, done, result)

		threading.Thread(target=worker, daemon=True).start()

	def _finish(self, done, result):
		self.busy = False
		if not self.alive:
			return
		try:
			done(result)
		except Exception:
			logger.exc("package operation callback failed")

	def start_status_check(self):
		names = [n for n, _c, _d in packages_catalog.CATALOG] + [u for u in self.used if u not in packages_catalog.BY_NAME]

		def done(found):
			if found is None:
				ui.message("The installed packages cannot be checked because kpsewhich was not found.")
				return
			for n in names:
				self.status[n] = n.lower() in found
			self.refresh(self.current())
			ui.message("Installed packages checked: %d of %d are installed." % (sum(1 for n in names if self.status.get(n)), len(names)))

		self.run_bg("Checking which packages are installed.", lambda: builder.installed_styles(names, self.cfg, self.info), done)

	def on_refresh(self, evt):
		self.used = self.frame.packages_in_use()
		self.start_status_check()

	# ---- actions
	def _in_all_view(self):
		return self.views[self.view.GetSelection()].startswith("All MiKTeX")

	def on_add(self, evt):
		name = self.current()
		if not name:
			return
		if self._in_all_view():
			ui.message("In this view only Install is available. Use the common packages list to add a use package line.")
			return
		ui.message(self.frame.add_package(name, ""))
		self.used = self.frame.packages_in_use()
		self.refresh(name)

	def on_add_options(self, evt):
		name = self.current()
		if not name or self._in_all_view():
			return
		v = ask(self, "Add package with options", [{"key": "o", "label": "Options for %s (for example a4paper,margin=2cm):" % name, "default": ""}])
		if v is None:
			return
		ui.message(self.frame.add_package(name, v["o"].strip()))
		self.used = self.frame.packages_in_use()
		self.refresh(name)

	def on_install(self, evt):
		name = self.current()
		if not name:
			return
		if not self.info["kind"]:
			ui.message("No LaTeX system was found. Install MiKTeX first.")
			return
		mpm_mode = self._in_all_view()

		def done(result):
			ok, log = result if result else (False, "The installation failed.")
			logger.log("install %s: ok=%s" % (name, ok))
			self.status[name] = True if ok else self.status.get(name)
			self.refresh(name)
			ui.message("%s is installed." % name if ok else "%s could not be installed. Choose Details to read the output." % name)
			self.last_log = log

		self.run_bg("Installing %s. This may take a while." % name, lambda: builder.install_package(name, self.cfg, mpm_mode, self.info), done)

	def on_details(self, evt):
		name = self.current()
		if not name:
			return
		cat = packages_catalog.BY_NAME.get(name)
		lines = ["Package: %s" % name]
		if cat:
			lines += ["What it does: %s" % cat[2], "Group: %s" % cat[1]]
		lines.append("Status: %s" % self._status_text(name))
		lines.append("In use in this document or project: %s" % ("yes" if name in self.used else "no"))
		lines.append("")
		lines.append("To use it, choose Add to document. A line \\usepackage{%s} is added to the preamble." % name)
		if self.status.get(name) is False:
			lines.append("It is not installed. MiKTeX installs missing packages automatically the first time you build, or choose Install now.")
		log = getattr(self, "last_log", "")
		if log:
			lines += ["", "Output of the last installation:", log[-3000:]]
		show_text(self, "Package %s" % name, "\n".join(lines))

	def on_update(self, evt):
		if not self.info["kind"]:
			ui.message("No LaTeX system was found.")
			return
		if wx.MessageBox("Update all installed packages? This can take several minutes and needs an internet connection.", "Update packages", wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
			return

		def done(result):
			ok, log = result if result else (False, "The update failed.")
			self.last_log = log
			ui.message("Packages updated." if ok else "The update reported a problem. Choose Details to read the output.")
			self.start_status_check()

		self.run_bg("Updating all packages. Please wait.", lambda: builder.update_packages(self.cfg, self.info), done)


# ------------------------------------------------------------------ project manager

class ProjectDialog(wx.Dialog):
	def __init__(self, frame):
		super().__init__(frame, title="Project files: %s" % frame.project.name)
		self.frame = frame
		self.project = frame.project
		main = wx.BoxSizer(wx.VERTICAL)
		main.Add(wx.StaticText(self, label="&Files of the project, in the order they appear in the final document:"), 0, wx.ALL, 6)
		self.list = wx.ListBox(self, size=(600, 240))
		main.Add(self.list, 1, wx.EXPAND | wx.ALL, 6)
		row = wx.GridSizer(4, 2, 4, 4)
		for label, handler in (
			("&Add files...", self.on_add),
			("Add open &documents", self.on_add_open),
			("&Remove", self.on_remove),
			("Move &up", self.on_up),
			("Move &down", self.on_down),
			("&Open in editor", self.on_open),
			("&Settings...", self.on_settings),
			("&Build...", self.on_build),
		):
			b = wx.Button(self, label=label)
			b.Bind(wx.EVT_BUTTON, handler)
			row.Add(b, 0, wx.EXPAND)
		main.Add(row, 0, wx.EXPAND | wx.ALL, 6)
		main.Add(self.CreateStdDialogButtonSizer(wx.CLOSE), 0, wx.EXPAND | wx.ALL, 8)
		self.SetEscapeId(wx.ID_CLOSE)
		self.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CLOSE), id=wx.ID_CLOSE)
		self.list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_open)
		self.SetSizerAndFit(main)
		self.CentreOnScreen()
		self.refresh()
		self.list.SetFocus()
		logger.log("dialog: project files (%d files)" % len(self.project.files))
		focus_dialog(self, self.list, "Project files, %d files" % len(self.project.files))

	def refresh(self, select=None):
		items = []
		for i, f in enumerate(self.project.files, 1):
			items.append("%d. %s (%s)" % (i, os.path.basename(f), os.path.dirname(f)))
		self.list.Set(items)
		if items:
			self.list.SetSelection(min(select if select is not None else 0, len(items) - 1))

	def _save(self):
		self.frame.save_project()

	def on_add(self, evt):
		dlg = wx.FileDialog(self, "Add .tex files to the project", wildcard="TeX files (*.tex)|*.tex|All files (*.*)|*.*", style=wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_FILE_MUST_EXIST)
		try:
			if dlg.ShowModal() != wx.ID_OK:
				return
			paths = dlg.GetPaths()
		finally:
			dlg.Destroy()
		added = 0
		for p in paths:
			p = os.path.normpath(p)
			if p not in self.project.files:
				self.project.files.append(p)
				added += 1
		self._save()
		self.refresh(len(self.project.files) - 1)
		ui.message("%d file(s) added. The project now has %d files." % (added, len(self.project.files)))

	def on_add_open(self, evt):
		added = 0
		for d in self.frame.docs:
			if d.path and os.path.normpath(d.path) not in self.project.files:
				self.project.files.append(os.path.normpath(d.path))
				added += 1
		self._save()
		self.refresh(len(self.project.files) - 1)
		ui.message("%d open document(s) added. The project now has %d files." % (added, len(self.project.files)))

	def on_remove(self, evt):
		i = self.list.GetSelection()
		if i == wx.NOT_FOUND:
			return
		name = os.path.basename(self.project.files[i])
		del self.project.files[i]
		self._save()
		self.refresh(i)
		ui.message("%s removed from the project. %d files left." % (name, len(self.project.files)))

	def _move(self, delta):
		i = self.list.GetSelection()
		j = i + delta
		if i == wx.NOT_FOUND or j < 0 or j >= len(self.project.files):
			ui.message("Cannot move further")
			return
		fl = self.project.files
		fl[i], fl[j] = fl[j], fl[i]
		self._save()
		self.refresh(j)
		self.list.SetFocus()
		ui.message("%s moved to position %d of %d" % (os.path.basename(fl[j]), j + 1, len(fl)))

	def on_up(self, evt):
		self._move(-1)

	def on_down(self, evt):
		self._move(1)

	def on_open(self, evt):
		i = self.list.GetSelection()
		if i == wx.NOT_FOUND:
			return
		path = self.project.files[i]
		self.EndModal(wx.ID_CLOSE)
		wx.CallAfter(self.frame.open_path, path)

	def on_settings(self, evt):
		if project_settings(self, self.project):
			self._save()
			self.SetTitle("Project files: %s" % self.project.name)
			ui.message("Project settings saved")

	def on_build(self, evt):
		self.EndModal(wx.ID_CLOSE)
		wx.CallAfter(self.frame.cmd_build)
