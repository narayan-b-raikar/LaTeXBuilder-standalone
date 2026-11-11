# -*- coding: utf-8 -*-
"""A small add-on log, so problems (and freezes) can be traced. No NVDA imports."""

import io
import os
import re
import tempfile
import time
import traceback

_path = None
MAX_BYTES = 400 * 1024


def init(base_dir):
	global _path
	_path = os.path.join(base_dir, "latexBuilder.log")
	try:
		if os.path.isfile(_path) and os.path.getsize(_path) > MAX_BYTES:
			os.replace(_path, _path + ".old")
	except OSError:
		pass


def path():
	return _path


def log(msg):
	if not _path:
		return
	try:
		with io.open(_path, "a", encoding="utf-8") as fh:
			fh.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
	except OSError:
		pass


def exc(msg=""):
	log("%s\n%s" % (msg, traceback.format_exc()))


def read_tail(max_lines=400):
	if not _path or not os.path.isfile(_path):
		return "The add-on log is empty."
	try:
		with io.open(_path, "r", encoding="utf-8", errors="replace") as fh:
			lines = fh.read().splitlines()
	except OSError as e:
		return "Could not read the log: %s" % e
	return "\n".join(lines[-max_lines:]) or "The add-on log is empty."


def clear():
	if _path and os.path.isfile(_path):
		try:
			os.remove(_path)
		except OSError:
			pass


_LEVEL_RE = re.compile(r"^(DEBUG|IO|INFO|DEBUGWARNING|WARNING|ERROR|CRITICAL)\b")


def nvda_log_candidates():
	out = []
	try:
		import globalVars
		name = getattr(globalVars.appArgs, "logFileName", None)
		if name:
			out.append(name)
	except Exception:
		pass
	tmp = tempfile.gettempdir()
	out += [os.path.join(tmp, "nvda.log"), os.path.join(tmp, "nvda-old.log")]
	return [p for p in out if p and os.path.isfile(p)]


def nvda_log_entries(keywords=("latexBuilder", "LaTeX Builder"), max_entries=30):
	"""Entries of NVDA's own log that mention this add-on (errors, tracebacks)."""
	found = []
	for p in nvda_log_candidates():
		try:
			with io.open(p, "r", encoding="utf-8", errors="replace") as fh:
				lines = fh.read().splitlines()
		except OSError:
			continue
		entries, cur = [], []
		for ln in lines:
			if _LEVEL_RE.match(ln) and cur:
				entries.append(cur)
				cur = []
			cur.append(ln)
		if cur:
			entries.append(cur)
		found += ["\n".join(e) for e in entries if any(k in "\n".join(e) for k in keywords)]
		if found:
			break
	if not found:
		return "No entries about LaTeX Builder were found in NVDA's log.\nTo read NVDA's whole log, press NVDA+F1."
	return "\n\n".join(found[-max_entries:])
