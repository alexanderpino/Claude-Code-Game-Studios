#!/usr/bin/env bash
# adr-files.sh — where this project keeps its ADRs, and which files they are:
# the files directly in docs.adr_dir (default docs/architecture) whose name
# matches docs.adr_glob (default adr-*.md) without regard to case, as
# project.yaml sets them (effects-map.md, `## docs.adr_dir`).
#
# The one reader of that location. adr-status.sh, adr-dep-graph.sh,
# registry.sh, project-state.sh and artifact-check.sh call this script; the
# hooks and statusline.sh call the same functions in yaml-helper.sh
# (adr_location, adr_files); skills run it instead of globbing a path.
#
# EMITS OBSERVATIONS, NOT A VERDICT (CLAUDE.md, "Helpers in .claude/scripts/").
#
# Usage: bash .claude/scripts/adr-files.sh [--root DIR] [--dir DIR] [list|where]
#   list        (the default) the location rows, then one `file` row per ADR
#   where       the location rows only
#   --root DIR  the project; defaults to the repo this script is in
#   --dir DIR   list DIR, as it is given, instead of docs.adr_dir (the pattern
#               is still the project's)
#   -h, --help  this text
#
# Output: TSV.
#   dir   <folder>  <docs.adr_dir | default>
#   glob  <pattern> <docs.adr_glob | default>
#   match <glob>    the folder and the pattern as a glob that matches, case
#                   sensitively, what the pattern matches in any case: each
#                   letter outside a [...] class as a class of both cases
#                   (docs/architecture/[Aa][Dd][Rr]-*.[Mm][Dd]). A skill hands
#                   it to Grep's glob= or a bash command, which match case
#                   sensitively; it matches exactly the `file` rows
#   new   <path>    the name a new ADR takes: the folder, the pattern's text
#                   before its first *, NNNN-<slug>, and its text after its last
#                   * (adr-*.md: adr-NNNN-<slug>.md; ADR-*.md: ADR-NNNN-<slug>.md);
#                   `-` when the pattern has no *
#   file  <path>    an ADR, relative to the root, sorted
#   invalid <reason>  in place of every row above, for a value that cannot be
#                   used; it never falls back to the default
# ADR ids are read from the file name as adr-<number>, in any case, so the
# files are named that way (ADR-0003-layered-modules.md).
#
# Exit codes: 0 read; 1 the root cannot be read; 2 usage error; 3 a setting
# cannot be used (its `invalid` row is printed). Reads only; never writes.
#
# bash 3.2 and BWK awk safe, no Python.

set -u
LC_ALL=C
export LC_ALL

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT_ARG=""
DIR_ARG=""
CMD=list
while [ $# -gt 0 ]; do
  case "$1" in
    --root|--dir)
      [ $# -ge 2 ] || { echo "adr-files: $1 needs a value" >&2; exit 2; }
      if [ "$1" = --root ]; then ROOT_ARG="$2"; else DIR_ARG="$2"; fi
      shift 2 ;;
    --root=*) ROOT_ARG="${1#--root=}"; shift ;;
    --dir=*) DIR_ARG="${1#--dir=}"; shift ;;
    list|where) CMD="$1"; shift ;;
    -h|--help) sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "adr-files: unknown argument: $1 (try --help)" >&2; exit 2 ;;
  esac
done

HELPER="$HERE/../hooks/yaml-helper.sh"
[ -f "$HELPER" ] || { echo "adr-files: $HELPER is missing" >&2; exit 1; }
# shellcheck source=/dev/null
. "$HELPER"

if [ -n "$ROOT_ARG" ]; then
  cd "$ROOT_ARG" 2>/dev/null || { echo "adr-files: cannot read root $ROOT_ARG" >&2; exit 1; }
else
  cd "$HERE/../.." 2>/dev/null || { echo "adr-files: cannot reach the repo root" >&2; exit 1; }
fi

if ! adr_location; then
  printf 'invalid\t%s\n' "$_YH_ADR_WHY"
  exit 3
fi
DIR="${DIR_ARG:-$_YH_ADR_DIR}"
printf 'dir\t%s\t%s\n' "$DIR" "$( [ -n "$DIR_ARG" ] && echo --dir || echo "$_YH_ADR_DIR_SRC" )"
printf 'glob\t%s\t%s\n' "$_YH_ADR_GLOB" "$_YH_ADR_GLOB_SRC"
if [ "$DIR" = . ]; then MATCH="$_YH_ADR_MATCH"; else MATCH="$DIR/$_YH_ADR_MATCH"; fi
printf 'match\t%s\n' "$MATCH"
case "$_YH_ADR_GLOB" in
  *\**)
    NEW="${_YH_ADR_GLOB%%\**}NNNN-<slug>${_YH_ADR_GLOB##*\*}"
    [ "$DIR" = . ] || NEW="$DIR/$NEW"
    printf 'new\t%s\n' "$NEW" ;;
  *) printf 'new\t-\n' ;;
esac
[ "$CMD" = list ] || exit 0
adr_files "$DIR" | while IFS= read -r f; do
  [ -n "$f" ] && printf 'file\t%s\n' "$f"
done
exit 0
