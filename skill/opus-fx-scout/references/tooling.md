# 구현에 필요한 도구 확인표

추천한 효과를 실제로 만들 때 무엇이 있어야 하는지 사용자에게 보여주고 확인받기 위한 표입니다.
카탈로그의 `level`과 `needs`(find.py `--show`에 표시)를 이 표에 대응시키세요.

## 목차
1. 실행 단계(level)
2. needs별 도구와 확인 방법
3. 플러그인·커넥터를 실제로 찾는 법
4. 사용자에게 보여줄 형식

## 1. 실행 단계(level)

| level | 이름 | 뜻 | 사용자가 할 일 |
|---|---|---|---|
| 1 | 채팅만 | HTML 파일 하나로 끝남 (Canvas, SVG, Three.js, 셰이더, Web Audio) | 없음. claude.ai 채팅의 아티팩트로 바로 보임 |
| 2 | Claude Code | 터미널이 필요함 (MP4 렌더링, npm 패키지, Python 분석, 로컬 파일) | Claude Code 또는 코워크에서 실행 |
| 3 | 외부 프로그램 | 데스크톱 앱 설치 필요 (Blender, Unity 등) | 프로그램 설치 + Claude Code |
| 4 | 외부 AI·API | 유료 생성 AI 호출 (영상·이미지·음성) | API 키, 크레딧 비용 |

level은 원본 작품이 쓴 방식 기준입니다. 같은 효과를 더 가벼운 단계로 낮출 수 있으면
(예: MP4 대신 HTML로 보기, 생성 이미지 대신 코드로 그린 일러스트) 대안으로 함께 제시하세요.
사용자가 원하는 결과물이 "영상 파일"이면 level 1 작품도 MP4로 받으려면 2단계가 됩니다.

## 2. needs별 도구와 확인 방법

| needs | 필요한 것 | 확인 방법 | 비고 |
|---|---|---|---|
| (없음) | 브라우저 | - | HTML 하나 |
| render | Playwright(헤드리스 Chromium) + ffmpeg | `npx playwright --version`, `ffmpeg -version` | 프레임 단위 캡처 후 MP4 인코딩. 대부분 원본이 이 방식 |
| remotion | Node.js 18+ + Remotion | `node -v`, `npx remotion --version` | React로 영상 제작. Remotion 공식 에이전트 스킬이 있는지 검색해 볼 것 |
| node | Node.js + npm (React·Vite·Next) | `node -v` | |
| python | Python 3 + numpy (비트 분석 등) | `python3 -c "import numpy"` | 음악 박자 분석에 자주 쓰임 |
| blender | Blender 설치 | `blender --version` | Blender를 Claude가 조작하는 MCP 서버(오픈소스)도 있음 → 검색 |
| engine | Unity / Unreal / Godot / C++ 빌드 환경 | 각 CLI 버전 확인 | 웹으로 낮출 수 있는지 먼저 검토 |
| figma | Figma 커넥터 | 커넥터 목록 확인 | 디자인 파일을 읽어 그대로 움직이게 하는 작품 |
| genvideo | 영상 생성 AI API (Seedance, Kling, Veo 등) | API 키 보유 여부를 사용자에게 질문 | 크레딧 비용 발생. 실행 전 예상 비용 고지 |
| genimage | 이미지 생성 AI API (Seedream, GPT Image, Magnific·fal 등) | 위와 같음 | 위와 같음 |
| genaudio | 음성·음악 생성 AI (ElevenLabs, Suno 등) | 위와 같음 | 대안: Web Audio로 코드 합성, 무료 음원(Mixkit 등) |
| assets | 사용자 자료 (로고, URL, 사진, 음악, 참고 영상) | 무엇이 필요한지 목록으로 질문 | 저작권: 음악·영상은 상업 이용 가능한지 확인 |

## 3. 플러그인·커넥터를 실제로 찾는 법

플러그인·커넥터·MCP 서버는 자주 바뀌므로 이름을 기억에 의존하지 말고 실행 중인 환경에서 찾습니다.

1. 지금 환경에 도구 검색 기능이 있으면 먼저 씁니다:
   - 플러그인 검색(`SearchPlugins`), 스킬 검색(`SearchSkills`), MCP 레지스트리 검색(`SearchMcpRegistry`)
   - 연결된 커넥터 목록(`ListConnectors`)과 커넥터 추천(`SuggestConnectors`)
   - 설치 제안(`SuggestPluginInstall`)은 사용자가 확인한 뒤에만
   (이름이 다를 수 있으니 ToolSearch로 "plugin", "connector", "mcp"를 검색해 확인)
2. 그런 도구가 없으면 웹 검색으로 "<도구명> MCP server", "<도구명> Claude Code skill"을 찾고,
   공식 저장소인지·최근 업데이트됐는지 확인한 것만 제시합니다.
3. 찾지 못했으면 "검색해 봤지만 확인된 플러그인이 없음"이라고 쓰고, 대신 직접 설치할 도구(npm 패키지 등)를 안내합니다.
   존재를 확인하지 않은 플러그인 이름을 만들어내지 마세요. 사용자가 그 이름으로 찾다가 시간을 버립니다.

설치, API 호출, 비용이 드는 작업은 사용자가 확인하기 전에 실행하지 않습니다.

## 4. 사용자에게 보여줄 형식

추천 작품마다 아래 표를 붙이고, 마지막에 한 번만 묻습니다.

```
**만들려면 필요한 것** · 실행 단계: Claude Code
| 필요한 것 | 왜 | 지금 환경 | 준비 방법 |
|---|---|---|---|
| Playwright + ffmpeg | 30초 MP4로 뽑기 위해 | 확인 필요 | Claude Code에서 `npx playwright install chromium` |
| 로고 SVG, 음악 1곡 | 원본이 사용자 자료를 받음 | 없음 | 직접 준비 (무료 음원: Mixkit) |
| (대안) HTML로만 보기 | MP4가 꼭 필요 없으면 | 바로 가능 | 채팅에서 바로 |
```

"지금 환경" 칸은 실제로 확인한 결과만 씁니다(명령을 돌려봤거나 커넥터 목록에 있음). 확인 못 했으면 "확인 필요".
설치가 필요 없는 항목(브라우저, CDN 라이브러리, 채팅 아티팩트)은 "바로 가능"이라고 써도 됩니다.

지금 환경에 플러그인 검색 도구가 일부만 있으면 있는 것만 쓰고, 없는 도구 때문에 멈추지 마세요.
마지막 질문 예: "어떤 걸로 진행할까요? 필요한 것 중 이미 있는 것과 설치해도 되는 것을 알려주세요."
