#!/usr/bin/env bash
# Copy Claude Code Game Studios into a project: a new folder or an existing
# repository. scripts/adopt.ps1 does the same in PowerShell; ADOPTING.md is the
# guide, and studio-tests/test_adopt_scripts.py checks that both agree.
#
# Usage: bash scripts/adopt.sh <target-dir> [--dry-run]
#
# Adds and overwrites the framework-owned files below, and never deletes a file.
# Keeps the project's own .claude/settings.json, .claude/agent-models.yaml,
# technical-preferences.md, CLAUDE.md, AGENTS.md and project.yaml. Checks every
# path it would write before writing any, and refuses a link, a folder where a
# file goes, or a read-only file it would change. No network and no git.
# Exit: 0 done, 1 refused or a write failed, 2 usage.
set -u

# --- The framework-owned paths: the one list this script copies -------------
FRAMEWORK_DIRS=".claude/agents .claude/skills .claude/rules .claude/hooks .claude/scripts .claude/engines .claude/genres .claude/docs"
FRAMEWORK_FILES=".claude/statusline.sh"
# The MIT notice goes with the copy.
LICENSE_SRC="LICENSE"
LICENSE_DEST=".claude/LICENSE"
# Copied when the target has none, then the project's own (UPGRADING.md).
PROJECT_OWNED=".claude/docs/technical-preferences.md"
# Copied when the target has none, then kept; a changed one gets the
# framework's copy beside it, for a merge by hand.
AGENT_MODELS=".claude/agent-models.yaml"
AGENT_MODELS_SIDECAR=".claude/agent-models.ccgs.yaml"
AGENT_MODELS_REASON="the project's own; merge $AGENT_MODELS_SIDECAR into it by hand, then run bash .claude/scripts/agent-models.sh sync"
SETTINGS=".claude/settings.json"
SETTINGS_SIDECAR=".claude/settings.ccgs.json"
SETTINGS_REASON="the project's own; merge $SETTINGS_SIDECAR into it by hand"
GITIGNORE_COMMENT="# Claude Code Game Studios: session state and logs the hooks write, personal settings, worktrees"
GITIGNORE_LINES="production/session-state/
production/session-logs/
project.local.yaml
.claude/worktrees/"
GITATTRIBUTES_COMMENT="# Claude Code Game Studios: bash runs the hooks and helpers, so they stay LF on Windows"
GITATTRIBUTES_LINES=".claude/**/*.sh text eol=lf
.claude/**/*.awk text eol=lf
.claude/**/*.tsv text eol=lf"

usage() {
  echo "Usage: bash scripts/adopt.sh <target-dir> [--dry-run]"
  echo "Copies the Claude Code Game Studios framework into <target-dir>. See ADOPTING.md."
}

TARGET_ARG="" DRY=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    -h|--help) usage; exit 0 ;;
    -*) usage >&2; echo "Unknown option: $arg" >&2; exit 2 ;;
    *) if [ -n "$TARGET_ARG" ]; then usage >&2; echo "One target only." >&2; exit 2; fi
       TARGET_ARG="$arg" ;;
  esac
done
if [ -z "$TARGET_ARG" ]; then usage >&2; exit 2; fi

SRC=$(cd "$(dirname "$0")/.." && pwd -P) || exit 1
if [ ! -e "$TARGET_ARG" ]; then echo "Refused: $TARGET_ARG does not exist." >&2; exit 1; fi
if [ ! -d "$TARGET_ARG" ]; then echo "Refused: $TARGET_ARG is not a directory." >&2; exit 1; fi
# pwd -P resolves every link on the way, so a link to the framework is caught.
TGT=$(cd "$TARGET_ARG" && pwd -P) || exit 1

fold_case() {
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) printf '%s' "$1" | tr '[:upper:]' '[:lower:]' ;;
    *) printf '%s' "$1" ;;
  esac
}
SRC_KEY=$(fold_case "$SRC") TGT_KEY=$(fold_case "$TGT")
case "$TGT_KEY/" in
  "$SRC_KEY/"*) echo "Refused: $TARGET_ARG is the framework repository or inside it." >&2; exit 1 ;;
esac

NL='
'
refuse() {  # heading problems
  echo "Refused: $1" >&2
  printf '%s' "$2" | LC_ALL=C sort >&2
  echo "Nothing was written." >&2
  exit 1
}

# --- Every path the run may write, checked before anything is written -------
LIST=$(cd "$SRC" && for d in $FRAMEWORK_DIRS; do [ -d "$d" ] && find "$d" -type f; done | LC_ALL=C sort)
DESTS="$FRAMEWORK_FILES $LICENSE_DEST $AGENT_MODELS $AGENT_MODELS_SIDECAR $SETTINGS $SETTINGS_SIDECAR CLAUDE.md .gitignore .gitattributes"
DESTS=$(for rel in $DESTS; do echo "$rel"; done)"$NL$LIST"

PROBLEMS="" PARENTS="" LAST_DIR=""
while IFS= read -r rel; do
  [ -n "$rel" ] || continue
  if [ -L "$TGT/$rel" ]; then PROBLEMS="$PROBLEMS  $rel (a link)$NL"
  elif [ -d "$TGT/$rel" ]; then PROBLEMS="$PROBLEMS  $rel (a folder where a file goes)$NL"
  fi
  case "$rel" in */*) ;; *) continue ;; esac
  dir="${rel%/*}"
  # LIST is sorted, so files of one folder come together: list its parents once.
  [ "$dir" = "$LAST_DIR" ] && continue
  LAST_DIR="$dir"
  while :; do
    PARENTS="$PARENTS$dir$NL"
    case "$dir" in */*) dir="${dir%/*}" ;; *) break ;; esac
  done
done <<EOF
$DESTS
EOF
while IFS= read -r dir; do
  [ -n "$dir" ] || continue
  if [ -L "$TGT/$dir" ]; then PROBLEMS="$PROBLEMS  $dir (a link)$NL"
  elif [ -e "$TGT/$dir" ] && [ ! -d "$TGT/$dir" ]; then PROBLEMS="$PROBLEMS  $dir (a file where a folder goes)$NL"
  fi
done <<EOF
$(printf '%s' "$PARENTS" | LC_ALL=C sort -u)
EOF
[ -z "$PROBLEMS" ] || refuse "$TARGET_ARG has paths this script would write through or over:" "$PROBLEMS"

# --- The plan: every action line, and the writes they stand for -------------
ADDED=0 OVERWRITTEN=0 UNCHANGED=0 SKIPPED=0 APPENDED=0
LINES="" TAR_QUEUE="" CP_QUEUE="" CHANGES=""
plan() {  # ACTION path [reason]
  if [ -n "${3:-}" ]; then LINES="$LINES$1 $2 ($3)$NL"; else LINES="$LINES$1 $2$NL"; fi
  case "$1" in
    ADD) ADDED=$((ADDED + 1)) ;; OVERWRITE) OVERWRITTEN=$((OVERWRITTEN + 1)); CHANGES="$CHANGES$2$NL" ;;
    UNCHANGED) UNCHANGED=$((UNCHANGED + 1)) ;; SKIP) SKIPPED=$((SKIPPED + 1)) ;;
    APPEND) APPENDED=$((APPENDED + 1)); CHANGES="$CHANGES$2$NL" ;;
  esac
}
# One framework file to a target path: ADD, OVERWRITE or UNCHANGED.
plan_file() {  # src-rel dest-rel
  if [ ! -e "$TGT/$2" ]; then plan ADD "$2"; CP_QUEUE="$CP_QUEUE$1|$2$NL"
  elif cmp -s "$SRC/$1" "$TGT/$2"; then plan UNCHANGED "$2"
  else plan OVERWRITE "$2"; CP_QUEUE="$CP_QUEUE$1|$2$NL"
  fi
}
# A file that is the project's own once it exists; a changed one is kept and
# the framework's copy goes to the sidecar.
plan_kept() {  # rel sidecar reason
  if [ ! -e "$TGT/$1" ]; then plan ADD "$1"; CP_QUEUE="$CP_QUEUE$1|$1$NL"
  elif cmp -s "$SRC/$1" "$TGT/$1"; then plan UNCHANGED "$1"
  else plan SKIP "$1" "$3"; plan_file "$1" "$2"
  fi
}

for rel in $FRAMEWORK_FILES; do [ -f "$SRC/$rel" ] && plan_file "$rel" "$rel"; done
[ -f "$SRC/$LICENSE_SRC" ] && plan_file "$LICENSE_SRC" "$LICENSE_DEST"
[ -f "$SRC/$AGENT_MODELS" ] && plan_kept "$AGENT_MODELS" "$AGENT_MODELS_SIDECAR" "$AGENT_MODELS_REASON"

# Two cksum runs (CRC and size) find the framework files that differ, so the
# loop below runs builtins only: a process per file takes minutes on Git Bash.
EXIST=""
while IFS= read -r rel; do
  [ -n "$rel" ] && [ -e "$TGT/$rel" ] && EXIST="$EXIST$rel$NL"
done <<EOF
$LIST
EOF
DIFFER="$NL"
if [ -n "$EXIST" ]; then
  SRC_SUMS="$NL$(cd "$SRC" && printf '%s' "$EXIST" | tr '\n' '\0' | xargs -0 cksum)$NL"
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    case "$SRC_SUMS" in *"$NL$line$NL"*) ;; *) DIFFER="$DIFFER${line#* * }$NL" ;; esac
  done <<EOF
$(cd "$TGT" && printf '%s' "$EXIST" | tr '\n' '\0' | xargs -0 cksum)
EOF
fi
while IFS= read -r rel; do
  [ -n "$rel" ] || continue
  if [ ! -e "$TGT/$rel" ]; then plan ADD "$rel"; TAR_QUEUE="$TAR_QUEUE$rel$NL"; continue; fi
  case "$DIFFER" in
    *"$NL$rel$NL"*)
      if [ "$rel" = "$PROJECT_OWNED" ]; then plan SKIP "$rel" "the project's own once it exists"
      else plan OVERWRITE "$rel"; TAR_QUEUE="$TAR_QUEUE$rel$NL"
      fi ;;
    *) plan UNCHANGED "$rel" ;;
  esac
