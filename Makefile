PYTHON ?= python3
BUNDLE ?= reference/Disco.app
SCENE_PYTHON ?= .venv/bin/python
XCODE_PROJECT := apps/ipad/DiscoPort.xcodeproj
SWIFT_OPTIONS := --scratch-path artifacts/build/swift --cache-path .cache/swift --config-path .cache/swift-config --security-path .cache/swift-security

.PHONY: inspect audit scenes test test-python test-input build-ipad build-simulator setup-scenes

inspect:
	$(PYTHON) tools/inspect_game.py --bundle "$(BUNDLE)"

audit:
	$(PYTHON) tools/audit_bundle.py "$(BUNDLE)" artifacts/inspection/bundle-audit.json

setup-scenes:
	$(PYTHON) -m venv .venv
	$(SCENE_PYTHON) -m pip install --cache-dir .cache/pip -r requirements-scenes.lock

scenes:
	$(SCENE_PYTHON) tools/inspect_scenes.py --bundle "$(BUNDLE)"

test: test-python test-input

test-python:
	PYTHONPATH=tools $(PYTHON) -m unittest discover -s tests -v

test-input:
	CLANG_MODULE_CACHE_PATH="$(CURDIR)/artifacts/cache/clang" SWIFTPM_MODULECACHE_OVERRIDE="$(CURDIR)/artifacts/cache/swift-manifest" swift test $(SWIFT_OPTIONS) -Xswiftc -module-cache-path -Xswiftc artifacts/cache/swift-modules

build-ipad:
	xcodebuild -project $(XCODE_PROJECT) -scheme DiscoPort -configuration Debug -destination 'generic/platform=iOS' -derivedDataPath artifacts/build/ipad CODE_SIGNING_ALLOWED=NO build

build-simulator:
	xcodebuild -project $(XCODE_PROJECT) -scheme DiscoPort -configuration Debug -destination 'generic/platform=iOS Simulator' -derivedDataPath artifacts/build/simulator CODE_SIGNING_ALLOWED=NO build
