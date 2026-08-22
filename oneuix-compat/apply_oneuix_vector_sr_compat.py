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

        // Samsung uses two CSC gates for the native real-time network-speed feature on
        // recent One UI builds. SystemUI can keep the indicator alive while Settings
        // hides its on/off preference if only the Common gate is overridden.
        //
        // Hook every getBoolean overload because Settings/SystemUI may call different
        // SemCscFeature signatures across One UI revisions. This also avoids depending
        // on a single legacy method signature when running through Vector-SR's legacy bridge.
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
    }
'''

if old not in text:
    raise SystemExit("Network.kt supportRealTimeNetworkSpeed anchor not found; upstream changed")
NETWORK.write_text(text.replace(old, new, 1), encoding="utf-8")

build = BUILD.read_text(encoding="utf-8")
old_version = 'versionName = "1.7.0"'
new_version = 'versionName = "1.7.0-vectorsr-s24u-compat1"'
if old_version not in build:
    raise SystemExit("One UI X versionName anchor not found; upstream changed")
BUILD.write_text(build.replace(old_version, new_version, 1), encoding="utf-8")

print("Applied One UI X Vector-SR/S24U network-speed compatibility patch")