done <<EOF
$LIST
EOF

plan_kept "$SETTINGS" "$SETTINGS_SIDECAR" "$SETTINGS_REASON"

OWN_INSTRUCTIONS=""
for f in CLAUDE.md .claude/CLAUDE.md AGENTS.md; do
  if [ -e "$TGT/$f" ]; then OWN_INSTRUCTIONS="$f"; break; fi
done
if [ -z "$OWN_INSTRUCTIONS" ]; then plan ADD CLAUDE.md; CP_QUEUE="${CP_QUEUE}CLAUDE.md|CLAUDE.md$NL"
elif [ "$OWN_INSTRUCTIONS" = CLAUDE.md ] && cmp -s "$SRC/CLAUDE.md" "$TGT/CLAUDE.md"; then plan UNCHANGED CLAUDE.md
else plan SKIP CLAUDE.md "the project has $OWN_INSTRUCTIONS; merge the framework's instructions by hand, see ADOPTING.md"
fi

if [ -e "$TGT/project.yaml" ]; then plan SKIP project.yaml "the project's own"
else plan SKIP project.yaml "never written: run /start or /setup-engine, or write it by hand, see ADOPTING.md"
fi

# The lines a file lacks, one per line.
missing_lines() {  # rel lines
  local file="$TGT/$1" line
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    if [ ! -f "$file" ] || ! tr -d '\r' < "$file" | grep -qxF -- "$line"; then printf '%s\n' "$line"; fi
  done <<EOF
$2
EOF
}
plan_append() {  # rel missing
  if [ -z "$2" ]; then plan UNCHANGED "$1"
  elif [ ! -e "$TGT/$1" ]; then plan ADD "$1"
  else plan APPEND "$1" "$(printf '%s' "$2" | tr '\n' ' ' | sed 's/ $//')"
  fi
}
GITIGNORE_MISSING=$(missing_lines .gitignore "$GITIGNORE_LINES")
GITATTRIBUTES_MISSING=$(missing_lines .gitattributes "$GITATTRIBUTES_LINES")
plan_append .gitignore "$GITIGNORE_MISSING"
plan_append .gitattributes "$GITATTRIBUTES_MISSING"

# A read-only file the run would change refuses the whole run (a Perforce
# workspace keeps files read-only until they are checked out).
READ_ONLY=""
while IFS= read -r rel; do
  [ -n "$rel" ] && [ ! -w "$TGT/$rel" ] && READ_ONLY="$READ_ONLY  $rel$NL"
done <<EOF
$CHANGES
EOF
[ -z "$READ_ONLY" ] || refuse "these files in $TARGET_ARG are read-only and the run would change them; make them writable (in Perforce, check them out) and run again:" "$READ_ONLY"

# --- Report, then write ------------------------------------------------------
echo "Target: $TARGET_ARG"
[ "$DRY" -eq 1 ] && echo "Dry run: nothing is written."
printf '%s' "$LINES"

failed() { echo "Copy failed: $1 could not be written in $TARGET_ARG; the lines above may be only partly done." >&2; exit 1; }

# Append the missing lines once, in the file's own line endings.
append_lines() {  # rel comment missing
  local file="$TGT/$1" line eol=$'\n' text=""
  [ -n "$3" ] || return 0
  if [ -s "$file" ]; then
    if [ -n "$(tr -dc '\r' < "$file")" ]; then eol=$'\r\n'; fi
    [ -n "$(tail -c 1 "$file")" ] && text="$eol"
    text="$text$eol"
  fi
  text="$text$2$eol"
  while IFS= read -r line; do
    [ -n "$line" ] && text="$text$line$eol"
  done <<EOF
$3
EOF
  printf '%s' "$text" >> "$file" || failed "$1"
}

if [ "$DRY" -eq 0 ]; then
  if [ -n "$TAR_QUEUE" ]; then
    set -o pipefail
    printf '%s' "$TAR_QUEUE" | (cd "$SRC" && tar -cf - -T -) | (cd "$TGT" && tar -xf -) \
      || failed "the files under .claude/"
    set +o pipefail
  fi
  while IFS='|' read -r from to; do
    [ -n "$from" ] || continue
    { mkdir -p "$TGT/$(dirname "$to")" && cp -- "$SRC/$from" "$TGT/$to"; } || failed "$to"
  done <<EOF
$CP_QUEUE
EOF
  append_lines .gitignore "$GITIGNORE_COMMENT" "$GITIGNORE_MISSING"
  append_lines .gitattributes "$GITATTRIBUTES_COMMENT" "$GITATTRIBUTES_MISSING"
fi

echo "Summary: $ADDED added, $OVERWRITTEN overwritten, $UNCHANGED unchanged, $SKIPPED skipped, $APPENDED appended."
[ "$DRY" -eq 1 ] && echo "Dry run: nothing was written."
exit 0
