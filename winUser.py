# -*- coding: utf-8 -*-
"""Replacement for the one function of NVDA's ``winUser`` module that LaTeX Builder uses."""

import ctypes
import sys


def setForegroundWindow(hwnd):
	if sys.platform == "win32":
		ctypes.windll.user32.SetForegroundWindow(hwnd)
