PYTHON ?= python3
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
