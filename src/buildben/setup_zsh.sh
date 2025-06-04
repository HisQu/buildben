#!/usr/bin/env bash
set -euo pipefail # < safer bash

# === Update APT & install zsh ========================================
sudo apt update
sudo apt install -y zsh git curl direnv

### Install Oh-My-Zsh (non-interactive)
export RUNZSH=no # < do not start zsh automatically
export CHSH=no   # < don’t try to chsh inside a script
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" --unanattended

# === Install Plugins =================================================
### Define where custom stuff lives
# > $ZSH is set by the installer (default: ~/.oh-my-zsh)
ZSH_CUSTOM="${ZSH_CUSTOM:-${ZSH:-$HOME/.oh-my-zsh}/custom}"

### Install powerlevel10k theme
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git \
    "$ZSH_CUSTOM/themes/powerlevel10k"

### Install zsh-syntax-highlighting plugin
git clone --depth=1 https://github.com/zsh-users/zsh-syntax-highlighting.git \
    "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting"

# === Enable the theme & plugins in ~/.zshrc ==========================
ZDOT="${ZDOTDIR:-$HOME}" # < respect ZDOTDIR if user set it
RCFILE="$ZDOT/.zshrc"

### Add the theme if not present
grep -q '^ZSH_THEME="powerlevel10k/powerlevel10k"' "$RCFILE" ||
    sed -i 's/^ZSH_THEME=.*/ZSH_THEME="powerlevel10k\/powerlevel10k"/' "$RCFILE"

### Add plugin to plugins=(...) list (idempotent)
if ! grep -q 'zsh-syntax-highlighting' "$RCFILE"; then
    sed -i 's/^plugins=(/plugins=(zsh-syntax-highlighting /' "$RCFILE"
fi

### Add direnv plugin (or just the hook) if missing
if ! grep -q 'direnv ' "$RCFILE"; then
    sed -i 's/^plugins=(/plugins=(direnv /' "$RCFILE"
fi
# > Fallback: ensure the hook line is present even without the plugin
if ! grep -q 'direnv hook zsh' "$RCFILE"; then
    echo 'eval "$(direnv hook zsh)"' >>"$RCFILE"
fi

# === Finished ========================================================
echo "Add MesloLGS NF font to your terminal for full Powerlevel10k glyphs."
echo "Start a new Zsh session or run:  exec zsh -l"

# https://github.com/romkatv/powerlevel10k?tab=readme-ov-file#oh-my-zsh
# => If not using iTerm2:
# => Install Fonts MesloLGS NF:
# => Either get them from this repo or download here:
# https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Regular.ttf
# https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Bold.ttf
# https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Italic.ttf
# https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Bold%20Italic.ttf
# => Change the font of your terminal to MesloLGS NF
