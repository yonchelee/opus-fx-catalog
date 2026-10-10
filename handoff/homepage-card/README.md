# 홈페이지 카드 추가 인계 — 효과 갤러리

**작성:** 2026-10-10, 클라우드 세션 · **적용 위치:** 맥미니 로컬 홈페이지 저장소 → Cloudflare Pages `homepage` (Direct Upload)

클라우드 세션은 홈페이지 원본을 볼 수 없었습니다(맥미니 로컬 저장소, GitHub 원격 없음). 그래서 여기에는 **카드 자료와 변경 원칙**만 있고, 실제 마크업은 맥미니에서 기존 카드 형식을 보고 맞춥니다.

## 이 폴더
| 파일 | 내용 |
|---|---|
| `card.json` | 카드 문구·링크·태그·날짜·출처 표기 (한 곳에서 복사) |
| `cover-1200x630.png` | 가로형 표지 (공유 미리보기 비율) |
| `cover-600x315.png` | 가로형 작은 버전 |
| `cover-800x800.png` | 정사각형 표지 |

받는 법 (맥미니):
```bash
mkdir -p /tmp/fx-card && cd /tmp/fx-card
for f in README.md card.json cover-1200x630.png cover-600x315.png cover-800x800.png; do
  curl -fsSLO "https://raw.githubusercontent.com/yonchelee/opus-fx-catalog/main/handoff/homepage-card/$f"
done
```

## 적용 전 확인 (하나라도 아니면 멈추고 사용자에게 보고)
1. 갤러리 링크가 열리는지: `curl -sI https://yonchelee.github.io/opus-fx-catalog/ | head -1` 가 `200` (Pages는 2026-10-10에 켜졌고 빌드 성공 확인됨)
   - 404면 GitHub Pages가 아직 꺼져 있는 것 → 사용자에게 저장소 Settings → Pages에서 `main` / `/ (root)` 저장을 요청
2. 홈페이지 저장소가 `main-release` 브랜치이고 작업 트리가 깨끗한지: `git status`, `git branch --show-current`
3. 지금 배포된 사이트가 열리는지: `curl -sI https://www.yonchelee.com/ | head -1`, `curl -sI https://yonchelee.com/ | head -1`
   - 참고: 클라우드 세션에서 났던 `getaddrinfo ENOTFOUND`는 그 웹 조회 도구가 `example.com`도 찾지 못하는 환경 문제였습니다. 사이트 DNS 문제의 증거가 아니니 무시해도 됩니다

## 적용 순서
1. **기존 작업 카드 형식 찾기.** 기존 작업 제목 하나로 검색해 카드가 어디서 오는지 확인합니다(HTML 직접 / JSON·YAML·MD 데이터 / 컴포넌트).
   예: `grep -rn "<기존 작업 제목>" --include=*.{html,json,md,mdx,yml,yaml,js,ts,tsx,astro,vue,svelte} .`
2. **같은 형식으로 카드 1개 추가.** 새 형식이나 새 스타일을 만들지 말고, 기존 카드를 복제해 `card.json` 값으로 바꿉니다.
   - 필드가 기존 카드에 없는 것(예: credits)은 넣지 않습니다. 설명 길이도 기존 카드에 맞춰 `description` 또는 `description_short` 중 고릅니다
   - 이미지: 기존 카드 비율에 맞는 표지를 고르고, 기존 이미지 폴더·파일명 규칙대로 복사합니다(예: `effect-gallery.png`)
   - 순서: 기존 정렬 규칙(최신순 등)을 따릅니다. 규칙이 없으면 맨 앞
   - 링크는 새 탭으로 여는지 등 기존 카드 동작을 그대로 따릅니다
3. **로컬 미리보기.** 기존에 쓰던 빌드·미리보기 방법으로 확인합니다(package.json scripts, Makefile, README 참고). 확인할 것:
   - 카드가 다른 카드와 같은 크기·정렬로 보이는지, 이미지가 잘리지 않는지
   - 휴대폰 너비(390px)에서 깨지지 않는지, 다크 모드가 있으면 다크 모드에서도
   - 카드 링크가 갤러리로 열리는지
4. **커밋.** 이 저장소의 기존 커밋 메시지 형식을 따릅니다. 예: `works: add 효과 갤러리 card`
5. **배포는 사용자 확인 후.** 확인 받을 때 보여줄 것: 바뀐 파일 목록, 미리보기 스크린샷(데스크톱·모바일).
   - 배포 방법은 **지금까지 쓰던 방법을 그대로** 씁니다. 저장소의 배포 스크립트, `wrangler.toml`, 셸 기록에서 확인하세요
   - wrangler로 Direct Upload를 해 왔다면 형태는 `npx wrangler pages deploy <빌드 출력 폴더> --project-name homepage --branch <프로덕션 브랜치>` 입니다. **프로덕션 브랜치 이름은 Cloudflare 대시보드 homepage → Settings에서 확인**하고 추측하지 마세요(`main-release`가 로컬 브랜치 이름이라고 해서 Pages 프로덕션 브랜치와 같다고 단정하지 말 것)
   - 대시보드에서 폴더를 끌어다 올려 왔다면, 빌드 출력 폴더 위치만 알려 드리고 업로드는 사용자가 합니다
6. **배포 후 확인.** www.yonchelee.com과 yonchelee.com 둘 다에서 카드가 보이고 링크가 열리는지 확인합니다. Cloudflare 캐시로 바로 안 보이면 배포 미리보기 주소(`*.pages.dev`)에서 먼저 확인합니다.

## 하지 말 것
- 새 Pages 프로젝트 만들기, 도메인·DNS 설정 바꾸기
- 확인 없이 프로덕션 배포
- 카드 외 다른 부분 수정 (발견한 문제는 보고만)

## 끝나면 보고할 것
- 카드가 들어간 파일과 커밋
- 배포 여부와 방법, 배포 URL
- 적용 전 확인 1~3의 결과
