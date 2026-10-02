#!/usr/bin/env python3
"""Launch step 7's bar: the release notes for 0.1.0, drafted (the launch list's step 7; the build room's brief of 30 Sept 2026, not in this repository,
section 1: "drafted. They are finished after the CI's first run"). Written before the notes exist (30 Sept 2026, the
calibrator's build room). The notes are CHANGELOG.md, beside the README. They restate the README, pyproject and the CI file,
and add no number of their own: a number that no source states is a claim nobody checked.

The clauses:
  N0  control: each check below fails on a planted copy (a number no source states; the old import name; a draft mark
      removed; a version not the package's; a path that is nowhere)
  N1  the notes say they are a draft, not released, and what is left before the release: the CI's first run, PyPI, the DOI,
      the page on GitHub Pages
  N2  their version is the package's (domino_calibrator.__version__)
  N3  every number in their plain text (code spans aside) is one the README, pyproject.toml or the CI file states
  N4  no old import name (the rename bar's scan), and the credit line as the README has it
  N5  every path they name in a code span is in the folder that goes public, or among the curation list's copied-in files

Amendment 1, after the green run: N0's plants were void. They wrote with open(p, 'w').write(read(p)...), which empties the
file before reading it, so each planted copy was empty (four checks red for the empty file, N5 green). The plant now reads
the text first, then writes, and asks that the planted text is in the file at its expected length. Nothing else changes.

Usage: python calibrator/runs/notes_bar.py REPO [CLAUSES]
"""
import os, re, sys, shutil, tempfile

REPO = sys.argv[1]
ONLY = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None
PKG = os.path.join(REPO, 'calibrator')
MODS = 'tests|cli|ades|apertures|degrade|estimators|hst|hstpsf|shrink|synth'
OLD = [re.compile(r'(?<![\w.-])(?:from\s+calibrator(?=[\s.])|import\s+calibrator(?![\w-]))'),      # the rename bar's five
       re.compile(r'(?<![\w/-])calibrator\.(?:%s|__\w+__)\b' % MODS),                                   # forms of the old name,
       re.compile(r'''(?<![\w-])['"]calibrator['"]'''),                                                  # copied from runs/
       re.compile(r'(?<![\w-])\.?/?calibrator/(?:tests|tools|data|runs|page|(?:__init__|%s)\.py)\b' % MODS),  # rename_bar.py
       re.compile(r'path:\s*calibrator\b|(?<![\w/-])\./calibrator\b')]
CREDIT = "A Castle product from Domino Observatory. Built by Annie, the Castle's AI."
COPIED_IN = ('tools/fetch_frames.py', 'tools/psfkit.py', 'data/hst-3i/', 'data/hst-3i/CHECKSUMS.sha256')
LEFT = ("CI's first run", 'PyPI', 'DOI', 'GitHub Pages')
RESULTS = {}


def verdict(name, ok, detail):
    RESULTS[name] = ok
    print('%-3s %s  %s' % (name, 'PASS' if ok else 'FAIL', detail), flush=True)


def want(name):
    return ONLY is None or name in ONLY


def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def sources():
    return '\n'.join(read(os.path.join(PKG, p)) for p in ('README.md', 'pyproject.toml', os.path.join('.github', 'workflows', 'tests.yml')))


def version():
    return re.search(r"^__version__ = '([^']+)'", read(os.path.join(PKG, 'domino_calibrator', '__init__.py')), flags=re.M).group(1)


def numbers(t):
    plain = re.sub(r'`[^`]*`', ' ', t)
    return sorted(set(re.findall(r'(?<![\w.])\d+(?:\.\d+)*(?![\w.]\d)', plain)))


