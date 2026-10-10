# opus-fx-catalog

**갤러리: https://yonchelee.github.io/opus-fx-catalog/** — 썸네일에 마우스를 올리면 움직임, 누르면 영상과 원본 프롬프트.

Claude(Opus 5.5 등)로 실제 만들어진 모션그래픽·3D·셰이더·인터랙티브 효과의 프롬프트 카탈로그입니다.
`opus-fx-scout` 스킬이 이 저장소를 읽어 결과물에 맞는 효과를 추천하고, 주간 자가서칭이 새 항목을 여기에 커밋합니다.

- `catalog.json` — 항목 전체 (`synced` 날짜 + `items`). 항목마다 원작자 게시물, 영상, 프롬프트 원문 링크, 효과 분류(fx), 필요 도구(needs), 실행 단계(level 1~4), 좋아요 수(likes·likes_at — `skill/opus-fx-scout/scripts/likes.py`가 X 게시물에서 받아 옴, `sync.py --out` 때 6일 지난 값만 갱신)
- `sources.json` — 등록된 소스와 채택 이유
- `editorial.json` — 손으로 편집하는 정보(한국어 제목·설명·용도·추천·검증 상태·적용 가이드·검색 동의어). 키는 catalog.json 의 id. **자동 갱신이 쓰지 않는다**
- `assets/` — 갤러리 화면(site.css, app.js, data.js 병합 규칙, search.js 검색)
- `fx/`, `use/`, `sitemap.xml` — `skill/opus-fx-scout/scripts/build_site.py`가 만드는 정적 페이지. 손으로 고치지 말고 생성기를 다시 돌린다(`--check`로 낡음 검사)
- `github.json` — GitHub 공개 저장소를 키워드·기간별로 탐색해 공개 조건을 통과한 코드 기반 작품(프롬프트 없음·코드 제공). `discovery/` 가 원천
- `discovery/` — 발굴 설정(`config.json`), 후보 전체와 판정 사유(`candidates.json`), 별 수 시계열(`stars.json`), 검색 진행 위치(`state.json`), 실행 기록(`runs/`)
- `status.json` — 단계별 마지막 시도·성공 시각(화면의 '자료 갱신' 표시)
- `tests/` — `python3 -m unittest discover -s tests`, `node --test`, `node tests/e2e.mjs`
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

## 자동 갱신

| 무엇 | 어디서 | 언제 |
|---|---|---|
| 등록 출처 동기화 · GitHub 신규 후보 발굴 · 별 수 기록 · 생성 · 검증 · 커밋 · Pages 빌드 · 공개 확인 | GitHub Actions `.github/workflows/catalog-update.yml` | 매일 06:17 KST(daily), 월 05:47 KST(weekly, 넓은 생성일 구간), 수동 실행 |
| 사람 판단이 필요한 새 프롬프트 모음 발굴 | Claude 클라우드 Routine 「효과 카탈로그 주간 업데이트」 | 월 08:47 KST |

예약 실행 점검(읽기 전용): `python3 skill/opus-fx-scout/scripts/check_runs.py` — 최근 실행의 원인(schedule/수동)·결과, 예약 실행의 기록, 공개 사이트 status.json 반영 여부를 보여 준다.
겹침: 같은 작업 흐름은 한 번에 하나만 돈다(concurrency). 실행 중에 새 실행이 오면 대기하고, 대기 중인 것이 또 있으면 앞의 대기만 취소된다. 대기했던 실행은 시작할 때 최신 main 으로 갈아타므로 앞 실행의 결과 위에서 이어 간다(2026-10-10 수동 실행 2회 겹침으로 확인). 다른 곳(Routine)이 실행 도중 main 에 push 해 생성 파일이 충돌하면 그 실행은 커밋하지 않고 실패로 끝나며(자료 손실 없음), 다음 실행이 처음부터 다시 한다. 커밋·push 와 Pages 단계는 `skill/opus-fx-scout/scripts/ci/` 의 스크립트이고, 임시 git 저장소와 가짜 gh·curl 로 `tests/test_ci.py` 에서 시험한다(Routine 동시 push, Pages 요청 실패·빌드 실패·사이트 미반영).
재판정 순서: 규칙 버전이 바뀌면 공개 작품 → 새 후보 → 제외됐던 것 → 조건이 모자란 효과·모음 → 보류된 라이브러리·앱 순으로 실행당 최대 175개(REST 예산 350)씩 다시 본다. 전체 재판정에는 여러 날이 걸린다. 실행마다 처리 수와 남은 수를 `status.json` 의 `last_run.rejudged`·`rejudge_left` 와 `discovery/runs/` 기록에 남긴다.
배포 확인: 실행마다 공개 사이트 status.json 의 run_id 가 이번 실행과 같은지 확인한다. 다음 실행은 시작할 때 지난 실행이 실제로 반영됐는지 대조해 `stages.publish` 에 기록하고, 안 됐으면 `missed_run` 과 함께 실패로 적고(성공 시각은 올리지 않음) 이번 커밋·빌드로 회복한다. 화면에는 '지난 실행 공개 누락 — 이번 갱신으로 다시 공개됨'으로 보인다. Pages 확인은 이번 커밋의 빌드만 본다(지난 회차의 실패 빌드가 남아 있어도 새 빌드를 기다림). status.json 은 실행마다 바뀌므로 자료 변경이 없어도 커밋이 하나 생긴다.

수동 실행: Actions → catalog-update → Run workflow, 또는 로컬에서
`GITHUB_TOKEN=$(gh auth token) python3 skill/opus-fx-scout/scripts/pipeline.py --dir . --mode daily`

GitHub 발굴은 주제·키워드 검색어(`discovery/config.json`)를 세 흐름으로 돈다: 누적 별이 많은 저장소, 최근 생성(별 하한 낮음),
최근 갱신. 검색당 1,000개 한도를 넘는 생성일 구간은 반씩 나눠 찾고, 처리한 구간을 `state.json` 에 남겨 다음 실행이 이어 간다.
GitHub 전체를 빠짐없이 모으는 것이 아니다 — 검색어에 걸리고 검색당 1,000개 한도 안에 든 저장소만 본다. 진행 구간은 `discovery/state.json`(검색어별 `until`·`before`), 호출 한도는 인증 검색 30회/분·검색당 1,000개·GITHUB_TOKEN 1,000회/시간이다. 예산(검색·REST·GraphQL 호출 수, 실행 시간)을 넘으면 기다리지 않고 다음 회차로 넘긴다.

자동 공개 조건: 시각 효과와 관련 · 개별 효과나 예제 모음(라이브러리·도구·자료집 제외) · 미리보기 이미지나 데모 링크 · 코드 · 라이선스 표시 ·
원작자 · 별 3개 이상 · 포크·미러·중복 아님. 나머지는 사유와 함께 보류(`candidates.json`), 링크 자료집은 출처 후보로 분류한다.
외부 저장소의 코드는 설치하거나 실행하지 않는다(README·파일 목록·메타데이터만 읽음). 프롬프트는 저장소에 파일로 있을 때만 링크한다.
'최근 상승'은 별 수 이력이 7일 이상 쌓인 저장소의 7일 증가량(증가량 5 이상·별 20 이상)만 순위에 넣는다.
