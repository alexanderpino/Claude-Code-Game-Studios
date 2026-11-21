#!/bin/bash

# --- work from the project root ----------------------------------------------
# Every path below is repo-relative, so a hook invoked with a working directory
# that is not the repo root would silently read and write the WRONG TREE --
# returning a near-empty result instead of the session-recovery block, and
# creating stray trees such as docs/production/session-logs/ on write.
#
# PRECEDENCE IS LOAD-BEARING. A cwd that IS a project root carries real
# information and must win: a caller sitting inside another project means that
# project, not this one. Resolving to the script's own location first would
# override them. So, in order:
#   1. cwd holds project.yaml   -> cwd   (a project root)
#   2. cwd holds .claude/       -> cwd   (a project root not yet configured),
#      unless cwd is itself named .claude: a stray .claude/.claude/ would
#      make .claude/ a root, and the hooks would write .claude/production/
#   3. CLAUDE_PROJECT_DIR       -> that  (populated in the hook environment),
#      unless it names a .claude folder, for the same reason as rule 2
#   4. this script's location   -> <root>/.claude/hooks/../.. by construction
# Rule 4 always works and needs no environment at all; rules 1-2 stop it from
# overriding a caller that legitimately means somewhere else.
#
# NOT an upward search: that resolves a nested project to its parent's config.
if [ -f "project.yaml" ] || { [ -d ".claude" ] && [ "${PWD##*/}" != ".claude" ]; }; then
  CCGS_ROOT="$PWD"
elif [ -n "${CLAUDE_PROJECT_DIR:-}" ] && [ -d "${CLAUDE_PROJECT_DIR}" ] && case "${CLAUDE_PROJECT_DIR%/}" in */.claude|*\\.claude) false ;; *) true ;; esac; then
  CCGS_ROOT="$CLAUDE_PROJECT_DIR"
else
  CCGS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
fi
[ -n "$CCGS_ROOT" ] && cd "$CCGS_ROOT" 2>/dev/null || true

# Claude Code PreCompact hook: log the compaction (and, on a Custom-engine
# project, the engine context -- see below). Nothing else.
#
# PRINTS NOTHING, ON PURPOSE. Claude Code writes PreCompact stdout to the debug
# log and discards its systemMessage (hooks documentation), so a state summary
# printed here reached no one -- and gathering it cost git and grep spawns on
# every compaction. What survives a compaction is the file on disk:
# SessionStart fires again with source `compact`, and session-start.sh shows
# the CHECKPOINT from production/session-state/active.md then.

# features.session_state: off => this hook is a no-op. Default `on`; see
# session_state_enabled() in yaml-helper.sh.
if [ -f .claude/hooks/yaml-helper.sh ]; then
    . .claude/hooks/yaml-helper.sh
    session_state_enabled || exit 0
fi

SESSION_LOG_DIR="production/session-logs"
mkdir -p "$SESSION_LOG_DIR" 2>/dev/null
echo "Context compaction occurred at $(date)." \
    >> "$SESSION_LOG_DIR/compaction-log.txt" 2>/dev/null

# Custom engine (engine.name: Custom): also log the engine context that
# session-start.sh re-injects after the compaction -- frame budget, Accepted
# ADRs, whether memory-invariants.md exists -- so the log shows what the
# session was working against. Same caps as session-start.sh; nothing printed.
# Verbose build and profiler logs are NOT preserved by either hook: keep the
# numbers that matter in a file (a /benchmark-report, active.md).
_PC_ENG=""
if command -v _yh_engine_name >/dev/null 2>&1; then
    _yaml_helper_set_root
    _yh_engine_name
    _PC_ENG=$(printf '%s' "$_YH_ENAME" | tr '[:upper:]' '[:lower:]')
fi
if [ "$_PC_ENG" = "custom" ]; then
    {
        echo "  Engine context (Custom):"
        # An unset key prints nothing, so the default is applied to the value,
        # not by sed (which never sees a line to rewrite).
        _PC_FPS=$(get_effective_yaml_key performance.target_framerate 2>/dev/null)
        _PC_FBM=$(get_effective_yaml_key performance.frame_budget_ms 2>/dev/null)
        echo "    frame budget: target_framerate ${_PC_FPS:-NOT SET} / frame_budget_ms ${_PC_FBM:-NOT SET}"
        # The ADR location is docs.adr_dir/docs.adr_glob (adr_files, yaml-helper.sh).
        _PC_ADRS=""
        command -v adr_location >/dev/null 2>&1 && adr_location && _PC_ADRS=$(adr_files)
        if [ ! -f .claude/scripts/adr-status.sh ]; then
            echo "    accepted ADRs: NOT ASSESSED (.claude/scripts/adr-status.sh is missing)"
        elif ! command -v adr_files >/dev/null 2>&1; then
            echo "    accepted ADRs: NOT ASSESSED (.claude/hooks/yaml-helper.sh is missing)"
        elif [ -n "$_YH_ADR_WHY" ]; then
            echo "    accepted ADRs: NOT ASSESSED ($_YH_ADR_WHY)"
        elif [ -z "$_PC_ADRS" ]; then
            echo "    accepted ADRs: none (no $_YH_ADR_DIR/$_YH_ADR_GLOB)"
        else
            _PC_ACC=$(bash .claude/scripts/adr-status.sh --root . 2>/dev/null \
                      | awk -F'\t' '$1 == "ADR" && $4 == "Accepted" { print $3 }')
            _PC_N=0
            [ -n "$_PC_ACC" ] && _PC_N=$(printf '%s\n' "$_PC_ACC" | wc -l | tr -d ' ')
            echo "    accepted ADRs ($_PC_N):"
            if [ "$_PC_N" -gt 0 ]; then
                printf '%s\n' "$_PC_ACC" | head -15 | tr '\n' '\0' \
                    | xargs -0 awk 'FNR == 1 { if (f != "" && !d) print f; d = 0; f = FILENAME }
                                    !d && FNR <= 5 && /^# / { sub(/^# /, ""); print; d = 1 }
                                    END { if (f != "" && !d) print f }' 2>/dev/null \
                    | tr -d '\r' | sed 's/^/      /'
                [ "$_PC_N" -gt 15 ] && echo "      ... $((_PC_N - 15)) more"
            fi
        fi
        if [ -f docs/architecture/memory-invariants.md ]; then
            echo "    memory invariants: docs/architecture/memory-invariants.md present"
        else
            echo "    memory invariants: absent"
        fi
        echo "    not preserved: verbose build and profiler logs"
    } >> "$SESSION_LOG_DIR/compaction-log.txt" 2>/dev/null
fi

exit 0
