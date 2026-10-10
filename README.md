# opus-fx-catalog

Claude(Opus 5.5 등)로 실제 만들어진 모션그래픽·3D·셰이더·인터랙티브 효과의 프롬프트 카탈로그입니다.
`opus-fx-scout` 스킬이 이 저장소를 읽어 결과물에 맞는 효과를 추천하고, 주간 자가서칭이 새 항목을 여기에 커밋합니다.

- `catalog.json` — 항목 전체 (`synced` 날짜 + `items`). 항목마다 원작자 게시물, 영상, 프롬프트 원문 링크, 효과 분류(fx), 필요 도구(needs), 실행 단계(level 1~4)
- `sources.json` — 등록된 소스와 채택 이유

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
