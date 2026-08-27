"""Remove volatile Word-export metadata while preserving the rendered PDF."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, ByteStringObject, NameObject


FIXED_IDENTIFIER = bytes.fromhex("e22f60de09b88cf01ad997969f48f53e")
FIXED_DATE = "D:20260827000000+00'00'"


def normalise(source: Path, destination: Path) -> None:
    reader = PdfReader(source)
    writer = PdfWriter(clone_from=reader)

    writer.add_metadata(
        {
            "/Title": "Development and Freeze of a Point-in-Time Multi-Horizon ETF Rotation Strategy for a UK SIPP",
            "/Subject": "Project EDGE / UKACTIVE — E2 developmental scientific paper",
            "/Author": "",
            "/Creator": "Deterministic Word-to-PDF publication pipeline",
            "/Producer": f"pypdf {__import__('pypdf').__version__}",
            "/CreationDate": FIXED_DATE,
            "/ModDate": FIXED_DATE,
            "/Keywords": "ETF rotation; industry momentum; point-in-time data; UK SIPP",
        }
    )

    # Word embeds an XMP packet with volatile timestamps. The fixed Info
    # dictionary above is sufficient for this archival publication.
    if NameObject("/Metadata") in writer._root_object:
        del writer._root_object[NameObject("/Metadata")]
    writer._ID = ArrayObject(
        [ByteStringObject(FIXED_IDENTIFIER), ByteStringObject(FIXED_IDENTIFIER)]
    )

    temporary = destination.with_suffix(".normalised.tmp.pdf")
    with temporary.open("wb") as handle:
        writer.write(handle)
    temporary.replace(destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    normalise(args.source.resolve(), args.destination.resolve())
    digest = hashlib.sha256(args.destination.read_bytes()).hexdigest()
    print(f"PDF {args.destination.resolve()} sha256={digest}")


if __name__ == "__main__":
    main()
