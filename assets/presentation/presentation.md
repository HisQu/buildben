---
marp: true
theme: markurstheme
paginate: true
header: "Build-Benedictions: init_proj"
footer: "Dr. Martin Kuric • 2025 • Germania Sacra, HisQu • ADW Göttingen"

---

# Build-Benedictions
# ``buildben init_proj`` 

## Managing Multiple (Python) Projects & Dependencies

By Dr. Martin Kuric

<!-- _paginate: skip -->



---
<header> <h1>From <a href="https://en.wikipedia.org/wiki/Benediction">Wikipedia</a>:</h1> </header>
  
![bg left 50%](./Benedictions_image.png) 


*"A **benediction** (Latin: bene, 'well' + dicere, 'to speak') is a short **invocation** for divine help, blessing and guidance [...]."*

*"**Invocation** is the act of calling upon a deity, spirit, or supernatural force, typically through prayer, ritual, or **spoken formula**, to seek guidance, assistance, or presence."*


---
<header> <h1>Build-Benedictions: Main Features</h1> </header>



- Standardize setups with **template scaffolds**:
  - ``buildben init_proj``: Create a new **project**. 
  - ``buildben add_experiment``: Add a new **experiment** to a project.
  - ``buildben init_database``: Create a new central **database**. *(WIP)*
- Integrate **popular tools**:
  - ``direnv``: Virtual environment & variables.
  - ``pip-tools``: Dependency management.
  - ``just``: For summarizing tasks (upgrade, test, etc.).
  - ``Docker``: Snapshot current state of project.

---

<header> <h1>Common Practice: ``requirements.txt`` & ``.venv``</h1> </header>

---

# Common Practice: Installing from GitHub

```bash
git clone <repo-url>             # Download
python -m venv .venv             # Protect system packages
source .venv/bin/activate        # Activate virtual environment
pip install -r requirements.txt  # Install dependencies
```

### Why this is not enough:
- ``requirements.txt`` only holds dependencies, not the **project structure**.
  - Python can't **import** local packages.
  - VS Code (sometimes) struggles with **refactoring** & **typing** across packages.
- ``requirements.txt`` not up-to-date?
- ``.venv`` not activated?


---

