"""The fix room's F13: the second audit room's should-fixes that are the repository's own (2 Oct 2026, his yes to all 27, with
his choice for 26; the fix room's record of 1 Oct 2026, not in this repository, section 29). Written before the fix, to fail on the
workflows as F12 left them, and to pass once they are fixed. By the report's numbers (11.2):
10 (F7.1)  every action pinned by its commit's SHA, the release it is named beside; Dependabot keeps the pins current.
26 (F5.2)  the Pages workflow skips while the repository is private (his choice), and the workflows' comments say what
           they do now.
Items 12, 13 and 23 live in files the Castle keeps as written: the public copy's curation carries them, and F13's bar and
the release bar check them there.
"""
import os, re, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WF = os.path.join(ROOT, '.github', 'workflows')


def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def workflows():
    return {f: read(os.path.join(WF, f)) for f in sorted(os.listdir(WF)) if f.endswith('.yml')}


class F13_10_PinnedActions(unittest.TestCase):
    def test_every_action_is_pinned_by_sha_beside_its_release(self):
        n = 0
        for f, t in workflows().items():
            for m in re.finditer(r'^\s*-?\s*uses:\s*(\S+)(.*)$', t, re.M):
                n += 1
                with self.subTest(f, uses=m.group(1)):
                    self.assertRegex(m.group(1), r'^[\w.-]+/[\w.-]+@[0-9a-f]{40}$')
                    self.assertRegex(m.group(2), r'#\s*v\d+\.\d+\.\d+\b')
        self.assertGreaterEqual(n, 19)

    def test_dependabot_keeps_the_actions_current(self):
        p = os.path.join(ROOT, '.github', 'dependabot.yml')
        self.assertTrue(os.path.exists(p), 'no .github/dependabot.yml')
        t = read(p)
        self.assertRegex(t, r'(?m)^version:\s*2\s*$')
        self.assertRegex(t, r'package-ecosystem:\s*"?github-actions"?')
        self.assertRegex(t, r'interval:\s*"?(?:daily|weekly|monthly)"?')


class F13_26_PagesWhilePrivate(unittest.TestCase):
    def test_the_deploy_job_skips_while_the_repository_is_private(self):
        t = workflows()['pages.yml']
        job = t[t.index('  deploy:'):]
        self.assertRegex(job.split('steps:')[0], r'if:\s*\$\{\{\s*!\s*github\.event\.repository\.private\s*\}\}')

    def test_the_comments_say_what_the_workflows_do_now(self):
        for f, t in workflows().items():
            c = ' '.join(l.strip().lstrip('#').strip() for l in t.splitlines() if l.strip().startswith('#'))
            for stale in (r'once the (?:public )?repository (?:is public|exists)', r'\bhis keys?\b', r'still to come',
                          r'the launch list', r'\b(?:seventh|thirteenth|build) room\b'):
                with self.subTest(f, stale=stale):
                    self.assertNotRegex(c, stale)


if __name__ == '__main__':
    unittest.main()
