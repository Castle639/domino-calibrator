#!/usr/bin/env python3
"""The fix room's F5 bar: the last pointers and psfkit's docstring (1 Oct 2026, his answers 2 and 3 after the room's first
checkpoint, in the room's report, sections 12 and 13). Committed before it runs: red on the folder as the curation's fourth
version builds it, green after its fifth. Its folder is built in the scratchpad with the recipe it is given, never in
release/. It names no string it looks for: the Castle's never-public files, the paper's path and its reference, psfkit's
phrases and F4's lists come from CHECKS, a file kept outside the folder, whose content the room's report records.

  python runs/fix_f5_bar.py LOG SCRATCH CURATE DECISIONS CHECKS      from calibrator/, with ADES_PYLIB, ADES_MASTER and
                                                                    PLAYWRIGHT_MODULE set

  V0  the controls, run first: V1 finds a pointer planted in a copy of the folder built; V2 fails on the Castle's own first
      study record, V3 on the Castle's own ades.py, V4 on the Castle's own psfkit.py; V5 finds an executable line planted in
      a runs/ script, and passes a comment planted there
  V1  his answer 2: no text file of the folder names one of CHECKS' never-public files (its name whole, with or without its
      folder and extension); nor, generically, a record of the calibrator's that is not in the folder's archive/, or a file
      of tools/ that is not in its tools/ (papers/ is checked by name: W6's own words name the folder, "archive/ or papers/")
  V2  the paper: no file of the folder names its text's path, and each file whose Castle source named it gives the public
      reference instead, as often as the source named the path
  V3  domino_calibrator/ades.py (his "make sure it's covered"): no never-public name in it, and its code the Castle's
  V4  his answer 3, psfkit.py's docstring: CHECKS' kept words there, none of its dropped ones, and TinyTim's source named
      in words
  V5  never code: every .py file of the folder parses to the same code as its Castle source, docstrings and comments aside,
      but CHECKS' named stand-ins
  V6  F4 still holds: no placeholder, no machine path, no pointer to a file left out; none of the 24 there, all 7 kept
  V7  the whole suite, strict, in a copy of the folder with Hubble's frames linked (the public arrangement), on the kit with
      the tested versions' flag: PASS, 0 failures, 0 errors, 0 skipped

Amendment 1 (1 of 2), before any green run: V0's control planted a tool that is not in the folder by spelling its name in
this file, which goes public with runs/ and which V1's generic half then read (the red run's 29th hit). The plant is now
made from two halves, so that this file never spells a tool the folder lacks.
"""
import os, re, sys, ast, json, shutil, hashlib, tempfile, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # calibrator/
REPO = os.path.dirname(ROOT)
LOG, SCRATCH, CURATE, DECISIONS, CHECKS = sys.argv[1:6]
CK = json.load(open(CHECKS, encoding='utf-8'))
out = open(LOG, 'w', encoding='utf-8')
BINARY = ('.png', '.woff2', '.gz', '.fits', '.npz', '.ico', '.pdf', '.svg')
STRICT = re.compile(r'^strict: (PASS|FAIL) \((\d+) run, (\d+) failures, (\d+) errors, (\d+) skipped: (\d+) allowed, (\d+) not\)', re.M)


def say(s):
    print(s, flush=True); out.write(s + '\n'); out.flush()


def read(p):
    return open(p, encoding='utf-8').read()


def texts(root):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d != '.git']
        for f in fn:
            if f.endswith(BINARY):
                continue
            p = os.path.join(dp, f)
            try:
                yield os.path.relpath(p, root), read(p)
            except UnicodeDecodeError:
                continue


def name_rx(names):
    """A whole name, with or without its folder and extension (the curation's own reading of a pointer)."""
    return re.compile(r'(?<![\w-])(?:%s)(?![\w-])' % '|'.join(re.escape(n) for n in sorted(names, key=len, reverse=True)))


