---
marp: true
theme: markurs-theme
paginate: true
header: "2025 · Build-Benedictions: Managing Multiple (Python) Projects & Dependencies"
footer: "Dr. Martin Kuric — ADW Göttingen · Germania Sacra / HisQu"


---
<center>

# Build-Benedictions 

# ``$ buildben init_proj`` 

## Managing Multiple (Python) Projects & Dependencies


<div class="speaker">
  <p class="author">Dr.&#8239rer.&#8239nat. Martin Kuric</p>
  <p class="affiliation">Academy of Sciences Göttingen · Germania Sacra / HisQu</p>
</div>

<!-- _paginate: skip -->
<!-- _footer: "" -->
<!-- _header: "" -->

</center>


---
<!-- ------------------------------------------------------------- -->
## From [Wikipedia]("https://en.wikipedia.org/wiki/Benediction"):
<!-- ------------------------------------------------------------- -->

![bg left 50%](./Benedictions_image.png) 

*"A **benediction** (Latin: bene, 'well' + dicere, 'to speak') is a short **invocation** for divine help, blessing and guidance [...]."*

*"**Invocation** is the act of calling upon a deity, spirit, or supernatural force, typically through prayer, ritual, or **spoken formula**, to seek guidance, assistance, or presence."*

<br>

<!-- _header: "" -->

---
<!-- ------------------------------------------------------------- -->
## Build-Benedictions: Main Features
<!-- ------------------------------------------------------------- -->

#### Standardize setups with **template** scaffolds:
- ``buildben init_proj``: Create a new **project** in ``/src``-layout.
- ``buildben add_experiment``: Add a new **experiment** to a project.
- ``buildben init_database``: Create a new central **database**. *(WIP)*

#### Integrate popular **CLI-tools**:
- ``direnv``: Automate virtual **environments** & variables.
- ``pip-tools``: Automate **dependency** management.
- ``just``: Summarizing tasks into **one-liners** (upgrade, test, etc.).
- ``docker``: **Snapshot** current state of project.

---
<!-- ------------------------------------------------------------- -->
## Common Architecture: ``requirements.txt`` & ``.venv``
<!-- ------------------------------------------------------------- -->




---
<!-- ------------------------------------------------------------- -->
## Common Practice: Installing from GitHub
<!-- ------------------------------------------------------------- -->


```bash
git clone "<repo-url>"             # Download
python -m venv ".venv"             # Protect system packages
source .venv/bin/activate          # Activate virtual environment
pip install -r requirements.txt    # Install dependencies
```

#### Why this is not enough:
- ``requirements.txt`` only holds dependencies, not the **project structure**.
  - Python **can't import** local packages.
  - VS Code (sometimes) struggles with **refactoring** & **typing** across packages.
- ``requirements.txt`` could be outdated.
- Activating ``.venv`` can be forgotten or annoying.


---
<!-- ------------------------------------------------------------- -->
<!-- ------------------------------------------------------------- -->

<img src="../diagram/diagram.svg" alt="diagram.svg" width="1500px" style="background-color:transparent; float: right; margin-left: 20px; margin-bottom: 20px;">

<!-- ![bg](../diagram/diagram.svg)  -->




---


```python
import pandas as pd

def dsaf(column: str) -> pd.DataFrame:
    """
    This function does something with a DataFrame.
    """
    if a is None:
        raise ValueError("a must not be None")
    column = pd.concat()
    a = 1 + 2
    # Do something with df
    return df


class bla:
  
```
