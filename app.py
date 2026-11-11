# -*- coding: utf-8 -*-
"""LaTeX Builder, stand-alone version (no NVDA needed).

Run:  python app.py [file.tex | project.texproj ...]
"""

import json
import os
import sys

import wx

import ui
from latexBuilder import logger
from latexBuilder.editor import Doc, EditorFrame

DEFAULT_CONFIG = {
	"passes": 2, "auto_install": True, "timeout": 600, "latex_dir": "", "pandoc_path": "",
	"autosave_seconds": 15, "confirm": "full", "beeps": True, "reminders": True,
	"editor_font_face": "", "editor_font_size": 12, "theme": "default", "word_wrap": True, "shortcuts": {},
	"csl_path": "", "references_title": "References", "reference_docx": "", "word_numbering": True, "project_open": "main",
}


class Host(object):
	"""What the editor window expects from the program that hosts it."""

	def __init__(self):
		base = os.environ.get("APPDATA") or os.path.expanduser("~")
		self.dir = os.path.join(base, "LaTeXBuilder")
		os.makedirs(self.dir, exist_ok=True)
		self.cfg = dict(DEFAULT_CONFIG)
		try:
			with open(self._path(), "r", encoding="utf-8") as fh:
				self.cfg.update(json.load(fh))
		except (IOError, OSError, ValueError):
			pass

	def _path(self):
		return os.path.join(self.dir, "settings.json")

	def cfg_dir(self):
		return self.dir

	def save_cfg(self):
		try:
			with open(self._path(), "w", encoding="utf-8") as fh:
				json.dump(self.cfg, fh, ensure_ascii=False, indent=2)
		except (IOError, OSError):
			logger.exc("could not save settings")

	def frame_closed(self):
		pass


def main(argv):
	app = wx.App(False)
	host = Host()
	logger.init(host.dir)
	logger.log("LaTeX Builder stand-alone started")
	frame = EditorFrame(host)
	frame.CreateStatusBar()

	def show_status(text):
		try:
			frame.SetStatusText(text[:200])
		except Exception:
			pass

	ui.sink = show_status
	frame.docs.append(Doc())
	frame.Show()
	frame._show(0, announce=False)
	for arg in argv[1:]:
		if not os.path.isfile(arg):
			continue
		if arg.lower().endswith(".texproj"):
			frame.load_project(os.path.abspath(arg))
		else:
			frame.open_path(os.path.abspath(arg))
	ui.message("LaTeX Builder. Press Control K to search all commands, F1 for the list of shortcuts.")
	wx.CallAfter(frame.offer_recovery)
	frame.Raise()
	frame.tc.SetFocus()
	app.MainLoop()
	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv))
