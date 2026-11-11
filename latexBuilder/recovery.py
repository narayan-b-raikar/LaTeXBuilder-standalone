# -*- coding: utf-8 -*-
"""Crash recovery: unsaved documents are copied to a recovery folder every few seconds."""

import io
import json
import os
import time

FOLDER_NAME = "latexBuilder-recovery"


def folder(base_dir):
	return os.path.join(base_dir, FOLDER_NAME)


def save(base_dir, uid, path, text, caret=0):
	d = folder(base_dir)
	os.makedirs(d, exist_ok=True)
	data = {"uid": uid, "path": path, "text": text, "caret": caret, "time": time.time()}
	target = os.path.join(d, uid + ".json")
	tmp = target + ".tmp"
	with io.open(tmp, "w", encoding="utf-8") as fh:
		json.dump(data, fh, ensure_ascii=False)
	os.replace(tmp, target)


def remove(base_dir, uid):
	try:
		os.remove(os.path.join(folder(base_dir), uid + ".json"))
	except OSError:
		pass


def pending(base_dir):
	"""Recovery entries found on disk, oldest first."""
	d = folder(base_dir)
	out = []
	try:
		names = os.listdir(d)
	except OSError:
		return out
	for n in names:
		if not n.endswith(".json"):
			continue
		try:
			with io.open(os.path.join(d, n), "r", encoding="utf-8") as fh:
				e = json.load(fh)
			if isinstance(e.get("text"), str) and e.get("uid"):
				out.append(e)
		except (OSError, ValueError):
			continue
	out.sort(key=lambda e: e.get("time", 0))
	return out
