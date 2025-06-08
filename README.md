<!-- ============================================================== -->
<!-- == Header ==================================================== -->
<div align="center">

<!-- --- Title ---------------------------------------------------- -->

# `buildben`: build-benedictions

*Part of:*
<!-- --- Logo ----------------------------------------------------- -->
<a href="https://hisqu.de" target="_blank">
  <img src="https://avatars.githubusercontent.com/u/196629600?s=200&v=4" 
       width="100px" alt="logo" style="margin-top: -10px;">
</a>

<br>

<!-- --- Badges --------------------------------------------------- -->

[![Code style:
black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

</div>

<!-- ============================================================== -->
<!-- == Abstract ================================================== -->
<div style="width: 85%; margin: 2rem auto; text-align: justify;">
<hr>

<blockquote> <i> A <b> benediction </b>(Latin: bene, 'well' + dicere, 'to speak') is a short invocation for divine help, blessing and guidance, usually at the end of worship service. </i> <sup> <a href="https://en.wikipedia.org/wiki/Benediction"> Wikipedia </a></sup> </blockquote>
<br>

`buildben` is a collection of scripts to integrate common developer tools
(e.g. `just`) and automate tasks.

<hr>
</div>

#### Features:
<!-- Summarize the top 3 features -->
- Automate development workflows
- Standardized project setup
- Dependency management tools



#### Main dependencies:
<!-- List your main dependencies here and explain why they're important. -->
- **`pipx`**: The recommended home for `buildben` to keep the OS-Python clean
- **`pip-tools`**: Used to re-compute the venv requirements and sync them.
- **`direnv`**: Auto-loads project-specific env vars and provides useful one-liners for environment management.
- **`just`**: For running tasks & managing build tools.
  
<br>

<div align="center">
  <img src="https://raw.githubusercontent.com/HisQu/buildben/main/assets/diagram/diagram.svg" 
       width="800px" alt="Management of Virtual Environments & Dependencies" >
</div>

<!-- ============================================================== -->
<!-- == Installation ============================================== -->
## 📦 Installation

### Prerequisites:
- Python installed on your OS (and you know its executable in your `$PATH`)
- A Package manager (`apt`, `brew`, `winget`, etc.)

### Install with `pip`:
`buildben` still requires `direnv` and `just` to work, but any pip
install will do:
```bash
git clone https://github.com/markur4/buildben.git
pip install -e buildben   # Installs editable for direct modifications.
```

### Install with `pipx` (how it's meant to be used):

1. Install `pipx` according to their official [docs](https://pipx.pypa.io/stable/installation/):
```bash
sudo apt install pipx        # For Ubuntu
# brew install pipx          # For MacOS
# py -m pip install --user pipx   # For Windows (Not tested!)
pipx ensurepath                   # Add pipx to PATH, if not already done
pipx upgrade-all                  # !! Never run pipx with sudo !!
```

2. Clone & install `buildben`:
```bash
git clone https://github.com/markur4/buildben.git
cd buildben         # Needed
pipx install -e .   # Editable for direct modifications.
```

3. Install [`just`](https://github.com/casey/just):
```bash
sudo apt install just     # For Ubuntu
# brew install just       # For MacOS
# pipx install rust-just  # Windows requires the cross-platform version (not tested!)
```


4. Install `direnv` & hook it into your shell: 
   - *Either* follow the instructions for [install](https://direnv.net/docs/installation.html) & [hook](https://direnv.net/docs/hook.html),
   - *Or* run `src/buildben/setup_zsh.sh` to install both `zsh` & other useful plugins, including `direnv`.

```bash
# === Example for Ubuntu + zsh =============
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

1. For drawing PlantUML-diagrams, we need Java (e.g.`temurin`) & `graphviz`:
```bash
sudo apt-get install temurin-21-jdk graphviz     # For Ubuntu
# brew install temurin graphviz                  # For MacOS
# winget install EclipseAdoptium.Temurin.21.JDK  # Windows 
winget install -e --id Graphviz.Graphviz
```

### Verify installation:
```bash
buildben-init-proj --help
```

### (Optional) Set up vscode:
1. Copy the path to the path to the python executable (sth like: `<my_project_name>/.direnv/python-3.12.3`). 
2. Open the vscode commands palette (Ctrl+Shift+P), search & select "Python: Select Interpreter".
3. Select "Search on workspace level".
4. "Enter interpreter path" & paste the path.
5. Optional, install extension [direnv](https://marketplace.visualstudio.com/items?itemName=mkhl.direnv)
5. Optional, install extension [vscode-just](https://marketplace.visualstudio.com/items?itemName=nefrob.vscode-just-syntax)

<br>

<!-- ============================================================== -->
<!-- == Usage ====================================================== -->
## 🚀 Usage:

### Initialize project scaffold & create venv
```bash
# Initialize project scaffold:
buildben-init-proj -n <my_project_name> -t ./ -u <my_github_username>
cd <my_project_name> # Change directory to project root
```
You will be prompted by direnv to allow the venv to activate. Say **yes**.








