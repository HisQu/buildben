

pipx ensurepath             # Add pipx to PATH, if not already done
pipx install pip-tools      # Install build tools away from OS-Python
pipx upgrade-all            # !! Never run pipx with sudo !!

pipx install --suffix=devtools path/to/.devtools/scripts