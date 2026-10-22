# 새 효과 자가서칭

카탈로그는 스냅샷이라 시간이 지나면 낡습니다. 두 단계로 갱신합니다.
1단계(등록된 소스 동기화)는 스크립트가 하고, 2단계(새 소스 발굴)는 Claude가 웹 검색으로 합니다.

## 저장 위치

카탈로그는 세 겹입니다. 스킬에 든 스냅샷(bundle) → 공유 저장소 `yonchelee/opus-fx-catalog`(remote) → 이 세션의 임시 추가분(overlay).
find.py는 셋을 합쳐 쓰고, `find.py --stats` 첫 줄에 어느 층이 몇 날짜 기준인지 나옵니다.
**오래 남는 곳은 remote 저장소뿐**입니다. 자가서칭 결과는 가능하면 저장소에 커밋하세요.

- **푸시할 수 있는 환경** (Claude Code·클라우드 세션, 예약 작업): 저장소를 clone하고 `--out`으로 쓴 뒤 커밋·푸시
  ```bash
  git clone --depth 1 https://github.com/yonchelee/opus-fx-catalog /tmp/fxrepo
  python3 scripts/sync.py --out /tmp/fxrepo            # 등록된 소스 동기화 + 전체 카탈로그 기록
  cd /tmp/fxrepo && git add -A && git commit -m "catalog: +N (소스명)" && git push
  ```
  새 소스 등록·수동 추가도 `--out /tmp/fxrepo`를 붙이면 저장소 쪽에 기록됩니다
  (`--register src.json --out ...`, `--add entries.json --out ...`). 커밋 메시지에 무엇을 왜 넣었는지 한 줄 남깁니다.
- **푸시할 수 없는 환경** (claude.ai 채팅 등): `--out` 없이 실행하면 overlay에만 저장됩니다.
  이 경우 "이번 대화에서만 반영되고, 주간 자동 업데이트가 저장소에 남긴다"고 사용자에게 밝힙니다.
- 저장소를 읽지 못하면(네트워크 차단 등) bundle만으로 동작합니다. 그 사실과 날짜를 답변에 밝힙니다.

## 편집 데이터는 건드리지 않는다

`editorial.json`은 사람이 쓰는 편집 정보(한국어 제목·설명·용도·추천·검증 기록·적용 가이드·검색 동의어)입니다.
`sync.py`는 이 파일을 쓰지 않습니다. 자가서칭·주간 업데이트에서도 손대지 마세요.
`sync.py --out`은 끝에 `build_site.py`를 불러 작품·용도 정적 페이지(`fx/`, `use/`)와 `sitemap.xml`을 다시 만듭니다.
생성된 파일도 함께 커밋합니다. `git add -A`면 됩니다.
편집 정보의 키는 catalog.json의 id와 정확히 같아야 합니다. 원본에서 사라진 id는 연결되지 않고 경고만 나옵니다.

## 자동 실행이 맡는 것과 사람이 맡는 것

- **GitHub Actions(매일·매주)**: 등록 출처 동기화(`sync.py --out`)와 GitHub 공개 저장소 키워드·기간별 탐색(`discover.py`)을 `pipeline.py` 로 돌리고 커밋·배포한다.
  클라우드 Routine 에서는 `sync.py` 를 다시 돌리지 않는다(중복 실행·커밋 충돌 방지).
- **클라우드 Routine(매주 월)**: 아래 2단계(새 프롬프트 모음 발굴)만 한다. 발굴 결과 `discovery/candidates.json` 의 `status: source`(링크 자료집)도 다음 출처 후보로 함께 본다.

## 1단계: 등록된 소스 동기화

```bash
python3 scripts/sync.py --dry-run   # 무엇이 새로 들어올지 보기
```
그다음 위 "저장 위치"에 맞게 `--out` 여부를 정해 실행합니다. 등록된 소스 목록은 bundle과 저장소의 sources.json을 합친 것입니다.

## 2단계: 새 소스 발굴

검색어 예시 (모델 이름은 최신으로 바꿔서):
- `awesome opus 5.5 videos prompts github`
- `claude opus motion graphics prompt collection`
- `claude code remotion prompt showreel`
- `"made with claude" three.js shader prompt`
- GitHub 저장소 검색: `awesome claude video`, `opus prompts motion`, 최근 업데이트 순
- 새 모델이 나왔다면 `awesome-opus6-videos`처럼 같은 패턴의 저장소가 생겼는지 확인

