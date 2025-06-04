# `buildben`: build-benedictions

<blockquote> <i> A <b> benediction </b>(Latin: bene, 'well' + dicere, 'to speak') is a short invocation for divine help, blessing and guidance, usually at the end of worship service. </i> <sup> <a href="https://en.wikipedia.org/wiki/Benediction"> Wikipedia </a></sup> </blockquote>

Build-benedictions (or short `buildben`) is a collection of scripts to automate developer tasks like:

- Setting up `zsh` & plugins
- Initialize file scaffolds for new projects, experiments, etc.
- Managing project-specific venv
- etc.

### Tools used:
- `pipx`: Keeps the OS-Python clean, and as a *redundancy* for:
  - When vscode is too dumb to find the .venv
  - For projects that don't have build-tools in their venv-requirements. 
- `just`: For running tasks & managing build tools.
- `direnv` (optional): Auto-loads project-specific env vars and auto-activates the venv when you cd into the repo.

<hr>

## 📦 Installation

### Prerequisites:
- Python installed on your OS (and you know its executable in your `$PATH`)
- A package manager (apt-get, brew, scoop, winget, etc. )

### Install with `pip`:
```bash
git clone https://github.com/markur4/buildben.git
pip install -e buildben   # Installs editable for direct modifications.
```

### Install with `pipx` (how it's meant to be used):

1. Install `pipx` according to their official [docs](https://pipx.pypa.io/stable/installation/):
```bash
sudo apt install just pipx        # For ubuntu
# brew install just pipx          # For MacOS
# py -m pip install --user pipx   # For Windows (Haven't tested that!)
pipx ensurepath                   # Add pipx to PATH, if not already done
pipx upgrade-all                  # !! Never run pipx with sudo !!
```

2. Clone & install `buildben`:
```bash
git clone https://github.com/markur4/buildben.git
pipx install -e buildben   # Editable for direct modifications.
```

3. Install `just`:
```bash
sudo apt install just       # Or whatever package manager you use
```


4. **Optional:** Install `direnv` & hook it into your shell: 
   - *Either* follow the instructions for [install](https://direnv.net/docs/installation.html) & [hook](https://direnv.net/docs/hook.html),
   - *Or* run `src/buildben/setup_zsh.sh` to install both `zsh` & other useful plugins, including `direnv`.
   - *Or* **skip** `direnv`! You can still manually execute all `just` commands!
<details><summary> <i><b>  For Ubuntu + zsh </b></i>  </summary>
<blockquote>

```bash
# === Install & hook direnv for Ubuntu + zsh =============
sudo apt install direnv
# Add direnv plugin (or just the hook) if missing
RCFILE="${ZDOTDIR:-$HOME}/.zshrc" # Respect ZDOTDIR if user set it
if ! grep -q 'direnv ' "$RCFILE"; then
    sed -i 's/^plugins=(/plugins=(direnv /' "$RCFILE"
fi
# Fallback: Ensure the hook line is present even without the plugin
if ! grep -q 'direnv hook zsh' "$RCFILE"; then
    echo 'eval "$(direnv hook zsh)"' >>"$RCFILE"
fi
```
</blockquote></details>

### Verify installation:
```bash
buildben-init-proj -- help
```

<hr>

## 🚀 Usage:
### Initialize project scaffold:
```bash
buildben-init-proj -n <my_project_name> -t ./ -u <my_github_username>
```





