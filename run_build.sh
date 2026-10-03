#!/bin/bash
# Rejection Memory Guard build driver v2: one aider (Qwen via local llama-server) run per step,
# then the full pytest suite, with up to MAX_FIX fix runs. Launch with ./launch_detached.sh
#   START_STEP=05 ./launch_detached.sh      END_STEP=05 limits the run; STOP_ON_FAIL=0 keeps going after a failed step
cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export RMG_OFFLINE=1
MAX_FIX="${MAX_FIX:-4}"
AIDER_TIMEOUT="${AIDER_TIMEOUT:-3600}"
START_STEP="${START_STEP:-01}"
STOP_ON_FAIL="${STOP_ON_FAIL:-1}"
SKIP_STEPS="${SKIP_STEPS:-}"           # e.g. "04c"
BUDGET_BYTES="${BUDGET_BYTES:-30000}"   # message + chat files, ~8.5k tokens; leaves room for whole-file output in a 16k ctx
PY="$PWD/.venv/bin/python"
AIDER="${AIDER_BIN:-$HOME/.aider-venv/bin/aider}"
ts(){ date '+%Y-%m-%d %H:%M:%S %Z'; }
log(){ echo "[$(ts)] $*"; }
wait_llm(){ until curl -sf -m 10 http://127.0.0.1:8080/health >/dev/null; do log "llama-server not healthy; waiting 60s"; sleep 60; done; }

files_for(){ case "$1" in
  01) echo "rmg/__init__.py rmg/models.py tests/__init__.py tests/test_models.py";;
  02) echo "rmg/ledger.py tests/test_ledger.py";;
  03) echo "rmg/extract.py tests/test_extract.py";;
  04) echo "rmg/similarity.py tests/test_similarity.py";;
  04b) echo "rmg/similarity.py tests/test_similarity.py";;
  04c) echo "rmg/ledger.py tests/test_ledger.py";;
  05) echo "rmg/guard.py tests/test_guard_basic.py";;
  06a) echo "rmg/guard.py tests/test_guard_fp.py";;
  06b) echo "rmg/guard.py tests/test_guard_reconsider.py";;
  07) echo "rmg/inject.py tests/test_inject.py";;
  08a) echo "rmg/api.py tests/test_api.py";;
  08b) echo "rmg/cli.py rmg/__main__.py tests/test_cli.py";;
  09) echo "rmg/analytics.py tests/test_analytics.py";;
  10) echo "rmg/web.py tests/test_web.py";;
  10b) echo "rmg/cli.py tests/test_cli.py";;
  11) echo "demo.py tests/test_demo.py";;
  12) echo "README.md pyproject.toml";;
esac; }
reads_for(){ case "$1" in   # most important first; trimmed from the end to fit BUDGET_BYTES
  01|02|03|04) echo "SPEC.md";;
  04b|04c) echo "";;
  05) echo "rmg/similarity.py rmg/ledger.py rmg/models.py";;
  06a|06b) echo "";;
  07) echo "";;
  08a) echo "";;
  08b) echo "rmg/api.py rmg/inject.py";;
  09) echo "rmg/ledger.py rmg/api.py";;
  10) echo "rmg/ledger.py rmg/models.py";;
  10b) echo "";;
  11) echo "";;
  12) echo "SPEC.md rmg/api.py";;
esac; }
fmt_for(){ case "$1" in 04b|06a|06b|10b) echo diff;; *) echo whole;; esac; }
fsize(){ [ -f "$1" ] && wc -c < "$1" | tr -d ' ' || echo 0; }

# build aider args: editable files then reads that fit in the budget
build_args(){ # $1 msgfile, $2 editable list, $3 read list
  ARGS=(); local total; total=$(fsize "$1")
  for f in $2; do mkdir -p "$(dirname "$f")"; ARGS+=(--file "$f"); total=$((total + $(fsize "$f"))); done
  for f in $3; do [ -f "$f" ] || continue; local s; s=$(fsize "$f")
    if [ $((total + s)) -le "$BUDGET_BYTES" ]; then ARGS+=(--read "$f"); total=$((total + s)); else log "budget: skipping read $f"; fi; done
  log "chat payload ~${total} bytes"
}

