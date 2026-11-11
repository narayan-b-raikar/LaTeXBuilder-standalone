# -*- coding: utf-8 -*-
"""Replacement for NVDA's ``ui`` module: speaks through a running screen reader when possible."""

import ctypes
import os
import sys

sink = None  # optional callable(text), for example the status bar of the window
_backend = None
_tried = False
_ao = None
_dll = None


def _base_dirs():
	dirs = [os.path.dirname(os.path.abspath(sys.argv[0])), os.getcwd()]
	if getattr(sys, "_MEIPASS", None):
		dirs.insert(0, sys._MEIPASS)
	return dirs


def _init():
	global _tried, _ao, _dll, _backend
	if _tried:
		return
	_tried = True
	try:
		import accessible_output2.outputs.auto as auto
		_ao = auto.Auto()
		_backend = "accessible_output2"
		return
	except Exception:
		_ao = None
	if sys.platform == "win32":
		names = ["nvdaControllerClient64.dll" if ctypes.sizeof(ctypes.c_void_p) == 8 else "nvdaControllerClient32.dll", "nvdaControllerClient.dll"]
		for d in _base_dirs():
			for n in names:
				p = os.path.join(d, n)
				if os.path.isfile(p):
					try:
						_dll = ctypes.windll.LoadLibrary(p)
						_backend = "nvdaControllerClient"
						return
					except OSError:
						_dll = None


def message(text, *args, **kwargs):
	"""Speak ``text`` (and show it through ``sink``)."""
	if not text:
		return
	text = str(text)
	if sink:
		try:
			sink(text)
		except Exception:
			pass
	_init()
	try:
		if _ao is not None:
			_ao.speak(text, interrupt=True)
		elif _dll is not None and _dll.nvdaController_testIfRunning() == 0:
			_dll.nvdaController_cancelSpeech()
			_dll.nvdaController_speakText(ctypes.c_wchar_p(text))
	except Exception:
		pass
