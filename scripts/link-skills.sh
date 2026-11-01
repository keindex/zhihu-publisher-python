#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

case "${OSTYPE:-}" in
    msys*|cygwin*)
        exec powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$repo_root/scripts/link-skills.ps1")" "$@"
        ;;
esac

if (( $# )); then
    printf '%s\n' 'This script takes no arguments on macOS or Linux.' >&2
    exit 2
fi

declare -a sources=() destinations=()
declare -a roots=("${CODEX_HOME:-$HOME/.codex}/skills" "$HOME/.agents/skills")

for bucket in engineering productivity in-progress; do
    for source in "$repo_root/skills/$bucket"/*; do
        [[ -f "$source/SKILL.md" ]] || continue
        name="$(basename -- "$source")"
        for root in "${roots[@]}"; do
            destination="$root/$name"
            if [[ -L "$destination" ]] && [[ "$(readlink -- "$destination")" == "$source" ]]; then
                printf 'Already linked: %s\n' "$destination"
            elif [[ -e "$destination" || -L "$destination" ]]; then
                printf 'Refusing to overwrite existing skill: %s\n' "$destination" >&2
                exit 1
            else
                sources+=("$source")
                destinations+=("$destination")
            fi
        done
    done
done

for (( index=0; index<${#sources[@]}; index++ )); do
    mkdir -p -- "$(dirname -- "${destinations[index]}")"
    ln -s -- "${sources[index]}" "${destinations[index]}"
    printf 'Linked: %s -> %s\n' "${destinations[index]}" "${sources[index]}"
done
