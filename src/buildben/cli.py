# buildben/cli.py
import argparse


def init_proj():
    print("Initializing project...")


def init_experiment():
    print("Initializing experiment...")


def main():
    parser = argparse.ArgumentParser(description="Buildben CLI Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # === Subcommands =================================================
    
    ### Subcommand: init-proj
    parser_init_proj = subparsers.add_parser(
        "init-proj", help="Initialize a project"
    )
    parser_init_proj.set_defaults(func=init_proj)

    ### Subcommand: init-experiment
    parser_init_experiment = subparsers.add_parser(
        "init-experiment", help="Initialize an experiment"
    )
    parser_init_experiment.set_defaults(func=init_experiment)

    # === Parse arguments
    args = parser.parse_args()
    args.func()


if __name__ == "__main__":
    main()