def hits(root, rx):
    found = {}
    for rel, t in texts(root):
        n = len(rx.findall(t))
        if n:
            found[rel] = n
    return found


def code(src):
    """The code a .py source parses to, docstrings and comments aside."""
    tree = ast.parse(src)
    for node in ast.walk(tree):
        body = getattr(node, 'body', None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], 'value', None), ast.Constant) \
                and isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]
    return ast.dump(tree, include_attributes=False)


def castle_source(rel):
    return os.path.join(REPO, rel) if rel.startswith('tools/') else os.path.join(ROOT, rel)


def code_changed(folder):
    bad = []
    for rel, t in texts(folder):
        if not rel.endswith('.py'):
            continue
        src = castle_source(rel)
        if not os.path.exists(src):
            bad.append(rel + ' (no source)')
            continue
        try:
            if code(t) != code(read(src)):
                bad.append(rel)
        except SyntaxError as e:
            bad.append('%s (does not parse: %s)' % (rel, e.msg))
    return bad


REC = re.compile(r'(?<![\w-])(CALIBRATOR_[A-Z0-9_]+?_20\d\d-\d\d-\d\d)(?![\w-])')
TOOL = re.compile(r'(?<![\w.-])tools/([\w-]+\.(?:py|sh|js|json|txt|md))(?![\w])')


def generic(folder):
    """V1's generic half: {relpath: count} of a record name not in the folder's archive/, and a file of tools/ not in its
    tools/."""
    records = {os.path.splitext(f)[0] for f in os.listdir(os.path.join(folder, 'archive'))} if os.path.isdir(os.path.join(folder, 'archive')) else set()
    tools = set(os.listdir(os.path.join(folder, 'tools'))) if os.path.isdir(os.path.join(folder, 'tools')) else set()
    found = {}
    for rel, t in texts(folder):
        n = sum(1 for m in REC.finditer(t) if m.group(1) not in records)
        n += sum(1 for m in TOOL.finditer(t) if m.group(1) not in tools)
        if n:
            found[rel] = n
    return found


def paper_case(folder_file, castle_file):
    """V2 for one file: (no path left, the reference given as often as the source named the path), with the counts."""
    P, R = CK['paper']['path'], CK['paper']['reference']
    src = read(castle_file) if os.path.exists(castle_file) else ''
    t = read(folder_file) if os.path.exists(folder_file) else ''
    need = src.count(P)
    return P not in t and t.count(R) >= need + src.count(R), need, t.count(P), t.count(R)


def docstring(path):
    try:
        return ast.get_docstring(ast.parse(read(path)), clean=False) or ''
    except (SyntaxError, OSError):
        return ''


def psfkit_case(path):
    d = docstring(path)
    kept = [w for w in CK['psfkit']['keep'] if w not in d]
    dropped = [w for w in CK['psfkit']['drop'] if w in d]
    source = CK['psfkit']['source'] in d
    return not kept and not dropped and source, 'kept words missing: %d of %d | dropped words left: %d of %d | TinyTim\'s source ' \
        'named in words: %s' % (len(kept), len(CK['psfkit']['keep']), len(dropped), len(CK['psfkit']['drop']), source)


def build(recipe, decisions, dest):
    shutil.rmtree(dest, ignore_errors=True)
    c = subprocess.run([sys.executable, recipe, REPO, dest, decisions, dest + '.manifest'], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=1800)
    return c.returncode == 0


