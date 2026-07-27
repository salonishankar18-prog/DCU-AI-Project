#!/bin/bash
# Push the Datum project to github.com/salonishankar18-prog/DCU-AI-Project
#
#   bash ~/DCU-AI-Project/push.sh
#
# Needs the Xcode Command Line Tools (for git). If `git --version` errors, run
# `xcode-select --install`, finish the installer, then re-run this.
#
# .env is gitignored, so the API key is NOT pushed.

set -e
cd "$(dirname "$0")"

REPO="https://github.com/salonishankar18-prog/DCU-AI-Project.git"

if ! git --version >/dev/null 2>&1; then
  echo "git is not available yet — run 'xcode-select --install', finish the installer, then re-run this script."
  exit 1
fi

if [ ! -d .git ]; then
  git init
  git remote add origin "$REPO"
fi

# Make sure the branch exists and is named main
git symbolic-ref HEAD refs/heads/main 2>/dev/null || true

git add -A
git status --short

git commit -m "Datum — floor plan dimension extraction and TGD M access review

Part 1: reads real-world dimensions out of CubiCasa5k model.svg files and burns
them onto the matching PNGs. Run over 100 plans: 94 ok, 6 on the scale fallback,
0 failures.

Part 2: Python measures the geometry (door clear widths, corridor minimum
cross-sections, largest furniture-free circle per room); Claude judges it against
verbatim clause text retrieved from TGD M 2022. Three outcomes: pass, fail,
undetermined. No TGD M threshold is hard-coded anywhere.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"

git branch -M main
echo
echo "Pushing to $REPO"
echo "If prompted for a password, use a GitHub Personal Access Token, not your account password:"
echo "  https://github.com/settings/tokens  (scope: repo)"
echo
git push -u origin main
