PYTHON ?= python3
PLATFORM ?= ipad
BUNDLE ?= reference/Disco.app
SCENE_PYTHON ?= .venv/bin/python
XCODE_PROJECT := apps/ipad/DiscoPort.xcodeproj
SWIFT_OPTIONS := --scratch-path artifacts/build/swift --cache-path .cache/swift --config-path .cache/swift-config --security-path .cache/swift-security

.PHONY: inspect inspect-vtc inspect-texture-memory recover-vtc audit scenes recover-scene setup-unity setup-astc stage-unity export-unity-ios build-unity-ipad deploy-unity-ipad prepare-runtime-probe deploy-runtime-probe prepare-engine-probe configure-engine-assets enable-engine-bc retag-startup-bundles retag-addressable-bundles prepare-native-plugins build-engine-ipad deploy-engine-probe test test-python test-input build-ipad build-simulator deploy-ipad setup-scenes
.PHONY: setup-ghidra analyze-native-memory analyze-native-plugin prepare-amplify-plugin

inspect:
	$(PYTHON) tools/inspect_game.py --bundle "$(BUNDLE)"

inspect-vtc:
	$(PYTHON) tools/inspect_vtc.py --bundle "$(BUNDLE)"

recover-vtc:
	$(SCENE_PYTHON) tools/inspect_vtc.py --bundle "$(BUNDLE)" --sample-pages 4 --planes 0 2 3 4

audit:
	$(PYTHON) tools/audit_bundle.py "$(BUNDLE)" artifacts/inspection/bundle-audit.json

setup-scenes:
	$(PYTHON) -m venv .venv
	$(SCENE_PYTHON) -m pip install --cache-dir .cache/pip -r requirements-scenes.lock

scenes:
	$(SCENE_PYTHON) tools/inspect_scenes.py --bundle "$(BUNDLE)"

recover-scene:
	$(SCENE_PYTHON) tools/recover_scene.py --bundle "$(BUNDLE)"

stage-unity:
	$(PYTHON) tools/stage_unity.py

setup-unity:
	$(PYTHON) tools/setup_unity.py

export-unity-ios:
	$(PYTHON) tools/build_unity.py

build-unity-ipad:
	xcodebuild -project artifacts/build/unity-ios/Unity-iPhone.xcodeproj -scheme Unity-iPhone -configuration Debug -destination 'generic/platform=iOS' -derivedDataPath artifacts/build/unity-device CODE_SIGNING_ALLOWED=NO SDK_STAT_CACHE_ENABLE=NO build

deploy-unity-ipad:
	$(PYTHON) tools/deploy_ipad.py --unity

prepare-runtime-probe:
	$(PYTHON) tools/prepare_runtime_probe.py --bundle "$(BUNDLE)"

deploy-runtime-probe:
	$(PYTHON) tools/deploy_ipad.py --runtime

prepare-engine-probe:
	$(PYTHON) tools/prepare_engine_probe.py

retag-startup-bundles:
	$(SCENE_PYTHON) tools/retag_startup_bundles.py

retag-addressable-bundles:
	$(SCENE_PYTHON) tools/retag_startup_bundles.py --addressables

prepare-native-plugins:
	$(PYTHON) tools/prepare_native_plugins.py

prepare-amplify-plugin:
	$(PYTHON) tools/prepare_amplify_plugin.py

setup-ghidra:
	$(PYTHON) tools/setup_ghidra.py

analyze-native-memory:
	$(PYTHON) tools/analyze_native_memory.py

analyze-native-plugin:
	$(PYTHON) tools/analyze_native_plugin.py

build-engine-ipad:
	$(PYTHON) tools/build_engine.py

enable-engine-bc:
	$(PYTHON) tools/enable_engine_bc.py

configure-engine-assets:
	$(PYTHON) tools/configure_engine_assets.py