def main():
    head = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
    sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
    say('# fix_f5_bar | HEAD %s | its sha256 %s | CHECKS %s | the recipe %s, %s | its decisions %s, %s' % (
        head, sha(os.path.abspath(__file__)), sha(CHECKS)[:12], os.path.basename(CURATE), sha(CURATE)[:12],
        os.path.basename(DECISIONS), sha(DECISIONS)[:12]))
    met = []
    work = os.path.join(SCRATCH, 'fix_f5_bar')
    os.makedirs(work, exist_ok=True)
    folder = os.path.join(work, 'folder')
    ok_build = build(CURATE, DECISIONS, folder)
    nfiles = sum(len(f) for _, _, f in os.walk(folder)) if ok_build else 0
    say('#   the folder built by the recipe: %s (%d files)' % ('yes' if ok_build else 'NO (the recipe failed)', nfiles))
    never = name_rx(CK['never_public'])
    d = tempfile.mkdtemp(dir=work)
    try:
        # V0: the controls
        ctl = {}
        plant = os.path.join(d, 'plant'); shutil.copytree(folder, plant)
        base, gbase = sum(hits(plant, never).values()), sum(generic(plant).values())
        with open(os.path.join(plant, 'README.md'), 'a', encoding='utf-8') as f:
            f.write('\nsee %s\n' % CK['never_public'][0])
            f.write('\nsee %s/%s\n' % ('tools', 'zz_unknown.py'))           # amendment 1: never spelled whole here
        ctl['a pointer planted is found'] = sum(hits(plant, never).values()) == base + 1
        ctl['a tool planted that is not in the folder is found'] = sum(generic(plant).values()) >= gbase + 1
        first = CK['paper']['castle_files'][0]
        ctl["the Castle's own first study record fails V2"] = not paper_case(os.path.join(REPO, first), os.path.join(REPO, first))[0]
        a = os.path.join(ROOT, 'domino_calibrator', 'ades.py')
        ctl["the Castle's own ades.py fails V3"] = bool(never.search(read(a)))
        ctl["the Castle's own psfkit.py fails V4"] = not psfkit_case(os.path.join(REPO, 'tools', 'psfkit.py'))[0]
        before = code_changed(plant)
        scripts = sorted(f for f in os.listdir(os.path.join(plant, 'runs')) if f.endswith('.py') and 'runs/' + f not in before)
        target = os.path.join(plant, 'runs', scripts[0]); src = read(target)
        open(target, 'w', encoding='utf-8').write(src + '\n# a comment planted\n')
        comment_passes = code_changed(plant) == before
        open(target, 'w', encoding='utf-8').write(src + '\n_PLANTED = 1\n')
        ctl['an executable line planted is found, a comment is not'] = comment_passes and 'runs/' + scripts[0] in code_changed(plant)
        v0 = ok_build and all(ctl.values())
        say('V0  %s  %s' % ('PASS' if v0 else 'FAIL', ' | '.join('%s: %s' % kv for kv in ctl.items())))
        met.append(v0)

        # V1: no pointer to a never-public file
        h, g = hits(folder, never), generic(folder)
        v1 = ok_build and not h and not g
        say('V1  %s  pointers to a never-public file of the Castle: %d in %d files | generically (a record or a tool not in the '
            'folder): %d in %d files' % ('PASS' if v1 else 'FAIL', sum(h.values()), len(h), sum(g.values()), len(g)))
        for f in sorted(set(h) | set(g))[:8]:
            say('    %s %d, %d' % (f, h.get(f, 0), g.get(f, 0)))
        met.append(v1)

        # V2: the paper's public reference
        rows, v2 = [], ok_build
        for rel in CK['paper']['castle_files']:
            frel = rel[len('calibrator/'):] if rel.startswith('calibrator/') else rel
            ok, need, left, given = paper_case(os.path.join(folder, frel), os.path.join(REPO, rel))
            v2 = v2 and ok
            rows.append('%s: the path %d in the source, %d left, the reference %d' % (frel, need, left, given))
        anywhere = hits(folder, re.compile(re.escape(CK['paper']['path'])))
        v2 = v2 and not anywhere
        say('V2  %s  the paper\'s path left anywhere in the folder: %d | %s' % ('PASS' if v2 else 'FAIL', sum(anywhere.values()), ' | '.join(rows)))
        met.append(v2)

        # V3: ades.py, covered
        fa = os.path.join(folder, 'domino_calibrator', 'ades.py')
        t = read(fa) if os.path.exists(fa) else ''
        same = bool(t) and code(t) == code(read(a))
        v3 = bool(t) and not never.search(t) and same
        say('V3  %s  domino_calibrator/ades.py: never-public names %d | its code the Castle\'s: %s' % (
            'PASS' if v3 else 'FAIL', len(never.findall(t)), same))
        met.append(v3)

        # V4: psfkit's docstring
        fp = os.path.join(folder, 'tools', 'psfkit.py')
        v4, why4 = psfkit_case(fp) if os.path.exists(fp) else (False, 'no tools/psfkit.py')
        v4 = ok_build and v4
        say('V4  %s  tools/psfkit.py\'s docstring: %s' % ('PASS' if v4 else 'FAIL', why4))
        met.append(v4)

        # V5: never code
        changed = [f for f in code_changed(folder) if f not in CK['code_standins']]
        v5 = ok_build and not changed
        say('V5  %s  .py files whose code the curation changed, but the named stand-ins: %d%s' % (
            'PASS' if v5 else 'FAIL', len(changed), (' (%s)' % ', '.join(changed[:6])) if changed else ''))
        met.append(v5)

        # V6: F4 still holds
        f4 = CK['f4']
        ph = sum(t.count(p) for _, t in texts(folder) for p in f4['placeholders'])
        mp = sum(t.count(p) for _, t in texts(folder) for p in f4['machine_paths'])
        lo = hits(folder, name_rx([os.path.splitext(os.path.basename(x))[0] for x in f4['leave_out']]))
        there = [x for x in f4['leave_out'] if os.path.exists(os.path.join(folder, x))]
        gone = [x for x in f4['keep'] if not os.path.exists(os.path.join(folder, x))]
        v6 = ok_build and not ph and not mp and not lo and not there and not gone
        say('V6  %s  placeholders %d | machine paths %d | pointers to a file left out %d | left out, still there: %d of %d | kept, '
            'missing: %d of %d' % ('PASS' if v6 else 'FAIL', ph, mp, sum(lo.values()), len(there), len(f4['leave_out']), len(gone),
                                   len(f4['keep'])))
        met.append(v6)

        # V7: the whole suite in the public arrangement
        copy = os.path.join(d, 'public_copy'); shutil.copytree(folder, copy)
        frames = [l.split()[0] for l in open(os.path.join(copy, 'runs', 'H0_POSITIONS_2026-09-30.txt')) if l.strip() and not l.startswith('#')]
        for fr in frames:
            os.symlink(os.path.join(REPO, 'data', 'hst-3i', fr + '_flc.fits'), os.path.join(copy, 'data', 'hst-3i', fr + '_flc.fits'))
        e = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'VIRTUAL_ENV')}
        e['DOMINO_CALIBRATOR_TESTED_VERSIONS'] = '1'
        c = subprocess.run([sys.executable, '-m', 'tests.strict'], cwd=copy, env=e, capture_output=True, encoding='utf-8',
                           errors='replace', timeout=5400)
        m = STRICT.search(c.stdout + c.stderr)
        v7 = c.returncode == 0 and bool(m) and m.group(1) == 'PASS' and m.group(3) == m.group(4) == m.group(5) == '0'
        say('V7  %s  the whole suite in a copy of the folder, the frames linked (%d): %s' % (
            'PASS' if v7 else 'FAIL', len(frames), m.group(0) if m else 'no strict summary'))
        if not v7:
            for mm in re.findall(r'^(?:FAIL|ERROR): (\S+) \((\S+)\)', c.stdout + c.stderr, re.M)[:12]:
                say('    %s %s' % mm)
        met.append(v7)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    k = sum(met)
    say('# fix f5 bar: %s, %d of %d%s' % ('MET' if k == len(met) else 'NOT MET', k, len(met),
                                         '' if k == len(met) else ' (failing: %s)' % ' '.join('V%d' % i for i, v in enumerate(met) if not v)))


if __name__ == '__main__':
    main()
