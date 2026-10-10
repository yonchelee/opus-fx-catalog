"""Effect + requirement classifier shared by sync.py and find.py.

Every English pattern is word-bounded on purpose: the first version matched
substrings, so "think"/"link" landed in painterly and "scene" anywhere
landed in 3D. Keep new patterns bounded the same way.
Chinese/Korean terms are appended unbounded (no word breaks in CJK).
"""
import re

# key, Korean label, short hint, regex (matched against lowercased prompt)
FX = [
    ('3d', '3D 씬·카메라', 'Three.js 공간, 카메라 무빙',
     r'\bthree\.?js\b|\b3d\b|\bwebgl\b|\bcamera (fl(y|ies|ying)|mov\w*|orbit\w*|dolly|push(es)?)\b|\bdepth of field\b|\bblender\b|三维|3D场景|镜头|运镜|카메라 무빙'),
    ('shader', '셰이더·글로우', 'GLSL, 블룸, 네온 빛',
     r'\bshaders?\b|\bglsl\b|\bbloom\b|\bglow(s|ing)?\b|\bneon\b|\braymarch\w*|\bfragment shader\b|\bchromatic aberration\b|着色器|光晕|发光|霓虹|셰이더|네온'),
    ('reel', '모션 쇼릴', '“쇼릴처럼 다 보여줘”류 짧은 프롬프트',
     r'\bshow ?reel\b|\bmotion designer you are\b|\bgo all out\b'),
    ('game', '플레이어블 게임', '키보드·터치로 조작',
     r'\bgames?\b|\bplayable\b|\bwasd\b|\barrow keys\b|\bgameplay\b|游戏|可玩|게임'),
    ('paint', '페인터리·손그림', '붓, 수채, 잉크, 종이 질감',
     r'\bpaint(ed|ing|ings|erly|s)?\b|\bbrush(es|stroke|strokes)?\b|\bwatercolou?r\b|\bink\b|\bsketch(y|ed|es)?\b|\bhand[- ]?(drawn|painted)\b|\bpencil\b|\bacrylic\b|\bpaper(y)?\b|\bgouache\b|\bcel[- ]shad\w*|水彩|手绘|水墨|油画|笔触|纸质|수채|손그림|붓'),
    ('ui', 'UI·제품 데모', '앱 화면, 런칭 영상',
     r'\bui\b|\bdashboard\b|\bapp screens?\b|\binterface\b|\bproduct (demo|launch|film|video)\b|\bsaas\b|\blanding page\b|\biphone\b|\blaunch (video|film|ad)\b|界面|产品演示|发布会|产品视频|제품 데모|런칭'),
    ('particles', '파티클·입자', '불꽃, 먼지, 군집',
     r'\bparticles?\b|\bswarm\b|\bsparks?\b|\bdust\b|\bconfetti\b|\bstarfield\b|\bboids\b|\bflock\w*|粒子|파티클|입자'),
    ('audio', '사운드 동기화', 'Web Audio, 비트 싱크',
     r'\bweb audio\b|\bsound ?design\b|\bsoundtrack\b|\bbpm\b|\bbeat[- ]?(grid|sync\w*)\b|\bon the beat\b|\baudio[- ]reactive\b|\bsynthesi[sz]ed\b|\bsound effects?\b|音效|配乐|节拍|音乐同步|사운드|비트'),
    ('liquid', '유체·물리', '물, 파동, 충돌',
     r'\bfluids?\b|\bliquid\b|\bwater\b|\bocean\b|\bwaves?\b|\bphysics\b|\bcloth\b|\bsoft[- ]body\b|\bragdoll\b|\bgravity\b|\bcollisions?\b|\bsprings?\b|流体|液体|物理|水面|유체|물리'),
    ('cosmic', '우주·자연', '행성, 은하, 숲, 하늘',
     r'\bgalax(y|ies)\b|\bplanets?\b|\bouter space\b|\bcosmic\b|\bnebula\b|\bblack hole\b|\baurora\b|\bforests?\b|\btrees?\b|\bmountains?\b|\bsky\b|\bskies\b|宇宙|星空|星系|行星|森林|우주|은하'),
    ('pixel', '픽셀아트', '8비트, 스프라이트',
     r'\bpixel[- ]?art\b|\bpixels?\b|\b8-bit\b|\b16-bit\b|\bsprites?\b|像素|픽셀'),
    ('morph', '모핑·트랜지션', '형태 변환, 매치컷, 루프',
     r'\bmorph\w*|\btransitions? between\b|\btransforms? into\b|\bseamless(ly)? loop\w*|\bmatch cuts?\b|变形|转场|모핑|트랜지션'),
    ('glitch', '글리치·레트로', 'CRT, VHS, ASCII',
     r'\bglitch\w*|\bcrt\b|\bvhs\b|\bretro\b|\bsynthwave\b|\bscan ?lines?\b|\bascii\b|\bdemoscene\b|故障|复古|赛博|글리치|레트로'),
    ('kinetic', '키네틱 타이포', '움직이는 글자',
     r'\bkinetic\b|\btypograph\w*|\blettering\b|\btext reveals?\b|\bmasked (type|text)\b|\btitle cards?\b|\bwordmark\b|文字动画|字体动效|排版|타이포'),
    ('data', '데이터·인포그래픽', '차트, 지도, 다이어그램',
     r'\bcharts?\b|\bbar graph\b|\bline graph\b|\bdata vi[sz]\w*|\binfographics?\b|\bdiagrams?\b|\bstatistics?\b|\bmaps?\b|图表|数据可视化|信息图|地图|차트|인포그래픽|지도'),
    ('etc', '기타', '분류 키워드 없음', None),
]
FX_NAME = {k: n for k, n, _, _ in FX}
TAGFX = {'particles': 'particles', 'shader': 'shader', 'webgl': 'shader', 'pixel': 'pixel',
         'physics': 'liquid', 'audio': 'audio', 'playable': 'game', 'threejs': '3d'}

