"""case_library 출처(LeaddeOpenLab 형식) 읽기 시험.  python3 -m unittest discover -s tests"""
import json, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'skill' / 'opus-fx-scout' / 'scripts'))
import case_library  # noqa: E402
import sync  # noqa: E402

SRC = {'id': 'leadde', 'type': 'case_library', 'repo': 'o/r', 'path': 'data/library/*.json',
       'filter': {'prompt_status': ['full_original']},
       'prompt_url_tpl': 'https://github.com/o/r/blob/main/prompts/{slug}.md', 'model': 'Opus 5.5', 'status': 'active'}


def case(pid, status='full_original', topic='motion-graphics', task='other-animation', tools=(), prompt='make a thing'):
    return {
        'prompt': prompt, 'summaryEn': f'Title {pid}', 'xUrl': f'https://x.com/someone/status/{pid}',
        'coverUrl': 'https://pbs.twimg.com/amplify_video_thumb/1/img/a.jpg',
        'mediaFingerprints': [f'https://video-s.twimg.com/amplify_video/1/vid/avc1/480x270/{pid}.mp4?tag=29', f'x-post:{pid}'],
        'post': {'id': pid, 'canonicalUrl': f'https://x.com/someone/status/{pid}',
                 'author': {'username': 'someone', 'profileUrl': 'https://x.com/someone'}},
        'analysis': {'caseEvidence': {'prompt': {'status': status}, 'task': task, 'purpose': {'topic': topic},
                                      'tools': [{'name': n, 'status': s} for n, s in tools]}},
    }


def files(*cases):
    return [(f"{c['post']['id']}.json", json.dumps(c)) for c in cases]


class Rows(unittest.TestCase):
    def test_full_original_only(self):
        out, st = case_library.rows(SRC, files(case('1'), case('2', status='fragment')), [])
        self.assertEqual([v['slug'] for v in out], ['1'])
        self.assertEqual((st['kept'], st['filtered']), (1, 1))

    def test_skips_posts_another_source_has(self):
        have = [{'id': 'yihui:x-1', 'src': 'yihui', 'post_url': 'https://x.com/a/status/1'}]
        out, st = case_library.rows(SRC, files(case('1'), case('2')), have)
        self.assertEqual([v['slug'] for v in out], ['2'])
        self.assertEqual(st['dup'], 1)

    def test_keeps_first_added_date(self):
        have = [{'id': 'leadde:1', 'src': 'leadde', 'post_url': 'https://x.com/a/status/1', 'added': '2026-10-01'}]
        out, _ = case_library.rows(SRC, files(case('1'), case('2')), have)
        self.assertEqual(out[0].get('added'), '2026-10-01')
        self.assertNotIn('added', out[1])  # 새 행은 normalize 가 오늘 날짜를 준다

    def test_category_and_tags(self):
        c = case('1', topic='games-interactive', tools=(('Three.js', 'required'), ('Blender', 'prohibited'), ('WebGPU', 'required')))
        v = case_library.row(c)
        self.assertEqual(v['category'], 'interactive')
        self.assertEqual(v['tech_tags'], ['shader', 'threejs'])  # prohibited 도구는 태그로 안 넣는다
        self.assertEqual(case_library.row(case('2', topic=None, task='blender'))['category'], '3d')
        self.assertEqual(case_library.row(case('3', topic=None, task='unknown'))['category'], 'motion')

    def test_media_from_author_post_only(self):
        c = case('1'); c['coverUrl'] = 'https://example.com/not-x.jpg'
        v = case_library.row(c)
        self.assertNotIn('thumb', v)
        self.assertTrue(v['mp4'].startswith('https://video-s.twimg.com/'))

    def test_normalize_row(self):
        r = sync.normalize('leadde', case_library.row(case('1', prompt='a three.js scene rendered to mp4 with ffmpeg')),
                           SRC['prompt_url_tpl'], SRC['model'])
        self.assertEqual((r['id'], r['src'], r['partial'], r['model']), ('leadde:1', 'leadde', False, 'Opus 5.5'))
        self.assertEqual(r['prompt_url'], 'https://github.com/o/r/blob/main/prompts/1.md')
        self.assertIn('3d', r['fx'])
        self.assertEqual(r['level'], 2)
        self.assertEqual(r['title'], 'Title 1')

    def test_bad_file_counted(self):
        no_post = {'prompt': 'p', 'analysis': {'caseEvidence': {'prompt': {'status': 'full_original'}}}}
        no_status = {'prompt': 'p'}
        out, st = case_library.rows(SRC, [('x.json', '{not json'), ('y.json', json.dumps(no_post)), ('z.json', json.dumps(no_status))], [])
        self.assertEqual((out, st['bad'], st['filtered']), ([], 2, 1))


if __name__ == '__main__':
    unittest.main()
