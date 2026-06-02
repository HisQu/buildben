

<!-- This is a comment -->

<!-- ============================================================== -->
<!-- == Header ==================================================== -->
<div align="center">

<!-- --- Title ---------------------------------------------------- -->
# `{my_project}`: A Template


<!-- --- Logo ----------------------------------------------------- -->
*Part of:*

<a href="https://hisqu.de" target="_blank">
  <img 
  src="https://avatars.githubusercontent.com/u/196629600?s=200&v=4" 
  width="100px" alt="logo"
  style="margin-top: -10px;"> 
</a>

<br>

<!-- --- Badges --------------------------------------------------- -->
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Pyright](https://img.shields.io/badge/type%20checked-pyright-blue)](https://microsoft.github.io/pyright/)
[![pytest](https://img.shields.io/badge/tested%20with-pytest-0A9EDC)](https://docs.pytest.org/)
<!-- [![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/HisQu/haiu/blob/main/LICENSE) -->




</div>

<!-- --- URLs --------------------------------------------------- -->
[`direnv`]: https://direnv.net/
[`just`]: https://github.com/casey/just?tab=readme-ov-file#packages
[`uv`]: https://github.com/astral-sh/uv?tab=readme-ov-file#uv


<!-- ============================================================== -->
<!-- ============================================================== -->

<div style="width: 85%; margin: 2rem auto; text-align: justify;">
<hr>

###  `{my_project}` ...
<!-- Summarize the top 3 features -->
- ... integrates cool things like lorem ipsum dolor
- ... standardizes Dolor sit amet dolor blah bla
- ... Ipsum dolor sit amet 


#### Main dependencies:
<!-- List your main dependencies here and explain why they're important. -->
- **`apprc`**: Runtime config, generated `config` CLI, Textual editor, and logging.

<hr>
</div>


<!-- Graphical Abstract goes here: -->

<!-- | ![Graphical abstract](./assets/figures/graphical-abstract_init-proj-graphviz.svg) |
|:--:|
| **Fig. 1 - Graphical Abstract:** Buildben creates scaffolds for Python projects adhering to Python PEP standards. |

<br> -->

<!-- HTML-version of Graphical Abstract -->
<!-- 
<div align="center">
  <img src="https://github.com/HisQu/buildben/raw/main/assets/figures/diagram-graphviz.svg"
       width="800px" alt="Management of Virtual Environments & Dependencies" >
  <p><em> 
  <b> Graphical Abstract: </b> 
  Management of Virtual Environments & Dependencies. Red dashed lines are Dependencies.
  </em></p>
</div> 




-->




<!-- ============================================================== -->
<!-- ============================================================== -->
### Table of Contents

<!-- toc -->

1. [`{my_project}`: A Template](#my_project-a-template)
   1. [📦 Installation](#-installation)
   2. [🚀 Usage](#-usage)
   3. [💻  Development](#--development)
   4. [📚  Examples / Documentation](#--examples--documentation)

<!-- tocstop -->
<!-- /toc -->

<br>

<!-- ============================================================== -->
<!-- ============================================================== -->
## 📦 Installation

### Prerequisites:
- `Python >=3.12,<3.13`
- `git`
- `uv` (optional)


### Install with `pip`:
#### 1. Install system dependencies:
``` bash
apt update
apt install python3.12
```
<!-- git clone https://github.com/{github_username}/{my_project}.git -->
#### 2. Clone & Install `{my_project}`:
``` bash
git clone https://github.com/HisQu/{my_project}.git
cd {my_project}
python -m pip install -e "."              # Core runtime dependencies
python -m pip install -e ".[rag]"         # Core + published RAG extra
python -m pip install -e "." --group dev  # Core + local dev tools
python -m pip install -e ".[rag]" --group dev
```
The `rag` commands apply after the commented `rag` extra in `pyproject.toml` is
uncommented and populated.

#### ✅ Verify installation: 
```bash
python -m {my_project}.main --help
{my_project} config doctor
```


<br>

<!-- ============================================================== -->
<!-- ============================================================== -->
## 🚀 Usage

<!-- Present a minimal example of the most important feature! -->

### Do this:
```bash
{my_project} config init /absolute/path/to/storage --name default --default
{my_project} config doctor
{my_project} config show --json
```
 
### Do that:
```bash
{my_project} config set app.message "Hello local storage"
{my_project} config edit
```



<br>

<!-- ============================================================== -->
<!-- ============================================================== -->
## 💻  Development 

### Dev-Hints:
- **Issues:** Open an issue on GitHub!
- **Contribute:** Feel free to fork this repo and submit a PR!



<!-- --- Testing ------------------------------------------------- -->

<details><summary> <h3> <i> Testing </i> </h3> </summary>

*!! Pytest not yet Implemented!*
```bash
python -m pip install -e "." --group dev  # Install testing tools from [dependency-groups]
pytest                                    # Run tests
```
</details>


<!-- --- Diagrams ------------------------------------------------- -->

<details><summary> <h3> <i> Class Diagram </i> </h3> </summary>
<blockquote>

<!-- Make a mermaid class diagram / flowchart! -->

<!-- <img src="https://raw.githubusercontent.com/markur4/plotastic/main/class_diagram.svg" alt="logo"> -->

</blockquote></details>



<br>

<!-- ============================================================== -->
<!-- ============================================================== -->
## 📚  Examples / Documentation 


<!-- This is a presentation / documentation of **specific** options. 
If available, link to files (e.g. .ipynb) in the examples folder! -->

<details><summary> <h3> <i> Example 1 </i> </h3> </summary>
<blockquote>

```bash
# Generate a quick plot from sample_data.csv
python -m {my_project} sample_data.csv --output plot.png
```

</blockquote></details>


<!-- --- Separator ------------------------------------------------ -->

<details><summary> <h3> <i> Example 1 </i> </h3> </summary>
<blockquote>


```bash
# Generate a quick plot from sample_data.csv
python -m {my_project} sample_data.csv --output plot.png
```

</blockquote></details>


<br>
