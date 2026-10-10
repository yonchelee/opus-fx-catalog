#!/usr/bin/env bash
# 커밋·push (Actions catalog-update 의 커밋 단계). 시험: tests/test_ci.py
# 사용: commit_push.sh "<커밋 메시지>"   출력: GITHUB_OUTPUT 에 pushed=true|false
# push 가 거부되면 최신 main 위로 rebase 해 최대 3번 다시 한다.
# rebase 가 충돌하면(다른 작업이 같은 생성 파일을 고친 경우) 중단하고 실패로 끝낸다 — main 의 남의 변경은 그대로 두고,
# 이번 회차 결과는 버린다. 수집 진행 위치(state.json)도 함께 버려지므로 다음 회차가 같은 구간을 다시 한다.
set -u
out="${GITHUB_OUTPUT:-/dev/null}"
git add -A
if git diff --cached --quiet; then echo "변경 없음"; echo "pushed=false" >> "$out"; exit 0; fi
git commit -qm "$1"
for i in 1 2 3; do
  if git push origin HEAD:main; then echo "pushed=true" >> "$out"; exit 0; fi
  git pull --rebase origin main || { git rebase --abort; echo "rebase 충돌 — 이번 결과는 버리고 다음 회차로"; echo "pushed=false" >> "$out"; exit 1; }
  sleep $((i * ${PUSH_SLEEP:-5}))
done
echo "push 3번 실패"; echo "pushed=false" >> "$out"
exit 1