def checks(root):
    """Each check on the notes at root: {name: (ok, detail)}."""
    p = os.path.join(root, 'CHANGELOG.md')
    if not os.path.exists(p):
        return {k: (False, 'no CHANGELOG.md') for k in ('N1', 'N2', 'N3', 'N4', 'N5')}
    t = read(p)
    out = {}
    draft = re.search(r'a draft, not released', t) is not None
    lacking = [w for w in LEFT if w not in t]
    out['N1'] = (draft and not lacking, 'draft marked: %s | what is left, lacking: %s' % (draft, ', '.join(lacking) or 'none'))
    head = re.search(r'^## (\d+\.\d+\.\d+)\b', t, flags=re.M)
    out['N2'] = (bool(head) and head.group(1) == version(), 'the notes: %s | the package: %s' % (head.group(1) if head else 'none', version()))
    src = sources()
    unsourced = [n for n in numbers(t) if not re.search(r'(?<![\w.])%s(?![\w]|\.\d)' % re.escape(n), src)]
    out['N3'] = (not unsourced and len(numbers(t)) > 0, '%d numbers, unsourced: %s' % (len(numbers(t)), ', '.join(unsourced) or 'none'))
    old = [i for i, line in enumerate(t.splitlines(), 1) if any(rx.search(line) for rx in OLD)]
    out['N4'] = (not old and CREDIT in re.sub(r'\s+', ' ', t), 'old-name lines: %s | the credit line: %s' % (old or 'none', CREDIT in re.sub(r'\s+', ' ', t)))
    spans = [s.strip() for s in re.findall(r'`([^`]*)`', t)]
    paths = [s for s in spans if ' ' not in s and (re.search(r'\.(md|py|html|js|txt|json|cff|toml|yml)$', s) or s.endswith('/'))]
    missing = [s for s in paths if not (os.path.exists(os.path.join(root, s)) or s in COPIED_IN)]
    out['N5'] = (not missing, '%d paths, missing: %s' % (len(paths), ', '.join(missing) or 'none'))
    return out


def main():
    print('# notes bar | CHANGELOG.md in %s' % PKG, flush=True)
    if want('N0'):
        rows, ok = [], True
        plants = {'N3': ('with numpy', 'with 31.4159 numpy'), 'N4': ('`domino-calibrator`', '`python -m calibrator.cli`'),
                  'N1': ('a draft, not released', 'released'), 'N2': ('## 0.1.0', '## 9.9.9'),
                  'N5': ('`README.md`', '`nowhere/at_all.md`')}
        base = checks(PKG)
        for k, (a, b) in plants.items():
            d = tempfile.mkdtemp(prefix='notes_n0_')
            shutil.copytree(PKG, os.path.join(d, 'c'), ignore=shutil.ignore_patterns('__pycache__', '*.egg-info', 'build', '.venv'))   # runs/ kept: N5 checks the notes' paths into it
            p = os.path.join(d, 'c', 'CHANGELOG.md')
            planted = os.path.exists(p) and a in read(p)
            if planted:                                     # amendment 1: read before writing, and the plant must be in the file
                txt = read(p)
                open(p, 'w', encoding='utf-8').write(txt.replace(a, b, 1))
                planted = b in read(p) and len(read(p)) == len(txt) - len(a) + len(b)
            got = checks(os.path.join(d, 'c'))[k][0]
            rows.append('%s planted: %s, then %s' % (k, planted, 'red' if not got else 'GREEN'))
            ok = ok and planted and not got
            shutil.rmtree(d, ignore_errors=True)
        verdict('N0', ok, ' | '.join(rows))
    res = checks(PKG)
    for k in ('N1', 'N2', 'N3', 'N4', 'N5'):
        if want(k):
            verdict(k, *res[k])
    names = [n for n in ('N0', 'N1', 'N2', 'N3', 'N4', 'N5') if n in RESULTS]
    met = sum(1 for n in names if RESULTS[n])
    print('# notes bar: %s, %d of %d%s' % ('MET' if met == len(names) else 'NOT MET', met, len(names),
                                            '' if met == len(names) else ' (failing: %s)' % ' '.join(n for n in names if not RESULTS[n])))


if __name__ == '__main__':
    main()
