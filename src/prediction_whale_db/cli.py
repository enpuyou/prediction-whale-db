import argparse
from collections.abc import Sequence
import sys
from typing import TextIO

from prediction_whale_db import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prediction-whale-db")
    parser.add_argument("--version", action="version", version=__version__)

    subcommands = parser.add_subparsers(dest="command", required=True)

    status_parser = subcommands.add_parser("status", help="show scaffold status")
    status_parser.set_defaults(handler=_handle_status)

    return parser


def _handle_status(stream: TextIO) -> int:
    print("prediction-whale-db scaffold is ready", file=stream)
    return 0


def main(argv: Sequence[str] | None = None, stream: TextIO | None = None) -> int:
    parser = build_parser()
    parsed_args = parser.parse_args(argv)
    output = stream if stream is not None else sys.stdout
    return parsed_args.handler(output)
