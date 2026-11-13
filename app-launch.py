#!/usr/bin/env python3
"""Launch through the canonical saved management program."""
import runpy
import sys
from pathlib import Path
program = Path(__file__).resolve().parent / 'src/buildben_distr/artifacts/management/management.py'
sys.argv = [str(program), 'launch', *sys.argv[1:]]
runpy.run_path(str(program), run_name='__main__')
