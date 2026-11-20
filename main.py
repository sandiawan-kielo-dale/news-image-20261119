#!/usr/bin/env python3
"""Entry point for the make.fun news-image-20261119 bounty.

Copies the pre-rendered entry.png (sitting next to this file) into the
make.fun output directory as entry.png, after validating the PNG
signature, the IHDR dimensions (at most 1024x1024) and the file size
(at most 1 MiB). Standard library only; deterministic on every run.
"""
import os
import shutil
import struct
import sys

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_DIMENSION = 1024
MAX_BYTES = 1024 * 1024


def fail(message):
    print("error: " + message, file=sys.stderr)
    return 1


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "entry.png")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    dst = os.path.join(out_dir, "entry.png")

    if not os.path.isfile(src):
        return fail("entry.png not found next to main.py: " + src)

    with open(src, "rb") as fh:
        data = fh.read()

    if len(data) > MAX_BYTES:
        return fail("entry.png is %d bytes, over the 1 MiB limit" % len(data))
    if data[:8] != PNG_SIGNATURE:
        return fail("entry.png does not start with the PNG signature")
    if len(data) < 33 or data[12:16] != b"IHDR":
        return fail("entry.png has no IHDR chunk")
    width, height = struct.unpack(">II", data[16:24])
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        return fail("entry.png is %dx%d, over the 1024x1024 limit"
                    % (width, height))

    os.makedirs(out_dir, exist_ok=True)
    shutil.copyfile(src, dst)
    print("wrote %s (%dx%d, %d bytes)" % (dst, width, height, len(data)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
