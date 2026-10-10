PYTHON ?= python3
PLATFORM ?= ipad

.PHONY: help setup doctor port install test inspect audit-release build-ipad build-android audit-android
help:
	@echo 'Disco on the Go — build from your own reference/Disco.app'
	@echo 'make setup                 Install pinned tools/dependencies (downloads)'
	@echo 'make doctor                Check game input and tools'
	@echo 'make port                  Build iPad (unsigned)'
	@echo 'make install               Sign, install assets and launch on iPad'
	@echo 'Add PLATFORM=android to setup, doctor, port or install for Android.'
	@echo 'make test / make audit-release   Source-only checks'

setup:
	$(PYTHON) tools/setup.py --platform $(PLATFORM)
doctor:
	$(PYTHON) tools/port.py doctor --platform $(PLATFORM)
port:
	$(PYTHON) tools/port.py build --platform $(PLATFORM)
install:
	$(PYTHON) tools/install.py --platform $(PLATFORM)
test:
	PYTHONPATH=tools $(PYTHON) -m unittest discover -s tests -v
inspect:
	$(PYTHON) tools/inspect_game.py --bundle reference/Disco.app
audit-release:
	$(PYTHON) tools/audit_release.py --history
# Rebuild already staged products; use make port for a complete rebuild.
build-ipad:
	$(PYTHON) tools/configure_ipad.py --increased-memory --no-debug-memory --amplify-cpu --lazy-scenes --landscape
	.venv/bin/python tools/prepare_branding.py --ipad-project artifacts/build/native-engine-ios
	$(PYTHON) tools/build_ipad_game.py
build-android:
	.venv/bin/python tools/prepare_branding.py
	$(PYTHON) tools/build_android_game.py --game-data --obb
audit-android:
	.venv/bin/python tools/audit_android_assets.py
	.venv/bin/python tools/audit_android_shaders.py
