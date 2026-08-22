#!/usr/bin/env python3
from pathlib import Path

NETWORK = Path("app/src/main/java/io/github/soclear/oneuix/hook/Network.kt")
BUILD = Path("app/build.gradle.kts")

text = NETWORK.read_text(encoding="utf-8")
old = '''    fun supportRealTimeNetworkSpeed(loadPackageParam: LoadPackageParam) {
        if (loadPackageParam.packageName != Package.SETTINGS &&
            loadPackageParam.packageName != Package.SYSTEMUI
        ) {
            return
        }
        try {
            findAndHookMethod(
                "com.samsung.android.feature.SemCscFeature",
                loadPackageParam.classLoader,
                "getBoolean",
                String::class.java,
                Boolean::class.java,
                object : XC_MethodHook() {
                    override fun beforeHookedMethod(param: MethodHookParam) {
                        if (param.args[0] == "CscFeature_Common_SupportZProjectFunctionInGlobal") {
                            param.result = true
                        }
                    }
                }
            )
        } catch (t: Throwable) {
            XposedBridge.log(t)
        }
    }
'''
new = '''    fun supportRealTimeNetworkSpeed(loadPackageParam: LoadPackageParam) {
        if (loadPackageParam.packageName != Package.SETTINGS &&
            loadPackageParam.packageName != Package.SYSTEMUI
        ) {
            return
        }

        // Recent Samsung builds can cache network-speed support in Settings during
        // StatusBarNetworkSpeedController class initialization. Keep the CSC hooks for
        // SystemUI/Settings, but also force the controller availability directly in
        // Settings so a cached false value cannot hide the preference.
        val networkSpeedFeatureKeys = setOf(
            "CscFeature_Common_SupportZProjectFunctionInGlobal",
            "CscFeature_Setting_SupportRealTimeNetworkSpeed",
        )

        try {
            val semCscFeatureClass = findClass(
                "com.samsung.android.feature.SemCscFeature",
                loadPackageParam.classLoader,
            )
            XposedBridge.hookAllMethods(
                semCscFeatureClass,
                "getBoolean",
                object : XC_MethodHook() {
                    override fun beforeHookedMethod(param: MethodHookParam) {
                        val featureName = param.args.firstOrNull() as? String ?: return
                        if (featureName in networkSpeedFeatureKeys) {
                            param.result = true
                        }
                    }
                }
            )
            XposedBridge.log(
                "[OneUIX-VectorSR] network-speed CSC hooks active in ${loadPackageParam.packageName}"
            )
        } catch (t: Throwable) {
            XposedBridge.log(t)
        }

        if (loadPackageParam.packageName == Package.SETTINGS) {
            try {
                findAndHookMethod(
                    "com.samsung.android.settings.notification.StatusBarNetworkSpeedController",
                    loadPackageParam.classLoader,
                    "getAvailabilityStatus",
                    object : XC_MethodHook() {
                        override fun beforeHookedMethod(param: MethodHookParam) {
                            // BasePreferenceController: 0 = AVAILABLE, 3 = UNSUPPORTED_ON_DEVICE.
                            param.result = 0
                        }
                    }
                )
                XposedBridge.log(
                    "[OneUIX-VectorSR] StatusBarNetworkSpeedController availability forced to AVAILABLE"
                )
            } catch (t: Throwable) {
                XposedBridge.log(t)
            }
        }
    }
'''

if old not in text:
    raise SystemExit("Network.kt supportRealTimeNetworkSpeed anchor not found; upstream changed")
NETWORK.write_text(text.replace(old, new, 1), encoding="utf-8")

build = BUILD.read_text(encoding="utf-8")
old_version = 'versionName = "1.7.0"'
new_version = 'versionName = "1.7.0-vectorsr-s24u-compat2"'
if old_version not in build:
    raise SystemExit("One UI X versionName anchor not found; upstream changed")
BUILD.write_text(build.replace(old_version, new_version, 1), encoding="utf-8")

print("Applied One UI X Vector-SR/S24U network-speed compatibility patch v2")
