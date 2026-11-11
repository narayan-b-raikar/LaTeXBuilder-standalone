# -*- coding: utf-8 -*-
"""The accessible LaTeX editor window (a normal wx frame that NVDA reads like any edit field)."""

import copy
import os
import re
import threading
import traceback
import uuid

import tones
import ui
import wx

from . import builder
from . import dialogs
from . import importer
from . import logger
from . import project as projmod
from . import recovery
from . import snippets
from . import texparse
from .snippets import CURSOR

WILDCARD = "TeX files (*.tex)|*.tex|All files (*.*)|*.*"
PROJ_WILDCARD = "LaTeX Builder projects (*.texproj)|*.texproj|All files (*.*)|*.*"

MENU_NAMES = {
	snippets.H: "&Headings",
	snippets.F: "&Format text",
	snippets.A: "&Alignment",
	snippets.L: "&Lists and blocks",
	snippets.N: "&Notes, poems, headers",
	snippets.D: "Document &parts",
	snippets.R: "&References, links, images, tables",
	snippets.M: "&Math",
}

THEMES = [
	("default", "System default colours", None, None),
	("white_on_black", "White text on black", (255, 255, 255), (0, 0, 0)),
	("yellow_on_black", "Yellow text on black", (255, 255, 0), (0, 0, 0)),
	("green_on_black", "Green text on black", (0, 255, 0), (0, 0, 0)),
	("black_on_yellow", "Black text on yellow", (0, 0, 0), (255, 255, 0)),
	("black_on_white", "Black text on white", (0, 0, 0), (255, 255, 255)),
]

TEXT_SYMBOLS = {"\\S", "\\P", "\\copyright", "\\textbullet", "\\dots", "--", "---"}


class Doc(object):
	def __init__(self, path=None, text="", modified=False):
		self.path = path
		self.text = text
		self.modified = modified
		self.caret = 0
		self.uid = uuid.uuid4().hex
		self.auto_text = None

	def name(self):
		return os.path.basename(self.path) if self.path else "Untitled"


