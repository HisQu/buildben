"""Entry Point"""

# %%
# --- Standard Lib --------
# from pprint import pprint
from rich import print as rprint
from pathlib import Path

# --- Dependencies --------
from IPython.display import display
import pandas as pd

# --- Local Imports -------
import <my_project>.utils as ut
import <my_project>.paths as P


# --- Typing --------------
from typing import Any



# %%


# %%
if __name__ == "__main__":
    with ut.timer("Main Test Script Execution"):
        print(P.ROOT_PKG)
        
        from pprint import pprint
