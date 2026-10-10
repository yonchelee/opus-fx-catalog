"""원본·편집 데이터 분리와 생성기 시험.  python3 -m unittest discover -s tests"""
import json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'skill' / 'opus-fx-scout' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import build_site  # noqa: E402
import sync  # noqa: E402


def row(i, **kw):
    r = {'id': i, 'src': i.split(':')[0], 'slug': i.split(':')[1], 'author': 'a', 'post_url': '', 'prompt': 'p',
         'fx': [], 'needs': [], 'level': 1, 'category': 'motion', 'partial': False, 'added': '2026-10-01'}
    r.update(kw)
    return r


class Merge(unittest.TestCase):
    def test_exact_id_only(self):
        items = [row('yihui:a-1'), row('yihui:a-12')]
        merged, orphans = build_site.merge(items, {'items': {'yihui:a-1': {'title_ko': '하나'}}})
        self.assertEqual(merged[0]['ed']['title_ko'], '하나')
        self.assertNotIn('ed', merged[1])  # 비슷한 slug 에 붙지 않는다
        self.assertEqual(orphans, [])

    def test_orphan_not_linked(self):
        merged, orphans = build_site.merge([row('yihui:a-2')], {'items': {'yihui:gone-9': {'title_ko': 'x'}}})
        self.assertEqual(orphans, ['yihui:gone-9'])
        self.assertTrue(all('ed' not in r for r in merged))

    def test_editorial_does_not_overwrite_source(self):
        merged, _ = build_site.merge([row('yihui:a-1', title='Orig')], {'items': {'yihui:a-1': {'title_ko': '편집'}}})
        self.assertEqual(merged[0]['title'], 'Orig')

    def test_item_path(self):
        self.assertEqual(build_site.item_path('yihui:_gill-ex_1'), 'fx/yihui/_gill-ex_1/')


class SyncKeepsEditorial(unittest.TestCase):
    def test_sync_merge_keeps_likes_and_media(self):
        old = [row('yihui:a-1', likes=5, likes_at='2026-10-10', thumb='t')]
        new = [row('yihui:a-1', prompt='updated')]
        merged, _, changed = sync.merge(old, new)
        self.assertEqual((merged[0]['likes'], merged[0]['thumb'], merged[0]['prompt']), (5, 't', 'updated'))

    def test_sync_out_never_touches_editorial(self):
        """sync.py --out 은 store.save_to_dir 와 build_site 만 부른다. editorial.json 은 바이트 그대로여야 한다."""
        with tempfile.TemporaryDirectory() as t:
            for f in ('catalog.json', 'editorial.json', 'sources.json'):
                shutil.copy(ROOT / f, Path(t) / f)
            before = (Path(t) / 'editorial.json').read_bytes()
            cat = json.loads((ROOT / 'catalog.json').read_text())
            import store
            store.save_to_dir(t, cat['items'], json.loads((ROOT / 'sources.json').read_text()), cat['synced'])
            build_site.build(t)
            self.assertEqual((Path(t) / 'editorial.json').read_bytes(), before)
            self.assertEqual(build_site.build(t, check=True), 0)


class Generated(unittest.TestCase):
    def test_repo_generated_files_are_fresh(self):
        r = subprocess.run([sys.executable, str(SCRIPTS / 'build_site.py'), '--dir', str(ROOT), '--check'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_no_orphans_in_repo(self):
        cat, ed = build_site.load(ROOT)
        _, orphans = build_site.merge(cat['items'], ed)
        self.assertEqual(orphans, [])


if __name__ == '__main__':
    unittest.main()