class EditorFrame(wx.Frame):
	def __init__(self, plugin):
		super().__init__(None, title="LaTeX Builder", size=(960, 700))
		self.plugin = plugin
		self.docs = []
		self.cur = -1
		self.project = None
		self.last_result = None
		self.last_output = None
		self.building = False
		self._tick = None
		self.find_text = ""
		self.find_case = False
		self._title_modified = False
		self.palette = []
		self.shortcuts = []
		self.command_labels = {}
		self.command_order = []
		self.defaults = {}
		self.timer = None
		self.tc = self._create_tc()
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.tc, 1, wx.EXPAND)
		self.SetSizer(sizer)
		self._build_menus()
		self.Bind(wx.EVT_CLOSE, self._on_close)
		self._start_timer()
		self.CentreOnScreen()

	# ------------------------------------------------------------------ text control
	def _create_tc(self):
		style = wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_PROCESS_TAB | wx.TE_NOHIDESEL
		if not self.plugin.cfg.get("word_wrap", True):
			style |= wx.HSCROLL  # a horizontal scroll bar switches wrapping off
		tc = wx.TextCtrl(self, style=style)
		tc.SetMaxLength(0)
		tc.Bind(wx.EVT_TEXT, self._on_text)
		return tc

	def on_toggle_wrap(self, evt):
		cfg = self.plugin.cfg
		self._store()
		cfg["word_wrap"] = not cfg.get("word_wrap", True)
		self.plugin.save_cfg()
		idx = self.cur
		old = self.tc
		self.tc = self._create_tc()
		sizer = self.GetSizer()
		sizer.Replace(old, self.tc)
		old.Destroy()
		sizer.Layout()
		self.cur = -1  # the new control is empty: do not store it over the document
		if idx >= 0:
			self._show(idx, announce=False)
		ui.message("Word wrap on. Long lines continue on the next line." if cfg["word_wrap"] else "Word wrap off. Each paragraph is one long line.")

	# ------------------------------------------------------------------ menus
	def effective(self, key):
		ov = self.plugin.cfg.get("shortcuts", {})
		if key in ov:
			return ov[key]
		return self.defaults.get(key, "")

	def set_shortcut(self, key, value):
		"""value: new accelerator text, "" for none, None to restore the default."""
		ov = self.plugin.cfg.setdefault("shortcuts", {})
		if value is None:
			ov.pop(key, None)
		else:
			ov[key] = value
		self.plugin.save_cfg()

	def reset_shortcuts(self):
		self.plugin.cfg["shortcuts"] = {}
		self.plugin.save_cfg()

	def on_customize_shortcuts(self, evt):
		dlg = dialogs.ShortcutsDialog(self)
		try:
			dlg.ShowModal()
		finally:
			dlg.Destroy()
		self.rebuild_menus()
		ui.message("Shortcuts updated")
		self.tc.SetFocus()

	def rebuild_menus(self):
		self._build_menus()

	def _item(self, menu, menu_title, label, handler, accel=None, key=None):
		plain = label.replace("&", "")
		key = key or ("%s:%s" % (menu_title.replace("&", ""), plain)).lower()
		self.defaults[key] = accel or ""
		acc = self.effective(key)
		text = label if not acc else "%s\t%s" % (label, acc)
		item = menu.Append(wx.ID_ANY, text)
		full = "%s: %s" % (menu_title.replace("&", ""), plain)

		def safe(evt=None, h=handler, name=full, short=plain):
			try:
				logger.log("command: %s" % name)
				return h(evt)
			except Exception:
				logger.exc("command failed: %s" % name)
				ui.message("An error occurred in %s. Open Help, then View add-on log, for details." % short)

		self.Bind(wx.EVT_MENU, safe, item)
		self.palette.append((full, safe))
		self.shortcuts.append((plain, acc))
		self.command_labels[key] = full
		self.command_order.append(key)
		return item

	def _build_menus(self):
		self.palette, self.shortcuts, self.command_labels, self.command_order, self.defaults = [], [], {}, [], {}
		mb = wx.MenuBar()
		# File
		m = wx.Menu()
		t = "&File"
		self._item(m, t, "&New empty document", self.on_new, "Ctrl+N")
		self._item(m, t, "New document from &template...", lambda e: self.act_newdoc(None))
		self._item(m, t, "&Open...", self.on_open, "Ctrl+O")
		self._item(m, t, "&Save", self.on_save, "Ctrl+S")
		self._item(m, t, "Save &as...", self.on_save_as, "Ctrl+Shift+S")
		self._item(m, t, "Save all &documents", self.on_save_all, "Ctrl+F2")
		self._item(m, t, "&Close document", self.on_close_doc, "Ctrl+W")
		self._item(m, t, "Ne&xt document", lambda e: self.cycle_doc(1), "Ctrl+PgDn")
		self._item(m, t, "&Previous document", lambda e: self.cycle_doc(-1), "Ctrl+PgUp")
		self._item(m, t, "Open documents &list...", self.on_doc_list, "Ctrl+Shift+W")
		self._item(m, t, "E&xit editor", lambda e: self.Close())
		mb.Append(m, t)
		# Edit
		m = wx.Menu()
		t = "&Edit"
		self._item(m, t, "&Undo", lambda e: self.tc.Undo(), "Ctrl+Z")
		self._item(m, t, "&Redo", lambda e: self.tc.Redo(), "Ctrl+Y")
		self._item(m, t, "&Find...", self.on_find, "Ctrl+F")
		self._item(m, t, "Find &next", lambda e: self.find_again(False), "F3")
		self._item(m, t, "Find pre&vious", lambda e: self.find_again(True), "Shift+F3")
		self._item(m, t, "Replace &all...", self.on_replace_all, "Ctrl+H")
		self._item(m, t, "&Go to line...", self.on_goto, "Ctrl+G")
		self._item(m, t, "&Command list...", self.on_palette, "Ctrl+K")
		mb.Append(m, t)
		# Insert (from catalogue)
		insert = wx.Menu()
		t = "&Insert"
		by_cat = {}
		for s in snippets.SNIPPETS:
			by_cat.setdefault(s.category, []).append(s)
		for cat in snippets.CATEGORIES:
			sub = wx.Menu()
			for s in by_cat.get(cat, []):
				self._item(sub, "Insert " + MENU_NAMES[cat], s.label, lambda e, s=s: self.run_snippet(s), s.shortcut, key="insert:" + s.key)
			insert.AppendSubMenu(sub, MENU_NAMES[cat])
		insert.AppendSeparator()
		self._item(insert, t, "LaTeX &packages...", lambda e: self.act_packages(None), key="insert:packages-menu")
		self._item(insert, t, "&Title page from a template...", lambda e: self.act_titlepage(None), key="insert:titlepage-menu")
		self._item(insert, t, "Footnote and endnote &settings...", lambda e: self.act_notesetup(None), key="insert:notes-menu")
		mb.Append(insert, t)
		# Navigate
		m = wx.Menu()
		t = "&Navigate"
		self._item(m, t, "&Next heading", lambda e: self.nav_heading(False), "Alt+Down")
		self._item(m, t, "&Previous heading", lambda e: self.nav_heading(True), "Alt+Up")
		self._item(m, t, "Next heading, same or higher &level", lambda e: self.nav_heading(False, True), "Alt+Shift+Down")
		self._item(m, t, "Previous heading, same or higher l&evel", lambda e: self.nav_heading(True, True), "Alt+Shift+Up")
		self._item(m, t, "Document &structure list...", self.on_structure, "Ctrl+Shift+O")
		self._item(m, t, "&Announce where I am", self.on_announce, "F2")
		self._item(m, t, "Next &footnote or endnote", lambda e: self.nav_kind("footnote", False), "F8")
		self._item(m, t, "Previous footnote or endnote", lambda e: self.nav_kind("footnote", True), "Shift+F8")
		self._item(m, t, "Next en&vironment", lambda e: self.nav_kind("environment", False), "F9")
		self._item(m, t, "Previous environment", lambda e: self.nav_kind("environment", True), "Shift+F9")
		self._item(m, t, "Next &math", lambda e: self.nav_kind("math", False))
		self._item(m, t, "Previous math", lambda e: self.nav_kind("math", True))
		self._item(m, t, "Next c&omment", lambda e: self.nav_kind("comment", False))
		self._item(m, t, "Previous comment", lambda e: self.nav_kind("comment", True))
		mb.Append(m, t)
		# View
		m = wx.Menu()
		t = "&View"
		self._item(m, t, "&Increase text size", lambda e: self._zoom(2), "Alt+PgUp")
		self._item(m, t, "&Decrease text size", lambda e: self._zoom(-2), "Alt+PgDn")
		self._item(m, t, "&Reset text size", lambda e: self._zoom(0), "Ctrl+0")
		self._item(m, t, "Toggle &word wrap", self.on_toggle_wrap)
		self._item(m, t, "Editor &font...", self.on_editor_font)
		self._item(m, t, "&Colour theme...", self.on_theme)
		self._item(m, t, "&Speech and sound options...", self.on_speech_options)
		self._item(m, t, "Document s&tatistics", self.on_statistics, "Ctrl+F3")
		self._item(m, t, "Read selection or s&ection as plain text", self.on_read_section, "Ctrl+F8")
		self._item(m, t, "Read &paragraph as plain text", self.on_read_paragraph, "Ctrl+F9")
		self._item(m, t, "Read &line as plain text", self.on_read_line, "Ctrl+F7")
		mb.Append(m, t)
		# Project
		m = wx.Menu()
		t = "P&roject"
		self._item(m, t, "&New project...", self.on_project_new)
		self._item(m, t, "&Open project...", self.on_project_open, "Ctrl+Shift+P")
		self._item(m, t, "Open &last project", self.on_project_last)
		self._item(m, t, "&Import project from main .tex file...", self.on_project_import)
		self._item(m, t, "Project &files...", self.on_project_files, "F4")
		self._item(m, t, "Open project &main file", self.on_project_open_main)
		self._item(m, t, "Project &settings...", self.on_project_settings, "Shift+F4")
		self._item(m, t, "&Add this document to project", self.on_project_add_current, "Ctrl+F4")
		self._item(m, t, "&Save project", lambda e: self.save_project(True))
		mb.Append(m, t)
		# Build
		m = wx.Menu()
		t = "&Build"
		self._item(m, t, "&Build document...", lambda e: self.cmd_build(), "F5")
		self._item(m, t, "Build &again", lambda e: self.rebuild_last(), "F6")
		self._item(m, t, "Show &errors and warnings", lambda e: self.cmd_errors(), "F7")
		self._item(m, t, "View full build &log", lambda e: self.cmd_log(), "Shift+F7")
		self._item(m, t, "&Open last result", lambda e: self.open_output(), "Ctrl+F5")
		self._item(m, t, "LaTeX &packages...", lambda e: self.act_packages(None), key="build:packages-menu")
		self._item(m, t, "&Settings...", self.on_settings, "Shift+F5")
		mb.Append(m, t)
		# Help
		m = wx.Menu()
		t = "&Help"
		self._item(m, t, "User &manual", self.on_manual, "F1")
		self._item(m, t, "User manual in web &browser", self.on_manual_browser)
		self._item(m, t, "&Keyboard shortcuts list", self.on_shortcuts, "Ctrl+Shift+F1")
		self._item(m, t, "&Customize keyboard shortcuts...", self.on_customize_shortcuts, "Ctrl+F1")
		self._item(m, t, "&View add-on log...", self.on_view_log, "Shift+F1")
		self._item(m, t, "&Copy add-on log", self.on_copy_log)
		self._item(m, t, "View &NVDA log entries...", self.on_nvda_log)
		self._item(m, t, "&Open log folder", self.on_open_log_folder)
		self._item(m, t, "Cl&ear add-on log", self.on_clear_log)
		self._item(m, t, "&About", self.on_about)
		mb.Append(m, t)
		old = self.GetMenuBar()
		self.SetMenuBar(mb)
		if old is not None and old is not mb:
			try:
				old.Destroy()
			except Exception:
				pass
		self._block_rich_edit_shortcuts()

	def _block_rich_edit_shortcuts(self):
		"""Rich edit controls react to Ctrl+E/L/R/J as paragraph alignment; ignore those keys."""
		used = set()
		for k in self.command_order:
			try:
				used.add(dialogs.accel_key(self.effective(k)))
			except Exception:
				pass
		entries = []
		for key in ("E", "L", "R", "J"):
			if (wx.ACCEL_CTRL, ord(key)) in used:
				continue
			i = wx.NewIdRef().GetId()
			self.Bind(wx.EVT_MENU, lambda e: None, id=i)
			entries.append(wx.AcceleratorEntry(wx.ACCEL_CTRL, ord(key), i))
		self.SetAcceleratorTable(wx.AcceleratorTable(entries))

	# ------------------------------------------------------------------ position helpers
	def _text(self):
		return self.tc.GetValue()

	def _pos_to_idx(self, pos):
		return len(self.tc.GetRange(0, pos))

	def _idx_to_pos(self, idx):
		last = self.tc.GetLastPosition()
		pos = max(0, min(idx, last))
		for _ in range(6):
			cur = len(self.tc.GetRange(0, pos))
			if cur == idx:
				break
			pos = max(0, min(pos + (idx - cur), last))
		return pos

	def _cur_index(self):
		return self._pos_to_idx(self.tc.GetInsertionPoint())

	def _sel_text(self):
		return self.tc.GetStringSelection().replace("\r\n", "\n").replace("\r", "\n")

	def _sel_idx(self):
		a, b = self.tc.GetSelection()
		return self._pos_to_idx(a), self._pos_to_idx(b)

	def _set_sel_idx(self, a, b=None):
		if b is None:
			b = a
		self.tc.SetSelection(self._idx_to_pos(a), self._idx_to_pos(b))
		self.tc.ShowPosition(self._idx_to_pos(b))

	def _cur_line(self, text=None):
		text = self._text() if text is None else text
		return text.count("\n", 0, self._cur_index())

	def _goto_line(self, line):
		text = self._text()
		lines = text.split("\n")
		line = max(0, min(line, len(lines) - 1))
		idx = sum(len(l) + 1 for l in lines[:line])
		self._set_sel_idx(idx)
		self.tc.SetFocus()
		return lines[line]

	def _insert_at_idx(self, idx, text):
		"""Insert ``text`` at an index (e.g. in the preamble) keeping selection/caret."""
		a, b = self._sel_idx()
		pos = self._idx_to_pos(idx)
		self.tc.Replace(pos, pos, text)
		shift = len(text)
		a2 = a + shift if a >= idx else a
		b2 = b + shift if b >= idx else b
		self._set_sel_idx(a2, b2)

	# ------------------------------------------------------------------ title / state
	def _store(self):
		if self.cur < 0:
			return
		d = self.docs[self.cur]
		d.text = self.tc.GetValue()
		d.caret = self._cur_index()
		d.modified = self.tc.IsModified()

	def _update_title(self):
		if self.cur < 0:
			self.SetTitle("LaTeX Builder")
			return
		d = self.docs[self.cur]
		mod = self.tc.IsModified()
		self._title_modified = mod
		parts = [d.name() + (" (modified)" if mod else "")]
		if self.project:
			parts.append("Project " + self.project.name)
		parts.append("LaTeX Builder")
		self.SetTitle(" - ".join(parts))

	def _on_text(self, evt):
		if self.tc.IsModified() != self._title_modified:
			self._update_title()
		evt.Skip()

	def _show(self, idx, announce=True):
		self._store()
		self.cur = idx
		d = self.docs[idx]
		self.tc.ChangeValue(d.text)
		self.tc.EmptyUndoBuffer()
		self._apply_view(preserve=False)
		self.tc.DiscardEdits()
		if d.modified:
			self.tc.MarkDirty()
		self._set_sel_idx(min(d.caret, len(d.text)))
		self._update_title()
		self.tc.SetFocus()
		if announce:
			ui.message("%s, document %d of %d" % (d.name(), idx + 1, len(self.docs)))

	# ------------------------------------------------------------------ documents
	def new_doc(self, text="", path=None, announce=True):
		self._store()
		self.docs.append(Doc(path, text, False))
		self._show(len(self.docs) - 1, announce)

	def on_new(self, evt):
		self.new_doc("")

	def on_open(self, evt):
		dlg = wx.FileDialog(self, "Open TeX file(s)", wildcard=WILDCARD, style=wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_FILE_MUST_EXIST)
		try:
			if dlg.ShowModal() != wx.ID_OK:
				return
			paths = dlg.GetPaths()
		finally:
			dlg.Destroy()
		for p in paths:
			self.open_path(p)

	def open_path(self, path):
		path = os.path.normpath(path)
		for i, d in enumerate(self.docs):
			if d.path and os.path.normcase(d.path) == os.path.normcase(path):
				if i != self.cur:
					self._show(i)
				return i
		try:
			text = projmod.read_text_file(path)
		except (IOError, OSError) as exc:
			wx.MessageBox("Could not open %s\n%s" % (path, exc), "Open", wx.OK | wx.ICON_ERROR, self)
			return None
		# replace an untouched empty untitled document
		if len(self.docs) == 1 and not self.docs[0].path and not self.tc.IsModified() and not self.tc.GetValue():
			self.docs[0] = Doc(path, text, False)
			self.cur = -1
			self._show(0)
			ui.message("%s opened" % os.path.basename(path))
			return 0
		self.new_doc(text, path, announce=False)
		ui.message("%s opened, %d lines" % (os.path.basename(path), text.count("\n") + 1))
		return self.cur

	def save_doc(self, idx=None):
		"""Save document ``idx`` (default: current). Returns False if cancelled/failed."""
		if idx is None:
			idx = self.cur
		if idx == self.cur:
			self._store()
		d = self.docs[idx]
		if not d.path:
			return self.save_doc_as(idx)
		try:
			projmod.write_text_file(d.path, d.text)
		except (IOError, OSError) as exc:
			wx.MessageBox("Could not save %s\n%s" % (d.path, exc), "Save", wx.OK | wx.ICON_ERROR, self)
			return False
		d.modified = False
		recovery.remove(self.plugin.cfg_dir(), d.uid)
		if idx == self.cur:
			self.tc.DiscardEdits()
			self._update_title()
		return True

	def save_doc_as(self, idx=None):
		if idx is None:
			idx = self.cur
		if idx == self.cur:
			self._store()
		d = self.docs[idx]
		start = os.path.dirname(d.path) if d.path else (os.path.dirname(self.project.path) if self.project and self.project.path else "")
		dlg = wx.FileDialog(self, "Save TeX file as", defaultDir=start, defaultFile=(d.name() if d.path else "document.tex"), wildcard=WILDCARD, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
		try:
			if dlg.ShowModal() != wx.ID_OK:
				return False
			path = dlg.GetPath()
		finally:
			dlg.Destroy()
		if not os.path.splitext(path)[1]:
			path += ".tex"
		d.path = os.path.normpath(path)
		return self.save_doc(idx)

	def on_save(self, evt):
		if self.save_doc():
			ui.message("Saved %s" % self.docs[self.cur].name())

	def on_save_as(self, evt):
		if self.save_doc_as():
			ui.message("Saved as %s" % self.docs[self.cur].name())

	def on_save_all(self, evt):
		self._store()
		n = 0
		for i, d in enumerate(self.docs):
			if d.modified:
				if not self.save_doc(i):
					return
				n += 1
		ui.message("%d document(s) saved" % n if n else "Nothing to save")

	def _confirm_close(self, idx):
		"""Ask to save if modified. Returns False if the user cancelled."""
		d = self.docs[idx]
		if idx == self.cur:
			self._store()
		if not d.modified:
			return True
		dlg = wx.MessageDialog(self, "Save changes to %s?" % d.name(), "LaTeX Builder", wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION)
		dlg.SetYesNoCancelLabels("&Save", "&Don't save", "&Cancel")
		try:
			r = dlg.ShowModal()
		finally:
			dlg.Destroy()
		if r == wx.ID_CANCEL:
			return False
		if r == wx.ID_YES:
			return self.save_doc(idx)
		return True

	def on_close_doc(self, evt):
		if self.cur < 0 or not self._confirm_close(self.cur):
			return
		old = self.cur
		name = self.docs[old].name()
		recovery.remove(self.plugin.cfg_dir(), self.docs[old].uid)
		del self.docs[old]
		self.cur = -1
		if not self.docs:
			self.docs.append(Doc())
			self._show(0, announce=False)
			ui.message("%s closed. New empty document." % name)
		else:
			self._show(min(old, len(self.docs) - 1), announce=False)
			ui.message("%s closed. Now in %s" % (name, self.docs[self.cur].name()))

	def cycle_doc(self, delta):
		if len(self.docs) < 2:
			ui.message("Only one document is open")
			return
		self._show((self.cur + delta) % len(self.docs))

	def on_doc_list(self, evt):
		self._store()
		items = [("%d. %s%s" % (i + 1, d.name(), " (modified)" if d.modified else ""), i) for i, d in enumerate(self.docs)]
		r = dialogs.choose(self, "Open documents", items, initial=self.cur, show_filter=False)
		if r is not None and r != self.cur:
			self._show(r)

	def _on_close(self, evt):
		self._store()
		for i in range(len(self.docs)):
			if not self._confirm_close(i):
				if evt.CanVeto():
					evt.Veto()
					return
		if self._tick:
			self._tick.Stop()
		if self.timer:
			self.timer.Stop()
		for d in self.docs:
			recovery.remove(self.plugin.cfg_dir(), d.uid)
		self.plugin.frame_closed()
		self.Destroy()

	# ------------------------------------------------------------------ inserting
	def _ensure_packages(self, pkgs):
		added = []
		for name, opts in pkgs:
			res = snippets.package_insertion(self._text(), name, opts)
			if res:
				self._insert_at_idx(res[0], res[1])
				added.append(name)
		return added

	def _insert_text(self, text, back=0, block=False, label="", pkgs=()):
		tc = self.tc
		added = self._ensure_packages(pkgs)
		if block:
			start, _end = tc.GetSelection()
			idx = self._pos_to_idx(start)
			end_idx = self._pos_to_idx(_end)
			val = self._text()
			if text.endswith("\n") and (end_idx >= len(val) or val[end_idx] == "\n"):
				# the line already ends here: do not create an extra blank line
				text = text[:-1]
				back = max(0, back - 1)
			if idx > 0 and val[idx - 1] != "\n":
				text = "\n" + text
		tc.WriteText(text)
		if back:
			idx = self._cur_index() - back
			self._set_sel_idx(idx)
		level = self.plugin.cfg.get("confirm", "full")
		if level == "none":
			msg = ""
		elif level == "short":
			msg = label.split(". ")[0]
		else:
			msg = label
			if added:
				msg += ". Added package " + ", ".join(added) + " to the preamble"
		if msg:
			ui.message(msg)

	def insert_template(self, tpl, block=False, pkgs=(), label=""):
		sel = self._sel_text()
		if block:
			sel = sel.strip("\r\n")
		if CURSOR in tpl:
			before, after = tpl.split(CURSOR, 1)
		else:
			before, after = tpl, ""
		if sel:
			self._insert_text(before + sel + after, back=len(after), block=block, label=label + " applied to selection", pkgs=pkgs)
		else:
			self._insert_text(before + after, back=len(after), block=block, label=label + " inserted", pkgs=pkgs)

	def run_snippet(self, snip):
		if snip.action:
			getattr(self, "act_" + snip.action)(snip)
		else:
			self.insert_template(snip.tpl, snip.block, snip.pkgs, snip.label.rstrip("."))

	# --- special insert actions
	def act_poem(self, snip):
		sel = self._sel_text()
		if sel.strip():
			body = texparse.poem_from_lines(sel)
			self._insert_text("\\begin{verse}\n%s\n\\end{verse}\n" % body, block=True, label="Poem created from the selected lines")
		else:
			self._insert_text("\\begin{verse}\n\n\\end{verse}\n", back=len("\n\\end{verse}\n"), block=True,
				label="Poem inserted. Type the lines. Press Shift+Enter to end a line, and leave a blank line between stanzas")

	def act_headerfooter(self, snip):
		code = dialogs.header_footer_code(self, self.project.options if self.project else {})
		if not code:
			return
		m = re.search(r"^[ \t]*\\begin\{document\}", self._text(), re.M)
		if m:
			self._insert_at_idx(m.start(), code)
			ui.message("Header and footer code added to the preamble")
		else:
			self._insert_text(code, block=True, label="Header and footer code inserted here. Move it above begin document")

	def act_titlepage(self, snip):
		base = self.project.options if self.project else {}
		w = dialogs.titlepage_form(self, base)
		if w is None:
			return
		code = projmod.titlepage_code(w)
		if code is None:
			code = "\\title{%s}\n\\author{%s}\n\\date{%s}\n\\maketitle\n" % (w["title"], w["author"], w["date"])
		pkgs = (("graphicx", ""),) if w["tp_logo"].strip() and "includegraphics" in code else ()
		self._insert_text(code, block=True, label="Title page inserted", pkgs=pkgs)
		if self.project and wx.MessageBox("Use this title page design for the whole project as well?", "Title page", wx.YES_NO | wx.ICON_QUESTION, self) == wx.YES:
			o = projmod.normalize_options(self.project.options)
			for k in ("title", "author", "date", "titlepage_template", "tp_subtitle", "tp_institution", "tp_department", "tp_extra", "tp_logo"):
				o[k] = w[k]
			o["maketitle"] = True
			self.project.options = o
			self.save_project()
			ui.message("The project now uses this title page design")

	def act_notesetup(self, snip):
		base = projmod.normalize_options(self.project.options if self.project else {})
		w = dialogs.notes_form(self, base)
		if w is None:
			return
		xe = projmod.needs_xelatex(w)
		lines = projmod.notes_preamble(w, xe)
		text = self._text()
		m = re.search(r"^[ \t]*\\begin\{document\}", text, re.M)
		if m and lines:
			self._insert_at_idx(m.start(), "\n".join(lines) + "\n")
			ui.message("Footnote and endnote settings added to the preamble of this document")
		elif self.project:
			o = projmod.normalize_options(self.project.options)
			for k in ("fn_numbering", "fn_style", "fn_size", "fn_font", "fn_layout", "fn_rule", "fn_bottom", "fn_sep",
					"en_use", "en_title", "en_size", "en_style", "en_numbering", "en_auto"):
				o[k] = w[k]
			self.project.options = o
			self.save_project()
			ui.message("Footnote and endnote settings saved in the project settings")
		elif lines:
			self._insert_text("\n".join(lines) + "\n", block=True, label="Footnote and endnote settings inserted here. Move them above begin document")
		else:
			ui.message("These are the default settings, so nothing was added")

	def act_input(self, snip):
		dlg = wx.FileDialog(self, "Choose the .tex file to include", wildcard=WILDCARD, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
		try:
			if dlg.ShowModal() != wx.ID_OK:
				return
			path = dlg.GetPath()
		finally:
			dlg.Destroy()
		base = os.path.splitext(projmod.fwd(path))[0]
		self._insert_text("\\input{%s}\n" % base, block=True, label="Include command inserted for %s" % os.path.basename(path))

	def act_newdoc(self, snip):
		o = projmod.normalize_options(self.project.options if self.project else {})
		opts = dialogs.edit_options(self, o, None, "New document from template")
		if opts is None:
			return
		self.new_doc(projmod.build_skeleton(opts), announce=False)
		# put the caret on the first heading's braces
		text = self._text()
		i = text.find("{}\n", text.find("\\begin{document}"))
		if i >= 0:
			self._set_sel_idx(i + 1)
		ui.message("New document created. The caret is inside the first heading; type its title.")

	def act_hyperlink(self, snip):
		sel = self._sel_text()
		v = dialogs.ask(self, "Hyperlink", [
			{"key": "url", "label": "Web address (&URL):", "default": "https://"},
			{"key": "text", "label": "Link &text (what is read and printed):", "default": sel},
		], validator=lambda v: "Please type the web address." if not v["url"].strip() else None)
		if v is None:
			return
		url = v["url"].strip().replace("%", "\\%").replace("#", "\\#")
		text = v["text"].strip() or v["url"].strip()
		self._insert_text("\\href{%s}{%s}" % (url, text), label="Hyperlink inserted", pkgs=snip.pkgs)

	def act_image(self, snip):
		dlg = wx.FileDialog(self, "Choose the picture", wildcard="Pictures (*.png;*.jpg;*.jpeg;*.pdf)|*.png;*.jpg;*.jpeg;*.pdf|All files (*.*)|*.*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
		try:
			if dlg.ShowModal() != wx.ID_OK:
				return
			path = dlg.GetPath()
		finally:
			dlg.Destroy()
		widths = [("Full text width", "\\textwidth"), ("80 percent of the width", "0.8\\textwidth"), ("50 percent of the width", "0.5\\textwidth"), ("30 percent of the width", "0.3\\textwidth"), ("Original size", "")]
		v = dialogs.ask(self, "Picture options", [
			{"key": "width", "type": "choice", "label": "&Width:", "choices": [w[0] for w in widths], "default": 1},
			{"key": "caption", "label": "&Caption (leave empty for none):", "default": ""},
			{"key": "label", "label": "&Label for references (optional):", "default": ""},
		])
		if v is None:
			return
		w = widths[v["width"]][1]
		opt = "[width=%s]" % w if w else ""
		inc = "\\includegraphics%s{%s}" % (opt, projmod.fwd(path))
		cap = v["caption"].strip()
		if cap:
			lines = ["\\begin{figure}[htbp]", "\t\\centering", "\t" + inc, "\t\\caption{%s}" % cap]
			if v["label"].strip():
				lines.append("\t\\label{%s}" % v["label"].strip())
			lines.append("\\end{figure}")
		else:
			lines = ["\\begin{center}", "\t" + inc, "\\end{center}"]
		self._insert_text("\n".join(lines) + "\n", block=True, label="Picture inserted", pkgs=snip.pkgs)

	def act_table(self, snip):
		def check(v):
			try:
				r, c = int(v["rows"]), int(v["cols"])
			except ValueError:
				return "Rows and columns must be numbers."
			if not (1 <= r <= 100 and 1 <= c <= 20):
				return "Use 1 to 100 rows and 1 to 20 columns."
			return None
		v = dialogs.ask(self, "Table", [
			{"key": "rows", "label": "Number of &rows:", "default": "3"},
			{"key": "cols", "label": "Number of &columns:", "default": "3"},
			{"key": "header", "type": "check", "label": "First row is a &header (bold)", "default": True},
			{"key": "borders", "type": "check", "label": "Draw &lines between cells", "default": True},
			{"key": "caption", "label": "Ca&ption (leave empty for none):", "default": ""},
		], validator=check)
		if v is None:
			return
		rows, cols = int(v["rows"]), int(v["cols"])
		b = v["borders"]
		spec = ("|" + "c|" * cols) if b else "c" * cols
		out = ["\\begin{tabular}{%s}" % spec]
		if b:
			out.append("\\hline")
		for r in range(rows):
			cells = []
			for c in range(cols):
				if r == 0 and v["header"]:
					cells.append("\\textbf{%s}" % (CURSOR if c == 0 else ""))
				else:
					cells.append(CURSOR if (r == 0 and c == 0) else "")
			out.append(" & ".join(cells) + " \\\\" + (" \\hline" if b else ""))
			if r == 0 and v["header"] and not b:
				out.append("\\hline")
		out.append("\\end{tabular}")
		body = "\n".join(out)
		cap = v["caption"].strip()
		if cap:
			body = "\\begin{table}[htbp]\n\\centering\n%s\n\\caption{%s}\n\\end{table}" % (body, cap)
		else:
			body = "\\begin{center}\n%s\n\\end{center}" % body
		body += "\n"
		before, after = body.split(CURSOR, 1)
		self._insert_text(before + after, back=len(after), block=True, label="Table with %d rows and %d columns inserted. The caret is in the first cell; type & to move to the next cell" % (rows, cols))

	def act_symbols(self, snip):
		items = [("%s  (%s)" % (n, t), t) for n, t in snippets.SYMBOLS]
		r = dialogs.choose(self, "Symbols and Greek letters", items, prompt="&Type the name, for example alpha or integral:")
		if r is None:
			return
		text = self._text()
		idx = self._cur_index()
		before = text[:idx].replace("\\$", "")
		in_math = before.count("$") % 2 == 1
		if not in_math:
			envs = texparse.open_environments(text.split("\n"), self._cur_line(text))
			in_math = any(e.rstrip("*") in ("equation", "align", "gather", "multline", "eqnarray", "math", "displaymath") for e in envs)
		if not in_math and before.rfind("\\[") > before.rfind("\\]"):
			in_math = True
		wrap = (not in_math) and r not in TEXT_SYMBOLS
		code = "$%s$" % r if wrap else r
		back = 0
		if r.endswith("{}"):
			back = 1 + (1 if wrap else 0)
		pkgs = (("amssymb", ""),) if r in ("\\therefore", "\\because") else ()
		self._insert_text(code, back=back, label="Inserted %s" % r, pkgs=pkgs)

	# ------------------------------------------------------------------ navigation
	def _describe_heading(self, h):
		name = h.kind.capitalize()
		if h.starred:
			name += " without number"
		num = (" " + h.number) if h.number else ""
		return "%s%s, %s" % (name, num, h.title or "no title yet")

	def nav_heading(self, backwards, same_level=False):
		text = self._text()
		lines = text.split("\n")
		heads = texparse.find_headings(lines)
		if not heads:
			ui.message("This document has no headings")
			return
		line = self._cur_line(text)
		lvl = None
		if same_level:
			h = texparse.heading_at(heads, line)
			if h is not None:
				lvl = h.level
		tgt = texparse.next_heading(heads, line, backwards, lvl)
		if tgt is None:
			ui.message("No previous heading" if backwards else "No next heading")
			return
		self._goto_line(tgt.line)
		ui.message(self._describe_heading(tgt))

	def nav_kind(self, kind, backwards):
		lines = self._text().split("\n")
		found = texparse.find_kind_lines(lines, kind)
		names = {"footnote": "footnote or endnote", "environment": "environment", "math": "math", "comment": "comment"}
		tgt = texparse.next_in(found, self._cur_line(), backwards)
		if tgt is None:
			ui.message("No %s %s" % ("previous" if backwards else "next", names[kind]))
			return
		txt = self._goto_line(tgt)
		ui.message("Line %d: %s" % (tgt + 1, txt.strip()))

	def on_structure(self, evt):
		text = self._text()
		lines = text.split("\n")
		heads = texparse.find_headings(lines)
		if not heads:
			ui.message("This document has no headings")
			return
		cur = texparse.heading_at(heads, self._cur_line(text))
		items = []
		initial = 0
		for i, h in enumerate(heads):
			ind = "    " * max(0, h.level)
			items.append(("%s%s %s (line %d)" % (ind, h.kind.capitalize() + ("*" if h.starred else ""), h.label(), h.line + 1), h))
			if cur is h:
				initial = i
		r = dialogs.choose(self, "Document structure", items, initial=initial, prompt="&Filter headings:")
		if r is not None:
			self._goto_line(r.line)
			ui.message(self._describe_heading(r))

	def on_announce(self, evt):
		text = self._text()
		lines = text.split("\n")
		line = self._cur_line(text)
		heads = texparse.find_headings(lines)
		path = texparse.heading_path(heads, line)
		envs = texparse.open_environments(lines, line)
		idx = self._cur_index()
		col = idx - (text.rfind("\n", 0, idx) + 1) + 1
		parts = ["Line %d of %d, column %d" % (line + 1, len(lines), col)]
		if path:
			parts.append("in " + ", inside ".join(reversed([self._describe_heading(h) for h in path])))
		else:
			parts.append("before the first heading")
		if envs:
			parts.append("inside environment " + ", ".join(reversed(envs)))
		ui.message(". ".join(parts))

	def on_goto(self, evt):
		total = self._text().count("\n") + 1
		v = dialogs.ask(self, "Go to line", [{"key": "n", "label": "Line number (1 to %d):" % total, "default": str(self._cur_line() + 1)}],
			validator=lambda v: None if v["n"].strip().isdigit() else "Please type a number.")
		if v is None:
			return
		txt = self._goto_line(int(v["n"]) - 1)
		ui.message("Line %s: %s" % (v["n"].strip(), txt))

	def on_palette(self, evt):
		items = [(label, h) for label, h in self.palette]
		r = dialogs.choose(self, "Command list", items, prompt="&Type part of a command name (for example footnote, bold, build):")
		if r is not None:
			wx.CallAfter(r, None)

	# ------------------------------------------------------------------ find / replace
	def _find(self, backwards=False):
		text = self._text()
		needle = self.find_text
		if not needle:
			ui.message("Nothing to search for. Press Control F first.")
			return
		hay, nd = (text, needle) if self.find_case else (text.lower(), needle.lower())
		a, b = self._sel_idx()
		if backwards:
			i = hay.rfind(nd, 0, a)
			wrapped = False
			if i < 0:
				i = hay.rfind(nd)
				wrapped = i >= 0
		else:
			i = hay.find(nd, b)
			wrapped = False
			if i < 0:
				i = hay.find(nd)
				wrapped = i >= 0
		if i < 0:
			ui.message("Not found: %s" % needle)
			return
		self._set_sel_idx(i, i + len(needle))
		line = text.count("\n", 0, i)
		ln = text.split("\n")[line]
		ui.message(("Search wrapped. " if wrapped else "") + "Line %d: %s" % (line + 1, ln.strip()))

	def on_find(self, evt):
		sel = self._sel_text()
		v = dialogs.ask(self, "Find", [
			{"key": "t", "label": "&Find what:", "default": sel if sel and "\n" not in sel else self.find_text},
			{"key": "case", "type": "check", "label": "&Match case", "default": self.find_case},
		])
		if v is None or not v["t"]:
			return
		self.find_text, self.find_case = v["t"], v["case"]
		self._find(False)

	def find_again(self, backwards):
		self._find(backwards)

	def on_replace_all(self, evt):
		v = dialogs.ask(self, "Replace all", [
			{"key": "t", "label": "&Find what:", "default": self.find_text},
			{"key": "r", "label": "Replace &with:", "default": ""},
			{"key": "case", "type": "check", "label": "&Match case", "default": self.find_case},
		])
		if v is None or not v["t"]:
			return
		text = self._text()
		flags = 0 if v["case"] else re.I
		new, n = re.subn(re.escape(v["t"]), lambda m: v["r"], text, flags=flags)
		if n:
			caret = self._cur_index()
			self.tc.SetValue(new)
			self._set_sel_idx(min(caret, len(new)))
		self.find_text, self.find_case = v["t"], v["case"]
		ui.message("%d replacement(s) made" % n)

	# ------------------------------------------------------------------ project commands
	def _remember_project(self):
		if self.project and self.project.path:
			self.plugin.cfg["last_project"] = self.project.path
			self.plugin.save_cfg()

	def save_project(self, announce=False):
		if not self.project:
			return
		if not self.project.path:
			return
		try:
			self.project.save()
			self._remember_project()
			if announce:
				ui.message("Project saved")
		except (IOError, OSError) as exc:
			wx.MessageBox("Could not save the project\n%s" % exc, "Project", wx.OK | wx.ICON_ERROR, self)

	def load_project(self, path):
		try:
			self.project = projmod.Project.load(path)
		except Exception as exc:
			wx.MessageBox("Could not open the project\n%s" % exc, "Project", wx.OK | wx.ICON_ERROR, self)
			return False
		self._remember_project()
		self._update_title()
		ui.message("Project %s opened with %d files" % (self.project.name, len(self.project.files)))
		self._open_project_main()
		return True

	def project_main_path(self):
		"""The main file of the project: the imported main file, otherwise the first file."""
		p = self.project
		if not p:
			return None
		if p.main_file and os.path.isfile(p.main_file):
			return p.main_file
		for f in p.files:
			if os.path.isfile(f):
				return f
		return None

	def _blank_placeholder_only(self):
		return (len(self.docs) == 1 and not self.docs[0].path and not self.tc.GetValue() and not self.tc.IsModified())

	def _open_project_main(self):
		"""After a project is opened with no file open: open its main file, or leave the editor empty (a setting)."""
		if self.plugin.cfg.get("project_open", "main") != "main" or not self.project:
			return
		if not self._blank_placeholder_only():
			return
		path = self.project_main_path()
		if path:
			self.open_path(path)

	def on_project_open_main(self, evt):
		path = self.project_main_path()
		if not path:
			ui.message("This project has no file that can be opened")
			return
		self.open_path(path)

	def on_project_new(self, evt):
		self._store()
		saved = [d for d in self.docs if d.path]
		if self.cur >= 0 and self.docs[self.cur].path:
			start = os.path.dirname(self.docs[self.cur].path)
		else:
			docs_dir = os.path.join(os.path.expanduser("~"), "Documents")
			start = docs_dir if os.path.isdir(docs_dir) else os.path.expanduser("~")
		v = dialogs.new_project_dialog(self, "My document", start, len(saved))
		if v is None:
			return
		safe_name = "".join("_" if c in '<>:"/\\|?*' else c for c in v["name"])
		path = os.path.join(v["folder"], safe_name + ".texproj")
		if os.path.exists(path) and wx.MessageBox("A project file with this name already exists in that folder. Replace it?", "New project", wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
			return
		p = projmod.Project(path)
		p.name = v["name"]
		if v["add_open"]:
			p.files = [os.path.normpath(d.path) for d in saved]
		self.project = p
		self.save_project()
		self._update_title()
		logger.log("project created: %s" % path)
		ui.message("Project %s created. Opening the list of project files." % p.name)
		wx.CallLater(500, lambda: self._later(self.on_project_files, "project files"))

	def _later(self, fn, name):
		try:
			fn(None)
		except Exception:
			logger.exc("failed: %s" % name)
			ui.message("An error occurred. Open Help, then View add-on log, for details.")

	def on_project_import(self, evt):
		dlg = wx.FileDialog(self, "Choose the main .tex file of the existing project", wildcard=WILDCARD, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
		try:
			if dlg.ShowModal() != wx.ID_OK:
				return
			path = dlg.GetPath()
		finally:
			dlg.Destroy()
		logger.log("import project: %s" % path)
		try:
			res = importer.import_main(path)
		except importer.ImportProblem as exc:
			wx.MessageBox(str(exc), "Import", wx.OK | wx.ICON_ERROR, self)
			return
		summary = "Found %d part file(s), recognised %d setting(s), and %d preamble line(s) will be kept as they are." % (len(res.files), len(res.recognised), len([l for l in res.options.get("extra_preamble", "").split("\n") if l.strip()]))
		v = dialogs.import_project_dialog(self, path, os.path.basename(res.root) or "Imported project", summary)
		if v is None:
			return
		safe_name = "".join("_" if c in '<>:"/\\|?*' else c for c in v["name"])
		proj_path = os.path.join(res.root, safe_name + ".texproj")
		if os.path.exists(proj_path) and wx.MessageBox("A project file with this name already exists in that folder. Replace it?", "Import", wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
			return
		p = projmod.Project(proj_path)
		p.name = v["name"]
		p.files = list(res.files)
		p.root_dir = res.root
		p.main_file = res.main
		p.engine = res.engine
		if v["mode"] == 0:
			p.options = res.options
			p.body_template = res.body_template if v["keep_body"] else None
			p.use_body_template = bool(v["keep_body"])
			p.build_original = False
		else:
			p.options = projmod.normalize_options({})
			p.body_template = None
			p.build_original = True
		self.project = p
		self.save_project()
		self._update_title()
		logger.log("project imported: %s (%d files)" % (proj_path, len(p.files)))
		ui.message("Project %s imported. The import report is opening." % p.name)
		wx.CallLater(400, lambda: self._later(lambda e: self._import_followup(res), "import report"))

	def _import_followup(self, res):
		dialogs.show_text(self, "Import report", res.report())
		self._open_project_main()
		wx.CallLater(300, lambda: self._later(self.on_project_files, "project files"))

	def on_project_open(self, evt):
		dlg = wx.FileDialog(self, "Open project", wildcard=PROJ_WILDCARD, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
		try:
			if dlg.ShowModal() != wx.ID_OK:
				return
			path = dlg.GetPath()
		finally:
			dlg.Destroy()
		self.load_project(path)

	def on_project_last(self, evt):
		path = self.plugin.cfg.get("last_project")
		if not path or not os.path.isfile(path):
			ui.message("There is no last project")
			return
		self.load_project(path)

	def _need_project(self):
		if self.project:
			return True
		ui.message("No project is open. Use the Project menu to create or open one.")
		return False

	def on_project_files(self, evt):
		if not self._need_project():
			return
		dlg = dialogs.ProjectDialog(self)
		try:
			dlg.ShowModal()
		finally:
			dlg.Destroy()
		self._update_title()
		self.tc.SetFocus()

	def on_project_settings(self, evt):
		if not self._need_project():
			return
		if dialogs.project_settings(self, self.project):
			self.save_project()
			self._update_title()
			ui.message("Project settings saved")

	def on_project_add_current(self, evt):
		if not self._need_project():
			return
		if self.cur < 0:
			return
		if not self.docs[self.cur].path and not self.save_doc_as():
			return
		path = os.path.normpath(self.docs[self.cur].path)
		if path in self.project.files:
			ui.message("%s is already in the project" % os.path.basename(path))
			return
		self.project.files.append(path)
		self.save_project()
		ui.message("%s added as file %d of the project" % (os.path.basename(path), len(self.project.files)))

	def on_settings(self, evt):
		if dialogs.settings_dialog(self, self.plugin.cfg):
			self.plugin.save_cfg()
			self._start_timer()
			ui.message("Settings saved")

	# ------------------------------------------------------------------ building
	def cmd_build(self):
		last = self.plugin.cfg.get("last_build", {})
		v = dialogs.build_dialog(self, self.project, last)
		if v is None:
			return
		self.plugin.cfg["last_build"] = v
		self.plugin.save_cfg()
		self.run_build(v)

	def rebuild_last(self):
		last = self.plugin.cfg.get("last_build")
		if not last:
			self.cmd_build()
			return
		self.run_build(last)

	def _save_for_build(self, whole_project):
		self._store()
		for i, d in enumerate(self.docs):
			if d.path and d.modified:
				if not self.save_doc(i):
					return False
		if not whole_project:
			d = self.docs[self.cur]
			if not d.path:
				ui.message("Please save this document first")
				if not self.save_doc_as():
					return False
		return True

	def run_build(self, v):
		if self.building:
			ui.message("A build is already running. Please wait.")
			return
		fmt_key = builder.FORMATS[v["fmt"]][0]
		whole = bool(v.get("scope") == 1 and self.project and self.project.files)
		if not self._save_for_build(whole):
			return
		cfg = dict(self.plugin.cfg)
		engine_pref = projmod.ENGINES[v.get("engine", 0)]
		if whole:
			proj = copy.copy(self.project)
			if engine_pref != "auto":
				proj.engine = engine_pref
			job = lambda: builder.build_project(proj, fmt_key, cfg)
			what = "project %s" % proj.name
		else:
			d = self.docs[self.cur]
			path, text = d.path, d.text
			job = lambda: builder.build_current_file(path, text, fmt_key, engine_pref, cfg)
			what = d.name()

		def worker():
			try:
				res = job()
			except Exception as exc:  # never let a thread die silently
				res = builder.BuildResult()
				res.message = "Unexpected error: %s" % exc
				res.log = traceback.format_exc()
			wx.CallAfter(self._build_done, res, v)

		self.building = True
		logger.log("build start: %s as %s" % (what, fmt_key))
		self._beep(500, 80)
		ui.message("Building %s as %s. Please wait." % (what, builder.FORMAT_BY_KEY[fmt_key][1].split(" (")[0]))
		self._tick = wx.CallLater(15000, self._still_building)
		threading.Thread(target=worker, daemon=True).start()

	def _beep(self, freq, dur):
		if self.plugin.cfg.get("beeps", True):
			tones.beep(freq, dur)

	def _still_building(self):
		if self.building:
			if self.plugin.cfg.get("reminders", True):
				ui.message("Still building")
			self._tick = wx.CallLater(15000, self._still_building)

	def _build_done(self, res, v):
		self.building = False
		if self._tick:
			self._tick.Stop()
		logger.log("build finished: ok=%s %s | %s" % (res.ok, res.message, "; ".join(i.describe() for i in res.errors()[:5])))
		self.last_result = res
		if res.ok:
			self._beep(880, 120)
			warns = len(res.warnings())
			msg = "Build finished. %s" % os.path.basename(res.output)
			if warns:
				msg += ". %d warnings, press F7 to see them" % warns
			for n in res.notes:
				msg += ". " + n
			self.last_output = res.output
			ui.message(msg)
			if v.get("open_after", True):
				self.open_output()
			return
		self._beep(220, 300)
		errs = res.errors()
		msg = res.message
		for n in res.notes:
			msg += " " + n
		if errs:
			msg += " First problem: %s. The list of problems is opening." % errs[0].describe()
		ui.message(msg)
		if errs:
			wx.CallAfter(self.cmd_errors)
		elif res.log:
			wx.CallAfter(self.cmd_log)

	def open_output(self):
		if not self.last_output or not os.path.isfile(self.last_output):
			ui.message("There is no result file yet. Build first.")
			return
		try:
			os.startfile(self.last_output)
		except (OSError, AttributeError) as exc:
			ui.message("Could not open the file: %s" % exc)

	def cmd_errors(self):
		res = self.last_result
		if res is None:
			ui.message("No build has been run yet")
			return
		issues = res.errors() + res.warnings()
		if not issues:
			ui.message("The last build had no errors or warnings")
			return
		items = [(i.describe(), i) for i in issues[:300]]
		r = dialogs.choose(self, "Errors and warnings (%d errors, %d warnings)" % (len(res.errors()), len(res.warnings())), items,
			prompt="&Filter:", extra_buttons=[("Show full &log", lambda d: dialogs.show_text(d, "Build log", self._log_text()))])
		if r is not None:
			self.goto_issue(r)

	def _log_text(self):
		res = self.last_result
		if res is None:
			return "No build has been run yet."
		head = [res.message]
		head += res.notes
		for i in res.errors()[:20]:
			head.append(i.describe())
		return "\n".join(head) + "\n\n" + (res.log or "")

	def cmd_log(self):
		if self.last_result is None:
			ui.message("No build has been run yet")
			return
		dialogs.show_text(self, "Build log", self._log_text())
		self.tc.SetFocus()

	def goto_issue(self, issue):
		res = self.last_result
		path, line = None, issue.line
		fname = os.path.basename(issue.file) if issue.file else None
		if fname == "main.tex":
			ui.message("This problem is in the generated main file, usually caused by the project settings or extra preamble")
			return
		if fname and fname in res.mapping:
			path = res.mapping[fname]
			if line:
				line += res.offsets.get(fname, 0)
		elif not fname:
			cands = [p for k, p in res.mapping.items() if k != "main.tex"]
			if len(cands) == 1:
				path = cands[0]
				if line:
					line += res.offsets.get(os.path.basename(path), 0)
		if not path:
			ui.message("Cannot tell which file this belongs to")
			return
		self.open_path(path)
		if line:
			txt = self._goto_line(line - 1)
			ui.message("%s line %d: %s" % (os.path.basename(path), line, txt.strip()))

	# ------------------------------------------------------------------ crash recovery
	def _start_timer(self):
		try:
			secs = int(self.plugin.cfg.get("autosave_seconds", 15))
		except (TypeError, ValueError):
			secs = 15
		if self.timer is None:
			self.timer = wx.Timer(self)
			self.Bind(wx.EVT_TIMER, self._on_timer, self.timer)
		self.timer.Stop()
		if secs > 0:
			self.timer.Start(secs * 1000)

	def _on_timer(self, evt):
		self.autosave_now()

	def autosave_now(self):
		"""Copy unsaved documents to the recovery folder (used by the timer and when NVDA exits)."""
		try:
			self._store()
			base = self.plugin.cfg_dir()
			for d in self.docs:
				if d.modified or (not d.path and d.text.strip()):
					if d.auto_text != d.text:
						recovery.save(base, d.uid, d.path, d.text, d.caret)
						d.auto_text = d.text
				else:
					recovery.remove(base, d.uid)
					d.auto_text = None
		except Exception:
			pass

	def offer_recovery(self):
		base = self.plugin.cfg_dir()
		mine = set(d.uid for d in self.docs)
		entries = [e for e in recovery.pending(base) if e["uid"] not in mine]
		if not entries:
			return
		names = ", ".join((os.path.basename(e["path"]) if e.get("path") else "Untitled") for e in entries[:8])
		dlg = wx.MessageDialog(
			self,
			"LaTeX Builder found %d document(s) with unsaved changes from an earlier session, for example after a crash: %s.\n\nRecover them now?" % (len(entries), names),
			"Recover unsaved work", wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
		)
		dlg.SetYesNoCancelLabels("&Recover", "&Discard", "&Ask me next time")
		try:
			r = dlg.ShowModal()
		finally:
			dlg.Destroy()
		if r == wx.ID_CANCEL:
			return
		if r == wx.ID_NO:
			for e in entries:
				recovery.remove(base, e["uid"])
			ui.message("Unsaved work discarded")
			return
		first = None
		for e in entries:
			recovery.remove(base, e["uid"])
			doc = Doc(e.get("path") or None, e["text"], True)
			doc.caret = int(e.get("caret", 0))
			if len(self.docs) == 1 and not self.docs[0].path and not self.docs[0].text and not self.tc.GetValue() and not self.tc.IsModified():
				self.docs[0] = doc
				self.cur = -1
				idx = 0
			else:
				self._store()
				self.docs.append(doc)
				idx = len(self.docs) - 1
			if first is None:
				first = idx
		self._show(first, announce=False)
		ui.message("%d document(s) recovered. They are marked as modified; save them to keep the changes." % len(entries))

	# ------------------------------------------------------------------ view
	def _view_font(self):
		size = int(self.plugin.cfg.get("editor_font_size", 12))
		face = self.plugin.cfg.get("editor_font_face", "")
		return wx.Font(size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, face)

	def _apply_view(self, preserve=True):
		"""Apply the editor font, size and colours chosen in the View menu."""
		try:
			tc = self.tc
			mod = tc.IsModified()
			font = self._view_font()
			theme = dict((t[0], t) for t in THEMES).get(self.plugin.cfg.get("theme", "default"), THEMES[0])
			if theme[2] is None:
				fg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
				bg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
			else:
				fg, bg = wx.Colour(*theme[2]), wx.Colour(*theme[3])
			tc.SetFont(font)
			tc.SetBackgroundColour(bg)
			tc.SetForegroundColour(fg)
			attr = wx.TextAttr(fg, bg, font)
			tc.SetDefaultStyle(attr)
			tc.SetStyle(0, tc.GetLastPosition(), attr)
			tc.Refresh()
			if preserve and not mod:
				tc.DiscardEdits()
		except Exception:
			logger.exc("apply view failed")

	def _zoom(self, delta):
		cfg = self.plugin.cfg
		size = 12 if delta == 0 else max(8, min(72, int(cfg.get("editor_font_size", 12)) + delta))
		cfg["editor_font_size"] = size
		self.plugin.save_cfg()
		self._apply_view()
		ui.message("Text size %d points" % size)

	def on_editor_font(self, evt):
		cfg = self.plugin.cfg
		r = dialogs.editor_font_dialog(self, cfg.get("editor_font_face", ""), cfg.get("editor_font_size", 12))
		if r is None:
			return
		cfg["editor_font_face"], cfg["editor_font_size"] = r
		self.plugin.save_cfg()
		self._apply_view()
		ui.message("Editor font: %s, %d points" % (r[0] or "system default", r[1]))

	def on_theme(self, evt):
		cur = self.plugin.cfg.get("theme", "default")
		items = [(t[1], t[0]) for t in THEMES]
		initial = [t[0] for t in THEMES].index(cur) if cur in [t[0] for t in THEMES] else 0
		r = dialogs.choose(self, "Colour theme", items, show_filter=False, initial=initial)
		if r is None:
			return
		self.plugin.cfg["theme"] = r
		self.plugin.save_cfg()
		self._apply_view()
		ui.message("Colour theme: %s" % dict((t[0], t[1]) for t in THEMES)[r])

	def on_speech_options(self, evt):
		if dialogs.speech_options(self, self.plugin.cfg):
			self.plugin.save_cfg()
			ui.message("Speech and sound options saved")

	def on_statistics(self, evt):
		text = self._text()
		st = texparse.statistics(text)
		parts = ["%d lines, %d words, %d characters" % (st["lines"], st["words"], st["characters"])]
		heads = [(k, st["headings"][k]) for k in texparse.LEVELS if k in st["headings"]]
		if heads:
			parts.append(", ".join("%d %s%s" % (n, k, "" if n == 1 else "s") for k, n in heads))
		else:
			parts.append("no headings")
		parts.append("%d footnotes or endnotes, %d environments" % (st["notes"], st["environments"]))
		sel = self._sel_text()
		if sel.strip():
			parts.append("Selection: %d words, %d characters" % (len(sel.split()), len(sel)))
		ui.message(". ".join(parts))

	def _speak_plain(self, src):
		plain = texparse.plain_text(src)
		if not plain:
			ui.message("Nothing to read here")
			return
		if len(plain) > 4000:
			plain = plain[:4000] + " ... The text was shortened."
		ui.message(plain)

	def on_read_section(self, evt):
		sel = self._sel_text()
		if sel.strip():
			self._speak_plain(sel)
			return
		lines = self._text().split("\n")
		a, b = texparse.section_range(lines, self._cur_line())
		self._speak_plain("\n".join(lines[a:b]))

	def on_read_paragraph(self, evt):
		lines = self._text().split("\n")
		a, b = texparse.paragraph_range(lines, self._cur_line())
		self._speak_plain("\n".join(lines[a:b]))

	def on_read_line(self, evt):
		lines = self._text().split("\n")
		self._speak_plain(lines[self._cur_line()])

	# ------------------------------------------------------------------ packages
	def packages_in_use(self):
		names = snippets.used_packages(self._text()) if self.cur >= 0 else []
		if self.project:
			o = projmod.normalize_options(self.project.options)
			names += snippets.used_packages(o["extra_preamble"])
			names += [n for flag, n in (("amsmath", "amsmath"), ("graphicx", "graphicx"), ("hyperref", "hyperref")) if o[flag]]
			if o["use_geometry"] or o["geometry_raw"]:
				names.append("geometry")
			if projmod.needs_xelatex(o):
				names.append("fontspec")
			if o["use_polyglossia"] and o["language"] != "English":
				names.append("polyglossia")
			if str(o["spacing"]).strip() not in ("", "1"):
				names.append("setspace")
		out = []
		for n in names:
			if n not in out:
				out.append(n)
		return out

	def add_package(self, name, options=""):
		"""Add \\usepackage{name} where it belongs. Returns a sentence for NVDA."""
		text = self._text()
		if snippets.package_insertion(text, name, options) is None and re.search(r"^[ \t]*\\begin\{document\}", text, re.M):
			return "%s is already loaded in this document." % name
		m = re.search(r"^[ \t]*\\begin\{document\}", text, re.M)
		line = "\\usepackage%s{%s}\n" % ("[%s]" % options if options else "", name)
		if m:
			self._insert_at_idx(m.start(), line)
			return "Added a use package line for %s to the preamble of this document." % name
		if self.project:
			o = projmod.normalize_options(self.project.options)
			if name in snippets.used_packages(o["extra_preamble"]):
				return "%s is already in the extra preamble of the project." % name
			extra = o["extra_preamble"]
			o["extra_preamble"] = (extra + ("\n" if extra and not extra.endswith("\n") else "") + line.rstrip("\n"))
			self.project.options = o
			self.save_project()
			return "This file has no preamble, so %s was added to the extra preamble of the project." % name
		self._insert_text(line, block=True)
		return "Inserted a use package line for %s at the caret. Move it above begin document." % name

	def act_packages(self, snip):
		dlg = dialogs.PackageManagerDialog(self)
		try:
			dlg.ShowModal()
		finally:
			dlg.alive = False
			dlg.Destroy()
		self.tc.SetFocus()

	# ------------------------------------------------------------------ logs
	def _diagnostics(self):
		import platform
		out = ["LaTeX Builder 1.6.0", "Python %s, %s" % (platform.python_version(), platform.platform())]
		try:
			out.append("wxPython %s" % wx.version())
		except Exception:
			pass
		try:
			import buildVersion
			out.append("NVDA %s" % buildVersion.version)
		except Exception:
			pass
		cfg = self.plugin.cfg
		out.append("LaTeX: %s" % (builder.find_tool("pdflatex", os.path.join(cfg.get("latex_dir", ""), "pdflatex.exe") if cfg.get("latex_dir") else "") or "not found"))
		out.append("XeLaTeX: %s" % (builder.find_tool("xelatex") or "not found"))
		out.append("Pandoc: %s" % (builder.find_tool("pandoc", cfg.get("pandoc_path", "")) or "not found"))
		out.append("Open documents: %d, project: %s" % (len(self.docs), self.project.name if self.project else "none"))
		return "\n".join(out)

	def _log_report(self):
		return "System information\n%s\n\nAdd-on log (newest at the end)\n%s" % (self._diagnostics(), logger.read_tail(400))

	def on_view_log(self, evt):
		dialogs.show_text(self, "Add-on log (newest at the end)", self._log_report(), caret_end=True)
		self.tc.SetFocus()

	def on_copy_log(self, evt):
		text = self._log_report()
		if wx.TheClipboard.Open():
			try:
				wx.TheClipboard.SetData(wx.TextDataObject(text))
			finally:
				wx.TheClipboard.Close()
			ui.message("The add-on log was copied to the clipboard")
		else:
			ui.message("Could not open the clipboard")

	def on_nvda_log(self, evt):
		dialogs.show_text(self, "NVDA log entries about LaTeX Builder", logger.nvda_log_entries(), caret_end=True)
		self.tc.SetFocus()

	def on_open_log_folder(self, evt):
		p = logger.path()
		if not p:
			ui.message("There is no log yet")
			return
		try:
			os.startfile(os.path.dirname(p))
		except (OSError, AttributeError) as exc:
			ui.message("Could not open the folder: %s" % exc)

	def on_clear_log(self, evt):
		if wx.MessageBox("Delete the add-on log?", "LaTeX Builder", wx.YES_NO | wx.ICON_QUESTION, self) == wx.YES:
			logger.clear()
			ui.message("The add-on log was cleared")

	# ------------------------------------------------------------------ help
	def on_manual(self, evt):
		dialogs.show_manual(self)
		self.tc.SetFocus()

	def on_manual_browser(self, evt):
		if dialogs.open_manual_in_browser():
			ui.message("The user manual is opening in your web browser.")
		else:
			ui.message("The manual file for the browser was not found. Use the manual in a window instead.")

	def on_shortcuts(self, evt):
		lines = ["LaTeX Builder keyboard shortcuts and commands", "(Press Control K to search all commands by name.)", ""]
		for label, accel in self.shortcuts:
			lines.append("%s: %s" % (label, accel) if accel else label)
		dialogs.show_text(self, "Keyboard shortcuts", "\n".join(lines))

	def on_about(self, evt):
		dialogs.show_text(self, "About", "LaTeX Builder for NVDA\nAn accessible LaTeX editor, navigator and builder.\nUses MiKTeX and Pandoc installed on this computer.")
