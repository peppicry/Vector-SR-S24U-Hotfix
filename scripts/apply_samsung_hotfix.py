#!/usr/bin/env python3
from pathlib import Path

updates = {}


def prepare(path, needle, replacement):
    text = path.read_text(encoding='utf-8')
    if text.count(needle) != 1:
        raise SystemExit(f'{path}: expected exactly one patch anchor; no files changed')
    updates[path] = text.replace(needle, replacement, 1)


legacy = Path('legacy/src/main/java/org/matrix/vector/legacy/LegacyDelegateImpl.java')
needle = '''    @Override\n    public Object processLegacyHook(Executable executable, Object thisObject, Object[] args, Object[] legacyHooks, OriginalInvoker invokeOriginal) {\n        VectorLegacyCallback<Executable> callback = new VectorLegacyCallback<>(executable, thisObject, args);\n'''
replacement = '''    @Override\n    public Object processLegacyHook(Executable executable, Object thisObject, Object[] args, Object[] legacyHooks, OriginalInvoker invokeOriginal) {\n        // Samsung framework can probe the shared UID name "android.uid.system" through\n        // ApplicationPackageManager#getApplicationInfoAsUser(). The original framework\n        // intentionally lets NameNotFoundException propagate to its caller, which handles it.\n        // Running legacy callbacks around this probe can turn that expected exception into a\n        // hot log/exception loop in system_server after a KernelSU soft restart. Bypass only\n        // this exact pseudo-package lookup and preserve the platform's original semantics.\n        if ("getApplicationInfoAsUser".equals(executable.getName())\n                && args != null\n                && args.length > 0\n                && "android.uid.system".equals(args[0])) {\n            try {\n                return invokeOriginal.invoke();\n            } catch (Throwable t) {\n                sneakyThrow(t);\n                return null; // unreachable; required by javac after sneakyThrow\n            }\n        }\n\n        VectorLegacyCallback<Executable> callback = new VectorLegacyCallback<>(executable, thisObject, args);\n'''
prepare(legacy, needle, replacement)

bridge = Path('legacy/src/main/java/de/robv/android/xposed/XposedBridge.java')
needle = '''    public synchronized static void log(Throwable t) {\n        String logStr = Log.getStackTraceString(t);\n        Log.e(TAG, logStr);\n    }\n'''
replacement = '''    public synchronized static void log(Throwable t) {\n        // Safety net for the Samsung shared-UID probe described in LegacyDelegateImpl.\n        // Suppress only this exact, expected NameNotFoundException; all other legacy\n        // callback failures remain fully logged.\n        if (t != null\n                && "android.content.pm.PackageManager$NameNotFoundException".equals(t.getClass().getName())\n                && "android.uid.system".equals(t.getMessage())) {\n            return;\n        }\n        String logStr = Log.getStackTraceString(t);\n        Log.e(TAG, logStr);\n    }\n'''
prepare(bridge, needle, replacement)

# Validate every anchor before touching either source file; emit explicit UTF-8/LF.
for path, updated in updates.items():
    path.write_bytes(updated.encode('utf-8'))

print('Applied Samsung android.uid.system legacy-hook hotfix (null-safe logger)')
