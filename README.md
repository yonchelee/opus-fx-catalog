# opus-fx-catalog

**갤러리: https://yonchelee.github.io/opus-fx-catalog/** — 썸네일에 마우스를 올리면 움직임, 누르면 영상과 원본 프롬프트.

Claude(Opus 5.5 등)로 실제 만들어진 모션그래픽·3D·셰이더·인터랙티브 효과의 프롬프트 카탈로그입니다.
`opus-fx-scout` 스킬이 이 저장소를 읽어 결과물에 맞는 효과를 추천하고, 주간 자가서칭이 새 항목을 여기에 커밋합니다.

- `catalog.json` — 항목 전체 (`synced` 날짜 + `items`). 항목마다 원작자 게시물, 영상, 프롬프트 원문 링크, 효과 분류(fx), 필요 도구(needs), 실행 단계(level 1~4), 좋아요 수(likes·likes_at — `skill/opus-fx-scout/scripts/likes.py`가 X 게시물에서 받아 옴, `sync.py --out` 때 6일 지난 값만 갱신)
- `sources.json` — 등록된 소스와 채택 이유
- `editorial.json` — 손으로 편집하는 정보(한국어 제목·설명·용도·추천·검증 상태·적용 가이드·검색 동의어). 키는 catalog.json 의 id. **자동 갱신이 쓰지 않는다**
- `assets/` — 갤러리 화면(site.css, app.js, data.js 병합 규칙, search.js 검색)
- `fx/`, `use/`, `sitemap.xml` — `skill/opus-fx-scout/scripts/build_site.py`가 만드는 정적 페이지. 손으로 고치지 말고 생성기를 다시 돌린다(`--check`로 낡음 검사)
- `tests/` — `python3 -m unittest discover -s tests`, `node --test tests/`, `node tests/e2e.mjs`
- `index.html` — 갤러리 페이지 (GitHub Pages, main 브랜치 루트). `?pick=id,id`로 후보만 번호 붙여 보기, `?q=`·`?fx=`로 필터, 기본은 좋아요 많은 순이고 `?sort=new`면 최신순
- 미리보기는 원본 게시물·skillry.dev의 공개 주소를 그대로 불러옵니다(저장소에 이미지를 저장하지 않음). 썸네일·MP4 주소 일부는 Li-Evan 모음에서 게시물 번호로 맞춰 가져왔습니다(`skill/opus-fx-scout/scripts/enrich_media.py`).

## 출처와 권리
모든 프롬프트와 영상의 권리는 각 원작자에게 있습니다. 항목은 아래 공개 모음에서 가져왔습니다.
- [yihui-dev/awesome-opus5-5-videos](https://github.com/yihui-dev/awesome-opus5-5-videos) — MIT (`src: yihui` 항목)
- [Li-Evan/awesome-opus-5.5-video-prompts](https://github.com/Li-Evan/awesome-opus-5.5-video-prompts) — CC BY 4.0 (`src: lievan` 항목)

새 소스가 추가되면 `sources.json`과 이 목록에 함께 기록합니다.

## 스킬 원본
`skill/opus-fx-scout/`는 이 카탈로그를 쓰는 스킬의 원본입니다. claude.ai 계정에는 패키징한 `.skill` 파일을 저장해서 씁니다.
스킬을 고치면 여기서 고치고 다시 패키징합니다. 주간 예약 작업도 이 폴더의 스크립트로 카탈로그를 갱신합니다.

```bash
python3 skill/opus-fx-scout/scripts/sync.py --out .   # 등록된 소스 동기화 → catalog.json 갱신
python3 skill/opus-fx-scout/scripts/find.py --stats    # 효과별 개수
```