run_aider(){ local msg="$1"; shift; wait_llm; log "aider start: $msg $*"
  perl -e 'alarm shift; exec @ARGV' "$AIDER_TIMEOUT" "$AIDER" --yes-always --no-auto-commits --no-dirty-commits \
    --no-show-model-warnings --no-check-update --no-analytics --no-pretty --no-stream --no-fancy-input \
    --map-tokens 1024 --edit-format "$EDIT_FMT" --message-file "$msg" "$@" < /dev/null
  log "aider exit rc=$?"
  # clean junk files created when the model emits prose as a filename
  git ls-files --others --exclude-standard | grep -vE '^(rmg|tests|steps)/|^(demo\.py|README\.md|pyproject\.toml)$' | while IFS= read -r j; do log "removing junk file: $j"; rm -f -- "$j"; done
  [ -d "./~" ] && rm -rf -- "./~"
}

run_tests(){ "$PY" -m pytest -q --tb=short -p no:cacheprovider tests > .last_pytest.txt 2>&1; local rc=$?
  tail -40 .last_pytest.txt; return $rc; }
empty_files(){ for f in $1; do [ -s "$f" ] || echo "$f"; done; }

log "===== build v2 start (START_STEP=$START_STEP END_STEP=${END_STEP:-} MAX_FIX=$MAX_FIX) ====="
SUMMARY=""
for prompt in steps/[0-9][0-9]*_*.md; do
  base="$(basename "$prompt")"; step="${base%%_*}"
  [[ "$step" < "$START_STEP" ]] && continue
  [[ -n "${END_STEP:-}" && "$step" > "$END_STEP" ]] && break
  [[ " $SKIP_STEPS " == *" $step "* ]] && { log "skipping step $step"; continue; }
  log "########## STEP $step: $prompt ##########"
  build_args "$prompt" "$(files_for "$step")" "$(reads_for "$step")"
  EDIT_FMT="$(fmt_for "$step")"
  pre_rev="$(git stash create 2>/dev/null)"; [ -n "$pre_rev" ] || pre_rev="$(git rev-parse HEAD)"
  run_aider "$prompt" "${ARGS[@]}"
  status=FAIL
  for attempt in $(seq 0 "$MAX_FIX"); do
    log "pytest (step $step, attempt $attempt)"
    emp="$(empty_files "$(files_for "$step")")"
    if git diff --quiet "$pre_rev" -- $(files_for "$step") 2>/dev/null && [ -z "$(git ls-files --others --exclude-standard -- $(files_for "$step"))" ]; then
      emp="${emp} (NO CHANGES were applied in this step; your previous reply was not applied, likely because it was too long or malformed. Make the required edits now, keeping the reply short: use small SEARCH/REPLACE blocks.)"; fi
    if [ -z "$emp" ] && run_tests; then status=PASS; break; fi
    [ -n "$emp" ] && log "empty files after step: $emp"
    [ "$attempt" -ge "$MAX_FIX" ] && break
    fixmsg=".fix_${step}_${attempt}.md"
    extra=""
    for f in $(grep -oE 'rmg/[A-Za-z0-9_]+\.py' .last_pytest.txt | sort -u); do
      [[ " $(files_for "$step") " == *" $f "* ]] || extra="$extra $f"; done
    { echo "Step $step is not finished. Fix it. Rules: write the product code so the tests pass; only change a test if it clearly contradicts the instructions below; never delete or weaken tests. Use small SEARCH/REPLACE blocks for existing files; write new or empty files in full. Never leave placeholders. Keep the reply short."
      [ -n "$emp" ] && echo "Problem: these files are empty or unchanged: $emp"
      [ -n "$extra" ] && echo "The failure involves$extra, which is added as editable: fix the bug there if that is where it is."
      echo; echo "Step instructions:"; cat "$prompt"
      echo; echo "pytest output:"; echo '```'; grep -vE '^\s*$' .last_pytest.txt | tail -60; echo '```'; } > "$fixmsg"
    build_args "$fixmsg" "$(files_for "$step") $extra" "$(reads_for "$step")"
    EDIT_FMT=diff
    run_aider "$fixmsg" "${ARGS[@]}"
  done
  log "STEP $step RESULT: $status ($(tail -1 .last_pytest.txt 2>/dev/null))"
  SUMMARY="$SUMMARY\nstep $step: $status"
  git add -A >/dev/null 2>&1; git commit -qm "step $step ($status) by qwen/aider" >/dev/null 2>&1 && log "committed step $step"
  if [ "$status" = FAIL ] && [ "$STOP_ON_FAIL" = 1 ]; then log "stopping: step $step failed (STOP_ON_FAIL=1)"; break; fi
done
log "===== build finished ====="
echo -e "SUMMARY:$SUMMARY"
