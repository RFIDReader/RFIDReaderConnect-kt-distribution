.PHONY: verify test lint secret-scan security-scan pre-commit pre-push hooks-install
verify:
	python3 tool/verify_artifact.py
test: verify
lint:
	git diff --check
secret-scan:
	python3 hooks/check-secrets.py
security-scan: verify lint secret-scan
pre-commit: lint secret-scan
pre-push: security-scan
hooks-install:
	bash hooks/sync-hooks.sh
