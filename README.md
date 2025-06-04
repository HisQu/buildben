# build-benedictions

<blockquote> <i> A <b> benediction </b>(Latin: bene, 'well' + dicere, 'to speak') is a short invocation for divine help, blessing and guidance, usually at the end of worship service. </i> <sup> <a href="https://en.wikipedia.org/wiki/Benediction"> Wikipedia </a></sup> </blockquote>

A collection of scripts to automate developer tasks like:

- Setting up `zsh` & plugins
- Initialize file scaffolds for new projects, experiments, etc.
- Managing project-specific venv
- etc.

### System Dependencies:
- `pipx`: Keeps the OS-Python clean, and as a *redundancy* for:
  - When vscode is too dumb to find the .venv.
  - For projects that don't have build-tools in their venv-requirements. 
- `just`: For running tasks & managing build tools.
- `direnv` (optional): Auto-loads project-specific env vars and auto-activates the venv when you cd into the repo.



## Installation:
1. Install `pipx`:
```bash
sudo apt install just pipx  # For ubuntu
# brew install just pipx    # For MacOS
pipx ensurepath             # Add pipx to PATH, if not already done
pipx upgrade-all            # !! Never run pipx with sudo !!
```

2. Clone & install:
```bash
git clone https://github.com/markur4/.devtools.git
cd .devtools
pipx install .
```

1. Install `just`:
```bash
sudo apt install direnv       # For ubuntu
# brew install direnv         # For MacOS
```

1. Install `direnv` & hook it into your shell: 
   - *Either* follow the instructions for [install](https://direnv.net/docs/installation.html) & [hook](https://direnv.net/docs/hook.html),
   - *Or* run `./scripts/setup_zsh.sh` to install both `zsh` & other useful plugins, including `direnv`.
   - *Or
## Usage:



