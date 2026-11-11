# -*- coding: utf-8 -*-
"""Runs MiKTeX (LaTeX engines) and Pandoc. No NVDA / wx imports."""

import os
import re
import shutil
import subprocess
import sys

from . import project as projmod
from . import texparse

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# (key, label, kind, extension, pandoc writer)
FORMATS = [
	("pdf", "PDF (using LaTeX / MiKTeX)", "latex", ".pdf", None),
	("docx", "Word document .docx (using Pandoc)", "pandoc", ".docx", "docx"),
	("odt", "OpenDocument text .odt (using Pandoc)", "pandoc", ".odt", "odt"),
	("rtf", "Rich text .rtf (using Pandoc)", "pandoc", ".rtf", "rtf"),
	("html", "Web page .html (using Pandoc)", "pandoc", ".html", "html5"),
	("epub", "E-book .epub (using Pandoc)", "pandoc", ".epub", "epub3"),
	("md", "Markdown .md (using Pandoc)", "pandoc", ".md", "markdown"),
	("txt", "Plain text .txt (using Pandoc)", "pandoc", ".txt", "plain"),
]
FORMAT_BY_KEY = dict((f[0], f) for f in FORMATS)


def _candidate_dirs(tool):
	local = os.environ.get("LOCALAPPDATA", "")
	pf = os.environ.get("ProgramFiles", r"C:\Program Files")
	pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
	if tool == "pandoc":
		return [
			os.path.join(local, "Pandoc"),
			os.path.join(pf, "Pandoc"),
			os.path.join(pf86, "Pandoc"),
		]
	return [
		os.path.join(local, "Programs", "MiKTeX", "miktex", "bin", "x64"),
		os.path.join(local, "Programs", "MiKTeX", "miktex", "bin"),
		os.path.join(pf, "MiKTeX", "miktex", "bin", "x64"),
		os.path.join(pf, "MiKTeX", "miktex", "bin"),
		os.path.join(pf86, "MiKTeX", "miktex", "bin"),
		r"C:\texlive\2025\bin\windows",
		r"C:\texlive\2024\bin\windows",
		r"C:\texlive\2023\bin\windows",
	]


def find_tool(name, configured=""):
	"""Return full path of an executable or '' if not found."""
	if configured and os.path.isfile(configured):
		return configured
	found = shutil.which(name)
	if found:
		return found
	exe = name + (".exe" if sys.platform == "win32" else "")
	for d in _candidate_dirs("pandoc" if name == "pandoc" else "latex"):
		cand = os.path.join(d, exe)
		if os.path.isfile(cand):
			return cand
	return ""


_miktex_cache = {}


def is_miktex(exe):
	if exe in _miktex_cache:
		return _miktex_cache[exe]
	result = False
	try:
		out = subprocess.run(
			[exe, "--version"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
			creationflags=CREATE_NO_WINDOW, timeout=60,
		).stdout.decode("utf-8", "replace")
		result = "miktex" in out.lower()
	except Exception:
		result = False
	_miktex_cache[exe] = result
	return result


def _env_with_tool_dir(exe, extra_dirs=()):
	env = dict(os.environ)
	env["PATH"] = os.path.dirname(exe) + os.pathsep + env.get("PATH", "")
	if extra_dirs:
		joined = os.pathsep.join(list(extra_dirs)) + os.pathsep
		if not is_miktex(exe):
			env["TEXINPUTS"] = joined
		env["BIBINPUTS"] = joined
		env["BSTINPUTS"] = joined
	return env


def _run_bibliography(base, outdir, cfg, env, extra_dirs, latex_exe):
	"""Run biber or bibtex when the document asks for a bibliography. Returns log text or None."""
	bcf = os.path.join(outdir, base + ".bcf")
	aux = os.path.join(outdir, base + ".aux")
	args = None
	name = ""
	if os.path.isfile(bcf):
		tool = find_tool("biber", "")
		name = "biber"
		if tool:
			args = [tool] + ["--input-directory=" + d for d in extra_dirs] + [base]
	elif os.path.isfile(aux):
		try:
			with open(aux, encoding="utf-8", errors="replace") as fh:
				wants = "\\bibdata" in fh.read()
		except OSError:
			wants = False
		if wants:
			name = "bibtex"
			tool = find_tool("bibtex", "")
			if tool:
				args = [tool]
				if is_miktex(latex_exe):
					args += ["-include-directory=" + d for d in extra_dirs]
				args.append(base)
	if not name:
		return None
	if args is None:
		return "===== %s =====\n%s was not found, so the bibliography was not built." % (name, name)
	try:
		_code, text = _run(args, outdir, env, int(cfg.get("timeout", 600)))
	except (subprocess.TimeoutExpired, OSError) as exc:
		return "===== %s =====\n%s failed: %s" % (name, name, exc)
	return "===== %s =====\n%s" % (name, text)


def choose_engine(preferred, tex_text, opts):
	if preferred and preferred != "auto":
		return preferred
	if projmod.needs_xelatex(opts or {}) or any(k in tex_text for k in ("fontspec", "polyglossia", "unicode-math")):
		return "xelatex"
	return "pdflatex"


class BuildResult(object):
	def __init__(self):
		self.ok = False
		self.output = ""
		self.log = ""
		self.issues = []
		self.mapping = {}
		self.offsets = {}
		self.notes = []
		self.message = ""

	def errors(self):
		return [i for i in self.issues if i.severity == "error"]

	def warnings(self):
		return [i for i in self.issues if i.severity == "warning"]


def _run(args, cwd, env, timeout):
	proc = subprocess.run(
		args, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
		creationflags=CREATE_NO_WINDOW, timeout=timeout,
	)
	return proc.returncode, proc.stdout.decode("utf-8", "replace")


def run_latex(main_tex, engine, cfg, workdir, outdir, mapping=None, extra_dirs=()):
	"""Compile ``main_tex`` to PDF. Returns BuildResult."""
	res = BuildResult()
	res.mapping = dict(mapping or {})
	configured = ""
	if cfg.get("latex_dir"):
		configured = os.path.join(cfg["latex_dir"], engine + (".exe" if sys.platform == "win32" else ""))
	exe = find_tool(engine, configured)
	if not exe:
		res.message = "Could not find %s. Install MiKTeX or set the path in Settings." % engine
		return res
	miktex = is_miktex(exe)
	passes = max(1, int(cfg.get("passes", 2)))
	base = os.path.splitext(os.path.basename(main_tex))[0]
	logs = []
	os.makedirs(outdir, exist_ok=True)
	env = _env_with_tool_dir(exe, extra_dirs)
	n = 0
	need = passes
	code = 0
	while n < need:
		args = [exe, "-interaction=nonstopmode", "-file-line-error", "-output-directory=" + outdir]
		if miktex:
			args.append("-enable-installer" if cfg.get("auto_install", True) else "-disable-installer")
			for d in extra_dirs:
				args.append("-include-directory=" + d)
		args.append(main_tex)
		try:
			code, text = _run(args, workdir, env, int(cfg.get("timeout", 600)))
		except subprocess.TimeoutExpired:
			res.log = "\n".join(logs)
			res.message = "The LaTeX run took too long and was stopped. If MiKTeX is waiting to install a package, run MiKTeX Console once."
			return res
		except OSError as exc:
			res.message = "Could not start %s: %s" % (engine, exc)
			return res
		n += 1
		logs.append("===== Pass %d (%s) =====\n%s" % (n, engine, text))
		if code != 0:
			break
		if n == 1:
			bib = _run_bibliography(base, outdir, cfg, env, extra_dirs, exe)
			if bib:
				logs.append(bib)
				need = max(need, 3)
	res.log = "\n".join(logs)
	res.issues = texparse.parse_log(logs[-1])
	pdf = os.path.join(outdir, base + ".pdf")
	res.ok = code == 0 and os.path.isfile(pdf)
	if res.ok:
		res.output = pdf
		res.message = "PDF created."
	else:
		res.message = "LaTeX reported %d error(s)." % max(1, len(res.errors()))
	return res


_PANDOC_MACROS = r"""\newcommand{\endnote}[1]{\footnote{#1}}
\newcommand{\theendnotes}{}
"""

_PANDOC_LUA = """local word = {center = "LB Center", flushright = "LB Right", flushleft = "LB Left", justify = "LB Justify"}
local css = {center = "center", flushright = "right", flushleft = "left", justify = "justify"}
function Div(el)
  for _, c in ipairs(el.classes) do
    if word[c] then
      if FORMAT:match("html") or FORMAT:match("epub") then
        el.attributes["style"] = "text-align: " .. css[c]
      else
        el.attributes["custom-style"] = word[c]
      end
      return el
    end
  end
end
"""

_CITE_RE = re.compile(r"\\(?:cite|citep|citet|citealp|citeauthor|citeyear|parencite|textcite|autocite|footcite|smartcite|nocite)\*?\b")


def pandoc_version(exe):
	try:
		_code, out = _run([exe, "--version"], None, dict(os.environ), 60)
	except Exception:
		return (0,)
	m = re.search(r"pandoc(?:\.exe)?\s+(\d+(?:\.\d+)*)", out)
	return tuple(int(x) for x in m.group(1).split(".")) if m else (0,)


def find_bibliographies(text, dirs):
	"""Paths of .bib files named by \bibliography{...} or \addbibresource{...}."""
	names = []
	for m in re.finditer(r"\\bibliography\{([^}]*)\}", text):
		names += [n.strip() for n in m.group(1).split(",") if n.strip()]
	for m in re.finditer(r"\\addbibresource(?:\[[^\]]*\])?\{([^}]*)\}", text):
		names.append(m.group(1).strip())
	paths = []
	for n in names:
		if not n.lower().endswith(".bib"):
			n += ".bib"
		if os.path.isabs(n) and os.path.isfile(n):
			paths.append(n)
			continue
		for d in dirs:
			cand = os.path.join(d, n)
			if d and os.path.isfile(cand):
				paths.append(cand)
				break
	return paths


def _patch_docx_styles(xml, font, size):
	for sid, jc in (("LBCenter", "center"), ("LBRight", "right"), ("LBLeft", "left"), ("LBJustify", "both")):
		xml = re.sub(r'(<w:style [^>]*w:styleId="%s"[^>]*>.*?<w:qFormat\s*/>)' % sid,
			lambda m, jc=jc: m.group(1) + '<w:pPr><w:jc w:val="%s"/></w:pPr>' % jc, xml, count=1, flags=re.S)
	if font:
		f = font.replace("&", "&amp;").replace('"', "&quot;")
		rf = '<w:rFonts w:ascii="%s" w:hAnsi="%s" w:cs="%s" w:eastAsia="%s"/>' % (f, f, f, f)
		xml = re.sub(r"<w:rFonts[^>]*Theme[^>]*/>", rf, xml)
	if size:
		half = str(int(size) * 2)
		xml = re.sub(r"(<w:rPrDefault>.*?)<w:sz w:val=\"\d+\"\s*/>(.*?)<w:szCs w:val=\"\d+\"\s*/>",
			lambda m: '%s<w:sz w:val="%s"/>%s<w:szCs w:val="%s"/>' % (m.group(1), half, m.group(2), half), xml, count=1, flags=re.S)
	return xml


def docx_postprocess(path, font="", size=""):
	"""Give the Word file real alignment styles and, optionally, the project font and size."""
	import zipfile
	tmp = path + ".tmp"
	with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
		for item in zin.infolist():
			data = zin.read(item.filename)
			if item.filename == "word/styles.xml":
				data = _patch_docx_styles(data.decode("utf-8"), font, size).encode("utf-8")
			zout.writestr(item, data)
	os.replace(tmp, path)


def run_pandoc(source_tex, fmt_key, cfg, workdir, output_path, resource_dirs=(), text="", options=None):
	"""Convert LaTeX with Pandoc. ``text`` is all the LaTeX text (main file and parts) used to detect features."""
	import tempfile
	res = BuildResult()
	exe = find_tool("pandoc", cfg.get("pandoc_path", ""))
	if not exe:
		res.message = "Could not find Pandoc. Install Pandoc or set the path in Settings."
		return res
	ver = pandoc_version(exe)
	fmt = FORMAT_BY_KEY[fmt_key]
	o = projmod.normalize_options(options) if options else None
	tmpdir = tempfile.mkdtemp(prefix="lbpandoc")
	macros = os.path.join(tmpdir, "lb_macros.tex")
	lua = os.path.join(tmpdir, "lb_improve.lua")
	with open(macros, "w", encoding="utf-8") as fh:
		fh.write(_PANDOC_MACROS)
	with open(lua, "w", encoding="utf-8") as fh:
		fh.write(_PANDOC_LUA)
	args = [exe, "-f", "latex", "-t", fmt[4], "-s", "-o", output_path, "--lua-filter=" + lua]
	if "\\tableofcontents" in text:
		args.append("--toc")
	if fmt_key in ("docx", "odt", "html", "epub", "rtf") and cfg.get("word_numbering", True):
		args.append("--number-sections")
	dirs = [d for d in resource_dirs if d]
	if dirs:
		args.append("--resource-path=" + os.pathsep.join(dirs))
	# citations: Pandoc does not read \bibliography by itself
	bibs = find_bibliographies(text, dirs + [workdir])
	if bibs and _CITE_RE.search(text):
		if ver >= (2, 11):
			args.append("--citeproc")
			for b in bibs:
				args.append("--bibliography=" + b)
			csl = cfg.get("csl_path", "")
			if csl and os.path.isfile(csl):
				args.append("--csl=" + csl)
			if ver >= (2, 11):
				args += ["-M", "reference-section-title=" + (cfg.get("references_title", "References") or "References")]
			res.notes.append("Citations were formatted by Pandoc from %s." % ", ".join(os.path.basename(b) for b in bibs))
		else:
			res.notes.append("This Pandoc is too old to format citations. Install Pandoc 2.11 or later.")
	elif _CITE_RE.search(text):
		res.notes.append("The document has citations but no .bib file was found, so Word output shows the keys only.")
	if o:
		code = projmod.LANG_CODES.get(o["language"])
		if code:
			args += ["-M", "lang=" + code]
	ref = cfg.get("reference_docx", "")
	if fmt_key == "docx" and ref and os.path.isfile(ref):
		args.append("--reference-doc=" + ref)
	if fmt_key == "html":
		args.append("--embed-resources" if ver >= (2, 19) else "--self-contained")
		args.append("--mathml")
	args += [macros, source_tex]
	env = dict(os.environ)
	try:
		code, out = _run(args, workdir, env, int(cfg.get("timeout", 600)))
	except subprocess.TimeoutExpired:
		res.message = "Pandoc took too long and was stopped."
		return res
	except OSError as exc:
		res.message = "Could not start Pandoc: %s" % exc
		return res
	finally:
		try:
			import shutil as _sh
			_sh.rmtree(tmpdir, ignore_errors=True)
		except Exception:
			pass
	res.log = "===== Pandoc =====\n" + " ".join(args) + "\n" + out
	res.ok = code == 0 and os.path.isfile(output_path)
	if res.ok:
		res.output = output_path
		res.message = "%s created." % os.path.basename(output_path)
		for ln in out.splitlines():
			if ln.lower().startswith("[warning]"):
				res.issues.append(texparse.LogIssue("warning", ln[9:].strip()))
		if fmt_key == "docx":
			try:
				font = size = ""
				if o and not (ref and os.path.isfile(ref)):
					info = projmod.LANG_BY_NAME[o["language"]]
					font = o["mainfont"].strip() or (info[4] if o["language"] != "English" else "")
					size = o["fontsize"]
				docx_postprocess(output_path, font, size)
			except Exception as exc:
				res.notes.append("The Word file was created, but its styles could not be improved: %s" % exc)
	else:
		first = next((ln for ln in out.splitlines() if ln.strip()), "unknown error")
		res.message = "Pandoc failed: %s" % first
		res.issues.append(texparse.LogIssue("error", first))
	return res


def build_current_file(path, text, fmt_key, engine_pref, cfg):
	"""Build a single .tex file that is saved at ``path`` (text is its current content)."""
	workdir = os.path.dirname(path)
	fmt = FORMAT_BY_KEY[fmt_key]
	if "\\documentclass" not in text:
		# a part file without preamble: wrap it in a temporary one-file project
		tmp = projmod.Project(os.path.join(workdir, "_fragment.texproj"))
		tmp.name = os.path.splitext(os.path.basename(path))[0]
		tmp.files = [path]
		tmp.options["maketitle"] = False
		res = build_project(tmp, fmt_key, cfg)
		res.notes.insert(0, "This file has no \\documentclass, so a default preamble was added for this build.")
		return res
	if fmt[2] == "latex":
		engine = choose_engine(engine_pref, text, {})
		outdir = os.path.join(workdir, "_latexbuild")
		res = run_latex(path, engine, cfg, workdir, outdir, mapping={os.path.basename(path): path})
		if res.ok:
			final = os.path.splitext(path)[0] + ".pdf"
			try:
				shutil.copyfile(res.output, final)
				res.output = final
			except OSError as exc:
				res.notes.append("Could not copy the PDF next to the source: %s" % exc)
		return res
	out = os.path.splitext(path)[0] + fmt[3]
	return run_pandoc(path, fmt_key, cfg, workdir, out, resource_dirs=[workdir], text=text)


def build_project(project, fmt_key, cfg, read=projmod.read_text_file):
	"""Build a whole project (several parts) to the requested format."""
	folder = project.folder()
	build_dir = os.path.join(folder, "build")
	if project.main_file and project.build_original:
		return _build_original(project, fmt_key, cfg, build_dir)
	main_path, mapping, notes, offsets = projmod.prepare_project_build(project, build_dir, read)
	with open(main_path, encoding="utf-8") as fh:
		main_text = fh.read()
	src_dirs = [project.root_dir] if project.root_dir else []
	for f in project.files:
		d = os.path.dirname(f)
		if d and d not in src_dirs:
			src_dirs.append(d)
	fmt = FORMAT_BY_KEY[fmt_key]
	safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in project.name).strip() or "project"
	if fmt[2] == "latex":
		engine = choose_engine(project.engine, main_text, project.options)
		res = run_latex(main_path, engine, cfg, build_dir, build_dir, mapping=mapping, extra_dirs=src_dirs)
		res.offsets = offsets
		if res.ok:
			final = os.path.join(folder, safe + ".pdf")
			try:
				shutil.copyfile(res.output, final)
				res.output = final
			except OSError as exc:
				res.notes.append("Could not copy PDF next to the project: %s" % exc)
	else:
		final = os.path.join(folder, safe + fmt[3])
		alltext = main_text
		for fname in mapping:
			if fname.startswith("part"):
				try:
					alltext += "\n" + projmod.read_text_file(os.path.join(build_dir, fname))
				except OSError:
					pass
		res = run_pandoc(main_path, fmt_key, cfg, build_dir, final, resource_dirs=[build_dir] + src_dirs, text=alltext, options=project.options)
		res.mapping = mapping
		res.offsets = offsets
	res.notes = notes + res.notes
	return res


