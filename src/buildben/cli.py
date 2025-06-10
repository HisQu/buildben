# buildben/cli.py
import argparse
from . import init_proj
from . import init_experim

def main() -> None:
    ### Init parsers
    # > Create a top-level parser
    PARSER = argparse.ArgumentParser(
        prog="buildben", description="Buildben CLI"
    )
    # > Create subparser, will be modified in place to include script-parsers
    subparsers: argparse._SubParsersAction = PARSER.add_subparsers(
        dest="cmd", required=True
    )

    ### Edit subparser in place to include script-specific parsers
    init_proj.add_parser(subparsers)
    init_experim.add_parser(subparsers)

    ### Parse args and run the command
    args = PARSER.parse_args()
    args.func(args)  # < ⚠ pass the Namespace to the handler

if __name__ == "__main__":
    main()
