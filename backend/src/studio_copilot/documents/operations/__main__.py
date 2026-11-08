"""python -m studio_copilot.documents.operations summarize --events-file PATH --output-dir PATH"""

import argparse
import json
import sys
from pathlib import Path

from .budget import OperationsError
from .report import summarize


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("summarize")
    command.add_argument("--events-file", type=Path, required=True)
    command.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(summarize(args.events_file, args.output_dir)))
        return 0
    except (OSError, ValueError, OperationsError):
        print("operations: summary failed; check local input and output paths.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