def _build_original(project, fmt_key, cfg, build_dir):
	"""Compile an imported main file exactly as it is (nothing is generated)."""
	main = project.main_file
	root = project.root_dir or os.path.dirname(main)
	if not os.path.isfile(main):
		res = BuildResult()
		res.message = "The original main file was not found: %s" % main
		return res
	os.makedirs(build_dir, exist_ok=True)
	mapping = {}
	for f in project.files:
		mapping[os.path.basename(f)] = f
		try:
			rel = os.path.relpath(os.path.dirname(f), root)
			if not rel.startswith(".."):
				os.makedirs(os.path.join(build_dir, rel), exist_ok=True)  # \include writes .aux files here
		except ValueError:
			pass
	mapping[os.path.basename(main)] = main
	text = projmod.read_text_file(main)
	fmt = FORMAT_BY_KEY[fmt_key]
	safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in project.name).strip() or "project"
	if fmt[2] == "latex":
		engine = choose_engine(project.engine, text, {})
		res = run_latex(main, engine, cfg, root, build_dir, mapping=mapping, extra_dirs=[root])
		if res.ok:
			final = os.path.join(project.folder(), safe + ".pdf")
			try:
				shutil.copyfile(res.output, final)
				res.output = final
			except OSError as exc:
				res.notes.append("Could not copy the PDF next to the project: %s" % exc)
	else:
		final = os.path.join(project.folder(), safe + fmt[3])
		alltext = text
		for f in project.files:
			try:
				alltext += "\n" + projmod.read_text_file(f)
			except OSError:
				pass
		res = run_pandoc(main, fmt_key, cfg, root, final, resource_dirs=[root], text=alltext)
		res.mapping = mapping
	res.notes.insert(0, "The original main file %s was built as it is." % os.path.basename(main))
	return res