inspect-texture-memory:
	$(SCENE_PYTHON) tools/inspect_texture_memory.py --bundle "$(BUNDLE)" --bundles

setup-astc:
	$(PYTHON) tools/setup_astc.py

deploy-engine-probe:
	$(PYTHON) tools/deploy_ipad.py --engine

test: test-python test-input

test-python:
	PYTHONPATH=tools $(PYTHON) -m unittest discover -s tests -v

test-input:
	CLANG_MODULE_CACHE_PATH="$(CURDIR)/artifacts/cache/clang" SWIFTPM_MODULECACHE_OVERRIDE="$(CURDIR)/artifacts/cache/swift-manifest" swift test $(SWIFT_OPTIONS) -Xswiftc -module-cache-path -Xswiftc artifacts/cache/swift-modules

build-ipad:
	xcodebuild -project $(XCODE_PROJECT) -scheme DiscoPort -configuration Debug -destination 'generic/platform=iOS' -derivedDataPath artifacts/build/ipad CODE_SIGNING_ALLOWED=NO build

build-simulator:
	xcodebuild -project $(XCODE_PROJECT) -scheme DiscoPort -configuration Debug -destination 'generic/platform=iOS Simulator' -derivedDataPath artifacts/build/simulator CODE_SIGNING_ALLOWED=NO build

deploy-ipad:
	$(PYTHON) tools/deploy_ipad.py

.PHONY: doctor port audit-release stage-engine-host

doctor:
	$(PYTHON) tools/port.py doctor --platform $(PLATFORM)

port:
	$(PYTHON) tools/port.py build --platform $(PLATFORM)

stage-engine-host:
	$(PYTHON) tools/stage_engine_host.py

audit-release:
	$(PYTHON) tools/audit_release.py --history

.PHONY: build-android-probe build-android-cpu-probe inspect-android-runtime inspect-android-shaders deploy-android-probe deploy-android-cpu-probe

build-android-probe:
	$(PYTHON) tools/build_android.py

build-android-cpu-probe:
	$(PYTHON) tools/build_android.py --with-original-kernel

inspect-android-runtime:
	$(PYTHON) tools/inspect_android_runtime.py

inspect-android-shaders:
	$(SCENE_PYTHON) tools/inspect_android_shaders.py --limit 64

deploy-android-probe:
	$(PYTHON) tools/deploy_android.py

deploy-android-cpu-probe:
	$(PYTHON) tools/deploy_android.py --with-original-kernel

.PHONY: setup-unity-android
setup-unity-android:
	$(PYTHON) tools/setup_unity_android.py

.PHONY: build-android-runtime-probe deploy-android-runtime-probe inspect-android-initializers
build-android-runtime-probe:
	$(PYTHON) tools/build_android.py --with-mapped-runtime

deploy-android-runtime-probe:
	$(PYTHON) tools/deploy_android.py --with-mapped-runtime

inspect-android-initializers:
	$(PYTHON) tools/inspect_android_initializers.py

.PHONY: prepare-android-assets build-android-game deploy-android-game
prepare-android-assets:
	$(SCENE_PYTHON) tools/prepare_android_assets.py

build-android-game:
	$(PYTHON) tools/build_android_game.py --game-data --obb

deploy-android-game:
	$(PYTHON) tools/deploy_android_game.py --install-only
	$(PYTHON) tools/upload_android_assets.py
	$(PYTHON) tools/deploy_android_game.py --launch-only

.PHONY: setup-android-legacy
setup-android-legacy:
	$(PYTHON) tools/setup_android_legacy.py

.PHONY: setup-glslang audit-android-assets audit-android-shaders audit-android
setup-glslang:
	$(PYTHON) tools/setup_glslang.py

audit-android-assets:
	$(SCENE_PYTHON) tools/audit_android_assets.py

audit-android-shaders:
	$(SCENE_PYTHON) tools/audit_android_shaders.py

audit-android: audit-android-assets audit-android-shaders
