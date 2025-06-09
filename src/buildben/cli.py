# buildben/cli.py
import argparse
from . import init_proj     # each sub-command module

def main() -> None:
    parser = argparse.ArgumentParser(prog="buildben", description="Buildben CLI")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    ### Wire up every command you want to support
    init_proj.add_parser(subparsers)
    # init_experiment.add_parser(subparsers)   # when you refactor the next one
    
    ### Parse args and run the command
    args = parser.parse_args()
    args.func(args)          # ⚠ pass the Namespace to the handler

if __name__ == "__main__":
    main()