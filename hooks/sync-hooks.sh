#!/bin/sh
set -eu
root=$(git rev-parse --show-toplevel)
git config extensions.worktreeConfig true
git config --worktree core.hooksPath "$root/hooks"
chmod +x "$root/hooks/pre-commit" "$root/hooks/pre-push" "$root/hooks/sync-hooks.sh"
