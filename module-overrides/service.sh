#!/system/bin/sh

MODDIR="${0%/*}"
cd "$MODDIR" || exit 1
MODDIR=$(pwd -P) || exit 1
. "$MODDIR/upgrade-runtime.sh" || exit 1

# KernelSU soft restart can leave the old daemon alive. Replace stale instances,
# but preserve a healthy current daemon and its existing reinjection state.
vector_stop_runtime "$MODDIR" stale || exit 1
if vector_has_current_runtime "$MODDIR"; then
    vector_upgrade_log 'The installed daemon is already running; keeping it for reinjection.'
    exit 0
fi

# Explicit BusyBox avoids Android Toybox unshare, which lacks --propagation.
vr_busybox=''
for vr_candidate in /data/adb/ksu/bin/busybox /data/adb/magisk/busybox /data/adb/ap/bin/busybox; do
    if [ -x "$vr_candidate" ]; then
        vr_busybox="$vr_candidate"
        break
    fi
done
if [ -n "$vr_busybox" ]; then
    "$vr_busybox" unshare --propagation slave -m "$MODDIR/daemon" --system-server-max-retry=3 "$@" </dev/null &
else
    # Supports root managers that already put a compatible BusyBox in PATH.
    case "$(unshare --help 2>&1)" in
        *--propagation*) unshare --propagation slave -m "$MODDIR/daemon" --system-server-max-retry=3 "$@" </dev/null & ;;
        *) vector_upgrade_log 'No compatible unshare found; daemon was not started.'; exit 1 ;;
    esac
fi
