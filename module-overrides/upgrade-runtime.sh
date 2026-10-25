#!/system/bin/sh
# Shared installer/service helpers. Never source files from a running process.

vector_upgrade_log() {
    if command -v ui_print >/dev/null 2>&1; then
        ui_print "- Vector upgrade: $*"
    elif command -v log >/dev/null 2>&1; then
        log -p i -t VectorUpgrade "$*"
    else
        printf '%s\n' "Vector upgrade: $*"
    fi
}

vector_process_name() {
    tr '\000' '\n' 2>/dev/null <"/proc/$1/cmdline" | head -n 1
}

vector_process_token() {
    local vr_stat
    vr_stat=$(cat "/proc/$1/stat" 2>/dev/null) || return 1
    # Fields after the final ') ' start at state (field 3); starttime is field 22.
    vr_stat=${vr_stat##*) }
    set -- $vr_stat
    [ "$#" -ge 20 ] || return 1
    shift 19
    printf '%s\n' "$1"
}

vector_owned_daemon() {
    local vr_pid="$1" vr_dir="$2" vr_fd vr_target
    case "$vr_pid" in ''|*[!0-9]*) return 1 ;; esac
    [ "$vr_pid" -gt 1 ] || return 1
    [ "$(vector_process_name "$vr_pid")" = 'lspd' ] || return 1
    for vr_fd in "/proc/$vr_pid/fd/"*; do
        vr_target=$(readlink "$vr_fd" 2>/dev/null) || continue
        case "$vr_target" in
            "$vr_dir/daemon.apk"|"$vr_dir/daemon.apk (deleted)") return 0 ;;
        esac
    done
    return 1
}

vector_current_daemon() {
    local vr_pid="$1" vr_dir="$2" vr_fd vr_target
    vector_owned_daemon "$vr_pid" "$vr_dir" || return 1
    [ "$(readlink "/proc/$vr_pid/cwd" 2>/dev/null)" = "$vr_dir" ] || return 1
    for vr_fd in "/proc/$vr_pid/fd/"*; do
        vr_target=$(readlink "$vr_fd" 2>/dev/null) || continue
        if [ "$vr_target" = "$vr_dir/daemon.apk" ] && [ "$vr_fd" -ef "$vr_dir/daemon.apk" ]; then
            return 0
        fi
    done
    return 1
}

vector_stop_process() {
    local vr_pid="$1" vr_name="$2" vr_token vr_round=0
    case "$vr_pid" in ''|*[!0-9]*) return 1 ;; esac
    [ "$vr_pid" -gt 1 ] || return 1
    vr_token=$(vector_process_token "$vr_pid") || return 0
    [ "$(vector_process_name "$vr_pid")" = "$vr_name" ] || return 0
    [ "$(vector_process_token "$vr_pid")" = "$vr_token" ] || return 0
    kill -TERM "$vr_pid" 2>/dev/null || :
    while [ "$vr_round" -lt 40 ]; do
        [ "$(vector_process_name "$vr_pid")" = "$vr_name" ] || return 0
        [ "$(vector_process_token "$vr_pid")" = "$vr_token" ] || return 0
        sleep 0.1
        vr_round=$((vr_round + 1))
    done
    vector_upgrade_log "Process $vr_pid ($vr_name) did not stop; refusing to force-kill or start a second daemon."
    return 1
}

vector_stop_runtime() {
    local vr_dir="$1" vr_mode="${2:-all}" vr_pid vr_targets=''
    case "$vr_mode" in all|stale) ;; *) return 1 ;; esac
    for vr_pid in $(pidof lspd 2>/dev/null); do
        vector_owned_daemon "$vr_pid" "$vr_dir" || continue
        if [ "$vr_mode" = 'stale' ] && vector_current_daemon "$vr_pid" "$vr_dir"; then
            continue
        fi
        vr_targets="$vr_targets $vr_pid"
    done
    [ -n "$vr_targets" ] || return 0

    # Stop only manager processes, never com.android.shell or Android core services.
    for vr_pid in $(pidof org.lsposed.manager 2>/dev/null); do
        vector_stop_process "$vr_pid" 'org.lsposed.manager' || return 1
    done
    for vr_pid in $vr_targets; do
        vector_owned_daemon "$vr_pid" "$vr_dir" || continue
        if [ "$vr_mode" = 'stale' ] && vector_current_daemon "$vr_pid" "$vr_dir"; then
            continue
        fi
        vector_upgrade_log "Stopping the previous Vector daemon ($vr_pid)."
        vector_stop_process "$vr_pid" 'lspd' || return 1
    done
}

vector_has_current_runtime() {
    local vr_pid
    for vr_pid in $(pidof lspd 2>/dev/null); do
        vector_current_daemon "$vr_pid" "$1" && return 0
    done
    return 1
}

# Called only after checking for an already recognized current daemon.
# Return 2 for an inconclusive start decision; never broaden stop criteria.
vector_start_preflight() {
    local vr_pid vr_dir="$1"
    if [ -r /data/local/tmp/daemon.apk ]; then
        vector_upgrade_log 'Start decision inconclusive: debug APK override present; no launch or stop requested.'
        return 2
    fi
    for vr_pid in $(pidof lspd 2>/dev/null); do
        if ! vector_owned_daemon "$vr_pid" "$vr_dir"; then
            vector_upgrade_log "Start decision inconclusive: lspd PID $vr_pid is not attributable; runtime left untouched."
            return 2
        fi
    done
    return 0
}

# Positive attribution only: no matching FD does not establish daemon failure.
# Do not assume the background launcher's PID is the eventual daemon's PID.
vector_observe_start() {
    local vr_dir="$1" vr_candidate vr_pid vr_token vr_ticks=0
    while [ "$vr_ticks" -lt 30 ]; do
        vr_pid=''
        for vr_candidate in $(pidof lspd 2>/dev/null); do
            vector_current_daemon "$vr_candidate" "$vr_dir" || continue
            vr_token=$(vector_process_token "$vr_candidate") || continue
            vr_pid="$vr_candidate"
            break
        done
        if [ -n "$vr_pid" ]; then
            sleep 1
            vr_ticks=$((vr_ticks + 2))
            if [ "$(vector_process_token "$vr_pid")" = "$vr_token" ] &&
                vector_current_daemon "$vr_pid" "$vr_dir"; then
                vector_upgrade_log "Current daemon $vr_pid observed in two samples; origin and Android IPC readiness are not established."
                return 0
            fi
        else
            sleep 0.5
            vr_ticks=$((vr_ticks + 1))
        fi
    done
    vector_upgrade_log 'Startup observation inconclusive; this does not establish daemon failure. No retry, stop or Android restart requested by this check.'
    return 2
}