새 소스로 받아들이는 기준 (모두 만족):
1. 공개되어 있고 출처(작성자 링크)가 붙어 있음
2. 프롬프트 전문이 상당수 있음. 결과 영상만 모은 곳은 효과 참고용일 뿐 프롬프트 사전에는 쓸모가 적음
3. 어떤 모델로 만들었는지 밝혀져 있음
4. 기존 소스와 대부분 겹치지 않음 (작성자·게시물 URL로 대조)

이미 검토한 곳:
- yihui-dev/awesome-opus5-5-videos: 채택 (메인, 475개, 자동 동기화)
- Li-Evan/awesome-opus-5.5-video-prompts: 채택 (334개 원문 대조, CC BY 4.0, yihui와 안 겹치는 133개 반영, 수동)
- LeaddeOpenLab/awesome-opus-5-5-video-prompts: 채택 (2026-10-22, 사용자 승인) — 사례 파일에 프롬프트 공개 표기가 생겨 `full_original` 195건만 자동 동기화(`type: case_library`, 다른 출처와 겹치는 16건 제외). `fragment` 533건은 받지 않음. 라이선스 파일 없음(RIGHTS.md: 원작자 소유)이라 미리보기는 원작자 X 주소만 씀
- X-RayLuan, guanmo-ai, HiAPIAI, athemeroy의 모음: 보류
- eastling(전부 중복), adela0414(원문이 아니라 다시 쓴 브리프), real-leo·BeatAPI(링크만 모음): 제외
- zhuyansen 모음(940작품 중 전문 91개), opusvideo 모음(46개, 프롬프트 대부분 없음): 보류

보류한 곳은 다음 자가서칭 때 먼저 다시 봅니다. 상태가 바뀌었으면(전문 추가, 출처 명시) 채택합니다.

GitHub 검색 CLI가 막혀 있으면 GitHub 커넥터의 저장소 검색이나 웹 검색으로 대신합니다.
후보는 실제로 열어 본 것만 보고합니다. 겹침은 X 게시물 ID(status 뒤 숫자)로 대조하면 정확합니다.

### 받아들인 소스를 넣는 법
- **같은 형식의 JSON이 있으면** (slug, author, post_url, prompt, tech_tags ...): 소스 정의를 만들어 등록
  ```bash
  cat > /tmp/src.json <<'J'
  {"id":"newsrc","name":"owner/repo","type":"videos_json","repo":"owner/repo","branch":"main",
   "path":"data/videos.json","prompt_url_tpl":"https://github.com/owner/repo/blob/main/prompts/{slug}.md",
   "model":"Opus 5.5","status":"active","note":"왜 채택했는지 한 줄"}
  J
  python3 scripts/sync.py --register /tmp/src.json && python3 scripts/sync.py
  ```
- **게시물별 JSON 사례 파일이 있으면** (LeaddeOpenLab 형식, `data/library/<게시물 id>.json`): `"type":"case_library"`, `"path":"data/library/*.json"`, `"filter":{"prompt_status":["full_original"]}` 로 등록. `scripts/case_library.py`가 폴더만 부분 clone 해서 읽고, 분류·태그를 카탈로그 어휘로 바꾼다
- **형식이 다르면** (YAML, README 목록, 웹페이지): 소스 정의는 `"type":"manual","status":"manual"`로 등록하고
  (sync.py가 자동으로 받지 않는다는 뜻), 항목을 직접 읽어 아래 형태로 정리한 뒤 `--add`
  ```json
  [{"source":"newsrc","slug":"author-postid","author":"...","post_url":"...","prompt":"전문",
    "prompt_partial":false,"tech_tags":["threejs"],"category":"3d","added":"YYYY-MM-DD","model":"Opus 5.5"}]
  ```
  `python3 scripts/sync.py --add /tmp/entries.json`
  `category`는 motion / explainer / 3d / interactive 중 하나로 맞춥니다(원본 분류명을 그대로 쓰지 말 것).
  `added`는 카탈로그에 넣은 날짜입니다. 게시 날짜를 알면 보고서에는 따로 적으세요.
  프롬프트는 원문 그대로 옮기고, 요약하거나 고쳐 쓰지 않습니다. 원작자 링크를 꼭 남깁니다.

## 보고 형식

```
**새로 들어온 효과** (지난 동기화 YYYY-MM-DD 이후 N개)
- "새로 게시된 작품"과 "원래 있었는데 카탈로그에 새로 들어온 작품"을 구분해서 씁니다
- 효과별 개수 변화: 3D +4, 셰이더 +2 ...
- 사용자 작업에 맞을 만한 것 2~3개: 한 줄 이유 + 링크
- 새로 찾은 소스: 이름 · 채택/보류 · 이유
```
신작이 없으면 "새 항목 없음"이라고 짧게 끝냅니다.
