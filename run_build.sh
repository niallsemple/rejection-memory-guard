#!/bin/bash
# Rejection Memory Guard build driver: one aider (Qwen via local llama-server) run per step,
# then pytest, with up to MAX_FIX fix loops. Run with:
#   nohup caffeinate -dimsu ./run_build.sh >> build.log 2>&1 &
# Resume from a step: START_STEP=05 ./run_build.sh ...
cd "$(dirname "$0")" || exit 1
REPO="$(pwd)"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export RMG_OFFLINE=1          # tests must not depend on the server
MAX_FIX="${MAX_FIX:-4}"
AIDER_TIMEOUT="${AIDER_TIMEOUT:-5400}"   # seconds per aider run
START_STEP="${START_STEP:-01}"
PY="$REPO/.venv/bin/python"
AIDER="${AIDER_BIN:-$HOME/.aider-venv/bin/aider}"

ts(){ date '+%Y-%m-%d %H:%M:%S %Z'; }
log(){ echo "[$(ts)] $*"; }

wait_llm(){
  until curl -sf -m 10 http://127.0.0.1:8080/health >/dev/null; do
    log "llama-server not healthy; waiting 60s"; sleep 60; done
}

# editable files and read-only context per step
files_for(){ case "$1" in
  01) echo "rmg/__init__.py rmg/models.py tests/__init__.py tests/test_models.py";;
  02) echo "rmg/ledger.py tests/test_ledger.py";;
  03) echo "rmg/extract.py tests/test_extract.py";;
  04) echo "rmg/similarity.py tests/test_similarity.py";;
  05) echo "rmg/guard.py tests/test_guard_basic.py";;
  06) echo "rmg/guard.py tests/test_guard_fp.py";;
  07) echo "rmg/inject.py tests/test_inject.py";;
  08) echo "rmg/api.py rmg/cli.py rmg/__main__.py tests/test_api_cli.py";;
  09) echo "rmg/analytics.py tests/test_analytics.py rmg/api.py rmg/cli.py";;
  10) echo "rmg/web.py tests/test_web.py rmg/cli.py";;
  11) echo "demo.py tests/test_demo.py rmg/api.py";;
  12) echo "README.md pyproject.toml";;
esac; }
reads_for(){ case "$1" in
  01) echo "";;
  02) echo "rmg/models.py";;
  03) echo "rmg/models.py";;
  04) echo "";;
  05) echo "rmg/models.py rmg/ledger.py rmg/similarity.py";;
  06) echo "rmg/models.py rmg/similarity.py tests/test_guard_basic.py";;
  07) echo "rmg/models.py rmg/ledger.py rmg/similarity.py";;
  08) echo "rmg/models.py rmg/ledger.py rmg/guard.py rmg/inject.py rmg/extract.py";;
  09) echo "rmg/ledger.py rmg/models.py";;
  10) echo "rmg/ledger.py rmg/models.py rmg/similarity.py";;
  11) echo "rmg/inject.py rmg/guard.py rmg/extract.py rmg/similarity.py";;
  12) echo "rmg/api.py rmg/cli.py";;
esac; }

run_aider(){ # $1 msgfile, rest: --file/--read args
  local msg="$1"; shift
  wait_llm
  log "aider start: $msg $*"
  perl -e 'alarm shift; exec @ARGV' "$AIDER_TIMEOUT" \
    "$AIDER" --yes-always --no-auto-commits --no-dirty-commits --no-show-model-warnings \
      --no-check-update --no-analytics --no-pretty --no-stream --no-fancy-input \
      --message-file "$msg" "$@" < /dev/null
  local rc=$?
  log "aider exit rc=$rc"
}

run_tests(){
  "$PY" -m pytest -q -x --timeout=120 -p no:cacheprovider tests > .last_pytest.txt 2>&1
  local rc=$?
  cat .last_pytest.txt | tail -60
  return $rc
}

log "===== build start (START_STEP=$START_STEP, MAX_FIX=$MAX_FIX) ====="
SUMMARY=""
for prompt in steps/[0-9][0-9]_*.md; do
  step="$(basename "$prompt" | cut -c1-2)"
  [[ "$step" < "$START_STEP" ]] && continue
  [[ -n "${END_STEP:-}" && "$step" > "$END_STEP" ]] && break
  log "########## STEP $step: $prompt ##########"
  args=(); for f in $(files_for "$step"); do mkdir -p "$(dirname "$f")"; args+=(--file "$f"); done
  args+=(--read SPEC.md); for f in $(reads_for "$step"); do [ -f "$f" ] && args+=(--read "$f"); done
  run_aider "$prompt" "${args[@]}"
  status=FAIL
  for attempt in $(seq 0 "$MAX_FIX"); do
    log "pytest (step $step, attempt $attempt)"
    if run_tests; then status=PASS; break; fi
    [ "$attempt" -ge "$MAX_FIX" ] && break
    fixmsg=".fix_${step}_${attempt}.md"
    { echo "The pytest suite is failing after step $step. Fix the product code (and tests only if a test is clearly wrong about the spec; never delete or weaken tests to make them pass). Keep every existing test passing."
      echo; echo "Original step instructions:"; cat "$prompt"
      echo; echo "pytest output (tail):"; echo '```'; tail -120 .last_pytest.txt; echo '```'; } > "$fixmsg"
    fargs=("${args[@]}")
    for f in $(grep -oE '(rmg|tests)/[A-Za-z0-9_]+\.py' .last_pytest.txt | sort -u | head -6); do
      [[ " ${fargs[*]} " == *" --file $f "* ]] || fargs+=(--file "$f"); done
    run_aider "$fixmsg" "${fargs[@]}"
  done
  log "STEP $step RESULT: $status"
  SUMMARY="$SUMMARY\nstep $step: $status"
  git add -A >/dev/null 2>&1
  git commit -qm "step $step ($status) by qwen/aider" >/dev/null 2>&1 && log "committed step $step"
done
log "===== build finished ====="
echo -e "SUMMARY:$SUMMARY"
