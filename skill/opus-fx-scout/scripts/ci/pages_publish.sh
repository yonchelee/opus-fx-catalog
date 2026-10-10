#!/usr/bin/env bash
# Pages 빌드 요청과 공개 확인 (Actions catalog-update 의 배포 단계). 시험: tests/test_ci.py
# 사용: pages_publish.sh <저장소 owner/name> <run_id>
# 실패하면 exit 1 → 실행이 실패로 남는다. 다음 회차 pipeline.py 가 사이트 run_id 를 대조해 '반영되지 않음'을 기록하고 다시 배포한다.
set -u
repo="$1"; run="$2"
site="${SITE:-https://yonchelee.github.io/opus-fx-catalog/}"
sha=$(git rev-parse HEAD)
gh api -X POST "repos/$repo/pages/builds" >/dev/null || echo "빌드 요청 실패 — push 로 시작된 빌드를 기다림"
s=""
for i in $(seq 1 "${PAGES_TRIES:-30}"); do
  s=$(gh api "repos/$repo/pages/builds/latest" --jq '.status + " " + .commit' || true)
  echo "$s"
  # 이번 커밋의 빌드만 본다. 지난 커밋의 실패 빌드가 아직 '최신'이면 새 빌드를 기다린다.
  case "$s" in "built $sha") break;; "errored $sha") echo "Pages 빌드 실패"; exit 1;; esac
  sleep "${PAGES_SLEEP:-20}"
done
case "$s" in "built $sha") ;; *) echo "Pages 빌드를 확인하지 못함 ($s)"; exit 1;; esac
rid=""
for i in $(seq 1 "${LIVE_TRIES:-12}"); do
  rid=$(curl -s "${site}status.json?v=$RANDOM$i" | python3 -c "import json,sys;print(json.load(sys.stdin).get('run_id'))" 2>/dev/null || true)
  [ "$rid" = "$run" ] && { echo "공개 사이트 확인: status.json run_id=$rid"; break; }
  sleep "${LIVE_SLEEP:-15}"
done
[ "$rid" = "$run" ] || { echo "공개 사이트 status.json 이 이번 실행이 아님 ($rid)"; exit 1; }
code=$(curl -s -o /dev/null -w '%{http_code}' "${site}github.json?v=$RANDOM")
[ "$code" = 200 ] || { echo "github.json $code"; exit 1; }
