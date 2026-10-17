#!/usr/bin/env bash

# Check only processes launched from this installation, including Python wrappers.
daemon_is_running() {
    local executable="$1" resolved candidate process index
    local -a arguments=()
    resolved="$(readlink -f -- "$executable")" || return 1
    for process in /proc/[0-9]*; do
        [ -r "$process/cmdline" ] || continue
        arguments=()
        mapfile -d '' -t arguments < "$process/cmdline" 2>/dev/null || continue
        for ((index = 0; index + 1 < ${#arguments[@]}; index++)); do
            candidate="${arguments[index]}"
            [ "$candidate" = "$executable" ] || {
                [[ "$candidate" = /* ]] || continue
                [ "$(readlink -f -- "$candidate" 2>/dev/null)" = "$resolved" ] || continue
            }
            [ "${arguments[index + 1]}" = worker ] && return 0
        done
    done
    return 1
}