# What the build actually needs. Level = the lightest place it can run.
#   1 채팅만      - single HTML file; a claude.ai chat artifact can show it
#   2 Claude Code - needs a shell: rendering to MP4, Node packages, local files
#   3 외부 프로그램 - a desktop app must be installed (Blender, Unity, ...)
#   4 외부 AI·API  - paid generation APIs / keys (video, image, voice models)
NEEDS = [
    ('render', 2, 'MP4 렌더링 (Playwright·ffmpeg)',
     r'\bmp4\b|\bffmpeg\b|\bplaywright\b|\bpuppeteer\b|\brender(ed|ing)? (the |a |it )?(final )?(video|mp4)\b|\b60 ?fps\b|\bheadless\b|\bexport (the |a )?video\b'),
    ('remotion', 2, 'Remotion (React로 영상 제작)', r'\bremotion\b'),
    ('node', 2, 'Node.js 프로젝트 (React·Vite 등)', r'\breact(\.js)? ?(app|components?|\+|and remotion)|\bin react\b|\bvite\b|\bnext\.?js\b|\bnpm\b|\bnode\.?js\b'),
    ('python', 2, 'Python 분석 (numpy 등)', r'\bnumpy\b|\bpython\b|\blibrosa\b'),
    ('blender', 3, 'Blender', r'\bblender\b'),
    ('engine', 3, '게임엔진·네이티브 (Unity·Unreal·C++)', r'\bunity\b|\bunreal engine\b|\bue5\b|\bgodot\b|c\+\+|\bswift ?ui\b'),
    ('figma', 2, 'Figma 커넥터', r'\bfigma\b'),
    ('genvideo', 4, '영상 생성 AI (Seedance·Kling·Veo 등)', r'\bseedance\b|\bkling\b|\bveo\b|\brunway (gen|ml)\w*|\bsora\b|\bhailuo\b'),
    ('genimage', 4, '이미지 생성 AI (Seedream·GPT Image 등)', r'\bseedream\b|\bmidjourney\b|\bgpt[- ]?image\b|\bnano[- ]?banana\b|\bflux (pro|dev|kontext|1)|\bmagnific\b|\bfal(\.ai)?\b|\bfoul api\b|\bimage gen\w*'),
    ('genaudio', 4, '음성·음악 생성 AI (ElevenLabs·Suno 등)', r'\belevenlabs\b|\bsuno\b|\blyria\b|\budio\b'),
    ('assets', 0, '내 자료 필요 (로고·URL·음악·영상 등)',
     r'\bmy (product|portfolio|app|website|logo|brand|photos?|clips?|footage)\b|\byour product\b|<website url>|\bproduct (link|url)\b|\bask me for\b|\broyalty-free song\b|\bi\'ve (included|attached)\b|\battached\b|\breference video\b'),
]
NEED_NAME = {k: n for k, _, n, _ in NEEDS}
LEVEL_NAME = {1: '채팅만', 2: 'Claude Code', 3: '외부 프로그램', 4: '외부 AI·API'}


def classify(prompt, tech_tags):
    p = (prompt or '').lower()
    fx = {k for k, _, _, r in FX if r and re.search(r, p)}
    fx |= {TAGFX[t] for t in tech_tags if t in TAGFX}
    if not fx:
        fx = {'etc'}
    needs = {k for k, _, _, r in NEEDS if re.search(r, p)}
    if 'ai-image' in tech_tags:
        needs.add('genimage')
    level = max([lv for k, lv, _, _ in NEEDS if k in needs] + [1])
    return sorted(fx), sorted(needs), level
