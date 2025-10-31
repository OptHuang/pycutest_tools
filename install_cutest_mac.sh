#!/usr/bin/env bash
# install_cutest_mac.sh
# Install CUTEst on macOS using Homebrew (plain text version)

set -e
set -o pipefail

echo "=========================================================="
echo "Installing CUTEst on macOS"
echo "=========================================================="

# Step 1. Ensure Command Line Tools
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

# Step 2. Install or update Homebrew
echo
echo "[2/4] Installing or updating Homebrew..."
if ! command -v brew &>/dev/null; then
  NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
  brew update
fi

# Step 3. Install CUTEst and dependencies
echo
echo "[3/4] Installing CUTEst and dependencies..."
brew tap optimizers/cutest
brew install cutest
brew install mastsif || echo "Warning: unable to install mastsif (optional)."

# Step 4. Update shell configuration (~/.bashrc)
echo
echo "[4/4] Configuring CUTEst environment..."
for f in archdefs mastsif sifdecode cutest; do
  prefix="$(brew --prefix "$f" 2>/dev/null || true)"
  if [ -n "$prefix" ] && [ -f "$prefix/$f.bashrc" ]; then
    line=". \"$prefix/$f.bashrc\""
    if ! grep -Fq "$line" ~/.bashrc 2>/dev/null; then
      echo "$line" >> ~/.bashrc
      echo "Added $f configuration to ~/.bashrc"
    fi
  fi
done

echo
echo "=========================================================="
echo "CUTEst installation complete."
echo "Next steps:"
echo "1. Run: source ~/.bashrc"
echo "2. Verify with: cutest -v"
echo
echo "If you are using Anaconda, ensure '~/.bashrc' is sourced inside your environment."
echo "=========================================================="