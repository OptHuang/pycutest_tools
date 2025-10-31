#!/usr/bin/env bash
# install_cutest_mac.sh
set -euo pipefail

echo "=========================================================="
echo "Installing CUTEst on macOS"
echo "=========================================================="

# 1) Xcode CLT
echo
echo "[1/4] Checking for Xcode Command Line Tools..."
if ! xcode-select -p &>/dev/null; then
  echo "Installing Command Line Tools..."
  xcode-select --install || true
  until xcode-select -p &>/dev/null; do
    echo "Waiting for Command Line Tools installation to complete..."
    sleep 30
  done
else
  echo "Command Line Tools already installed."
fi

# 2) Homebrew
echo
echo "[2/4] Installing or updating Homebrew..."
if ! command -v brew &>/dev/null; then
  NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
  brew update
fi

# 3) Install CUTEst and dependencies
echo
echo "[3/4] Installing CUTEst and dependencies..."
brew tap optimizers/cutest
brew install sifdecode mastsif cutest

# 4) Write bashrc
echo
echo "[4/4] Configuring CUTEst environment..."
for f in mastsif sifdecode cutest; do
  prefix="$(brew --prefix "$f" 2>/dev/null || true)"
  rc="$prefix/$f.bashrc"
  if [ -n "$prefix" ] && [ -f "$rc" ]; then
    line=". \"$rc\""
    if ! grep -Fq "$line" ~/.bashrc 2>/dev/null; then
      echo "$line" >> ~/.bashrc
      echo "Added $f configuration to ~/.bashrc"
    fi
  fi
done

# Source bashrc from bash_profile
if ! grep -Fq 'source ~/.bashrc' ~/.bash_profile 2>/dev/null; then
  echo 'source ~/.bashrc' >> ~/.bash_profile
fi

if [ -n "${GITHUB_ENV:-}" ]; then
  # Persist CUTEST env to GITHUB_ENV for subsequent steps
  for f in mastsif sifdecode cutest; do
    rc="$(brew --prefix "$f")/$f.bashrc"
    if [ -f "$rc" ]; then
      # shellcheck disable=SC1090
      source "$rc"
    fi
  done

  # Auto-detect MYARCH if not set
  if [ -z "${MYARCH:-}" ] && [ -n "${CUTEST:-}" ] && [ -d "$CUTEST/lib" ]; then
    first_arch="$(find "$CUTEST/lib" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | head -n1 || true)"
    if [ -n "$first_arch" ]; then
      export MYARCH="$first_arch"
    fi
  fi

  {
    [ -n "${CUTEST:-}" ] && echo "CUTEST=$CUTEST"
    [ -n "${SIFDECODE:-}" ] && echo "SIFDECODE=$SIFDECODE"
    [ -n "${MASTSIF:-}" ] && echo "MASTSIF=$MASTSIF"
    [ -n "${MYARCH:-}" ] && echo "MYARCH=$MYARCH"
  } >> "$GITHUB_ENV"

  echo "Persisted CUTEST env to GITHUB_ENV:"
  echo "  CUTEST=${CUTEST:-}"
  echo "  SIFDECODE=${SIFDECODE:-}"
  echo "  MASTSIF=${MASTSIF:-}"
  echo "  MYARCH=${MYARCH:-}"
fi

echo
echo "=========================================================="
echo "CUTEst installation complete."
echo "Next steps:"
echo "1. Run: source ~/.bashrc (for interactive shells)"
echo "2. Verify with: cutest -v"
echo "=========================================================="