# ---------------------------------------------------------------- LaTeX package tools (MiKTeX / TeX Live)

def _tool_dir_cfg(cfg, name):
	d = cfg.get("latex_dir", "")
	return os.path.join(d, name + (".exe" if sys.platform == "win32" else "")) if d else ""


def package_system(cfg):
	"""Describe the TeX installation: dict(kind, mpm, tlmgr, kpsewhich, latex)."""
	latex = find_tool("pdflatex", _tool_dir_cfg(cfg, "pdflatex"))
	info = {"latex": latex, "kind": "", "mpm": "", "tlmgr": "", "kpsewhich": find_tool("kpsewhich", _tool_dir_cfg(cfg, "kpsewhich"))}
	info["mpm"] = find_tool("mpm", _tool_dir_cfg(cfg, "mpm"))
	info["tlmgr"] = find_tool("tlmgr", "")
	if latex:
		info["kind"] = "miktex" if is_miktex(latex) else "texlive"
	return info


def installed_styles(names, cfg, kind_info=None):
	"""Set of package names (from ``names``) whose .sty file is installed, or None if it cannot be checked."""
	info = kind_info or package_system(cfg)
	exe = info["kpsewhich"]
	if not exe:
		return None
	found = set()
	chunk = 60
	import tempfile
	for i in range(0, len(names), chunk):
		part = names[i:i + chunk]
		try:
			_code, out = _run([exe] + [n + ".sty" for n in part], tempfile.gettempdir(), _env_with_tool_dir(exe), 120)
		except Exception:
			return None
		for ln in out.splitlines():
			ln = ln.strip()
			if ln.lower().endswith(".sty"):
				found.add(os.path.basename(ln)[:-4].lower())
	return found


