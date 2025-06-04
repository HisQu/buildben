# `buildben`: build-benedictions

<blockquote> <i> A <b> benediction </b>(Latin: bene, 'well' + dicere, 'to speak') is a short invocation for divine help, blessing and guidance, usually at the end of worship service. </i> <sup> <a href="https://en.wikipedia.org/wiki/Benediction"> Wikipedia </a></sup> </blockquote>

Build-benedictions (or short `buildben`) is a collection of scripts to automate developer tasks like:

- Setting up `zsh` & plugins
- Initialize file scaffolds for new projects, experiments, etc.
- Managing project-specific venv
- etc.

### Tools used:
- `pipx`: The recommended home for `buildben` to keep the OS-Python clean, but have a system-wide venv with dev-tools for all your projects. But `buildben` should also work with any `pip`.
  - Installed along with `buildben`:
  - `pip-tools`:  Used to re-compute the venv requirements.
- `just`: For running tasks & managing build tools.
- `direnv` (optional): Auto-loads project-specific env vars and auto-activates the venv when you cd into the repo.

<hr>

<!-- == Installation ============================================== -->
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
cd buildben         # Needed
pipx install -e .   # Editable for direct modifications.
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
buildben-init-proj --help
```

<hr>


<!-- == Usage ====================================================== -->
## 🚀 Usage:

### Initialize project scaffold & create venv
```bash
# Initialize project scaffold:
buildben-init-proj -n <my_project_name> -t ./ -u <my_github_username>
cd <my_project_name> # Change directory to project root
```
You will be prompted by direnv to allow the venv to activate. Say yes.

### Include .direnv in vscode:
- Copy the path to the path to the python executable (sth like: `<my_project_name>/.direnv/python-3.12.3`). 
- Open the vscode commands palette (Ctrl+Shift+P), search for "Python: Select Interpreter".
- Click "Search on workspace level", then "Enter interpreter path"
- Paste the path.








