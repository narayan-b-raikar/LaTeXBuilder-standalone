# -*- coding: utf-8 -*-
"""Replacement for NVDA's ``tones`` module."""

try:
	import winsound
except ImportError:  # not Windows
	winsound = None


def beep(hz, length, *args, **kwargs):
	if winsound is None:
		return
	try:
		winsound.Beep(int(max(37, min(32767, hz))), int(max(1, length)))
	except Exception:
		pass
