#!/usr/bin/env python3
"""Render a staging /ai page by substituting its node origin."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

PRODUCTION_ORIGIN = "https://punkto.xyz"


def validate_origin(origin: str) -> None:
    try:
        parsed = urlsplit(origin)
        # Accessing port also validates malformed port values.
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("--origin must be an absolute http:// or https:// URL without a path") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or not parsed.hostname
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
        or origin.endswith("/")
        or any(char.isspace() for char in origin)
    ):
        raise ValueError("--origin must be an absolute http:// or https:// URL with no trailing slash or path")


def render(source_text: str, origin: str) -> tuple[str, int]:
    validate_origin(origin)
    count = source_text.count(PRODUCTION_ORIGIN)
    rendered = source_text.replace(PRODUCTION_ORIGIN, origin)
    if PRODUCTION_ORIGIN in rendered:
        raise ValueError("rendered output still contains the production origin")
    if origin not in rendered:
        raise ValueError("rendered output does not contain the target origin")
    return rendered, count


def atomic_write(output: Path, content: str) -> None:
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=output.parent,
            prefix=f".{output.name}.", suffix=".tmp", delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            temp_file.write(content)
        os.replace(temp_name, output)
    except OSError:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="pwa/ai.html")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    source = Path(args.source)
    output = Path(args.output)
    try:
        source_text = source.read_text(encoding="utf-8")
        rendered, count = render(source_text, args.origin)
        if args.check:
            if not output.exists():
                raise ValueError(f"--check output does not exist: {output}")
            if output.read_bytes() != rendered.encode("utf-8"):
                raise ValueError(f"--check failed: {output} differs from rendered output")
            print(f"checked {count} origin replacements from {source} for {args.origin} -> {output}")
        else:
            atomic_write(output, rendered)
            print(f"rendered {count} origin replacements from {source} to {args.origin} -> {output}")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