def mpm_package_list(cfg, info=None):
	"""MiKTeX packages: list of (name, installed True/False/None)."""
	info = info or package_system(cfg)
	if not info["mpm"]:
		return None
	env = _env_with_tool_dir(info["mpm"])
	import tempfile
	try:
		_c, names_out = _run([info["mpm"], "--list-package-names"], tempfile.gettempdir(), env, 300)
	except Exception:
		return None
	names = [ln.strip() for ln in names_out.splitlines() if ln.strip() and " " not in ln.strip()]
	status = {}
	try:
		_c, out = _run([info["mpm"], "--list"], tempfile.gettempdir(), env, 300)
		for ln in out.splitlines():
			t = ln.split()
			if len(t) >= 3 and t[0] in ("i", "-", "I"):
				status[t[-1]] = t[0] in ("i", "I")
	except Exception:
		pass
	return [(n, status.get(n)) for n in names]


def install_package(name, cfg, mpm_name=False, info=None):
	"""Install a package. Returns (ok, log). ``mpm_name`` True means ``name`` is a MiKTeX package name."""
	import tempfile
	info = info or package_system(cfg)
	if info["kind"] == "miktex":
		if mpm_name and info["mpm"]:
			try:
				code, out = _run([info["mpm"], "--install=" + name], tempfile.gettempdir(), _env_with_tool_dir(info["mpm"]), 1200)
			except Exception as exc:
				return False, "Could not run mpm: %s" % exc
			return code == 0, out
		# let MiKTeX fetch whatever provides name.sty by compiling a tiny document
		d = tempfile.mkdtemp(prefix="lbpkg")
		tex = os.path.join(d, "t.tex")
		with open(tex, "w", encoding="utf-8") as fh:
			fh.write("\\documentclass{article}\n\\usepackage{%s}\n\\begin{document}x\\end{document}\n" % name)
		try:
			code, out = _run([info["latex"], "-interaction=nonstopmode", "-enable-installer", "-output-directory=" + d, tex], d, _env_with_tool_dir(info["latex"]), 1200)
		except subprocess.TimeoutExpired:
			return False, "The installation took too long and was stopped."
		except Exception as exc:
			return False, "Could not run LaTeX: %s" % exc
		ok = bool(installed_styles([name], cfg, info) and name.lower() in installed_styles([name], cfg, info))
		return ok, out
	if info["tlmgr"]:
		env = _env_with_tool_dir(info["tlmgr"])
		try:
			_c, found = _run([info["tlmgr"], "search", "--file", "--global", "/%s.sty" % name], tempfile.gettempdir(), env, 300)
			pkgs = [ln[:-1] for ln in found.splitlines() if ln.endswith(":") and not ln.startswith(" ")]
			target = pkgs[0] if pkgs else name
			code, out = _run([info["tlmgr"], "install", target], tempfile.gettempdir(), env, 1200)
		except Exception as exc:
			return False, "Could not run tlmgr: %s" % exc
		return code == 0, out
	return False, "No package manager was found. Install MiKTeX, or set its folder in Build, Settings."


def update_packages(cfg, info=None):
	import tempfile
	info = info or package_system(cfg)
	try:
		if info["mpm"]:
			code, out = _run([info["mpm"], "--update"], tempfile.gettempdir(), _env_with_tool_dir(info["mpm"]), 3600)
			return code == 0, out
		if info["tlmgr"]:
			code, out = _run([info["tlmgr"], "update", "--all"], tempfile.gettempdir(), _env_with_tool_dir(info["tlmgr"]), 3600)
			return code == 0, out
	except Exception as exc:
		return False, "Update failed: %s" % exc
	return False, "No package manager was found."
