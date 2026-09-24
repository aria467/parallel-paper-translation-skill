#!/usr/bin/env python3
"""Prepare isolated PDF copies and merge audited translation fragments."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slug(title: str) -> str:
    value = re.sub(r"[^\w]+", "-", title.casefold()).strip("-_−")
    value = value.encode("utf-8")[:45].decode("utf-8", errors="ignore").strip("-_−")
    return value or "section"


def section_id(title: str) -> str:
    match = re.match(r"^\s*(\d+(?:\.\d+)*)\.?\s+", title)
    if not match:
        raise ValueError(f"Not a numbered heading: {title!r}")
    return match.group(1)


def prepare(args: argparse.Namespace) -> None:
    source = Path(args.pdf).expanduser().resolve(strict=True)
    workspace = Path(args.workspace).expanduser().resolve()
    headings = json.loads(Path(args.headings).expanduser().read_text(encoding="utf-8"))
    if not isinstance(headings, list) or len(headings) < 2:
        raise ValueError("Headings JSON must be an ordered array with References last")
    if not all(isinstance(item, str) and item.strip() for item in headings):
        raise ValueError("Every heading must be a nonempty string")
    if headings[-1].strip().casefold() != "references":
        raise ValueError("The last boundary must be References")
    ids = [section_id(title) for title in headings[:-1]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate section numbers")

    manifest_path = workspace / "fragment_manifest.json"
    pdf_dir = workspace / "pdf_copies"
    fragments_dir = workspace / "outputs" / "translated_fragments"
    if manifest_path.exists() or pdf_dir.exists() or fragments_dir.exists():
        raise FileExistsError("Use a fresh workspace; this run already has translation files")

    pdf_dir.mkdir(parents=True)
    fragments_dir.mkdir(parents=True)
    original_hash = sha256(source)
    fragments: list[dict[str, object]] = []
    for number, (start, end) in enumerate(zip(headings, headings[1:]), 1):
        pdf_copy = pdf_dir / f"translater_{number:02d}.pdf"
        shutil.copyfile(source, pdf_copy)
        if sha256(pdf_copy) != original_hash:
            raise OSError(f"PDF copy {number} differs from source")
        filename = f"{number:02d}__{slug(start)}__to__{slug(end)}.md"
        fragments.append(
            {
                "number": number,
                "start": start,
                "end": end,
                "pdf": str(pdf_copy),
                "output": str(fragments_dir / filename),
            }
        )

    manifest = {"source_pdf": str(source), "source_sha256": original_hash, "fragments": fragments}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(fragments)} identical PDF copies; SHA-256 {original_hash}")
    print(manifest_path)


def receipt_path(manifest_path: Path, number: int) -> Path:
    return manifest_path.parent / "verified_handoffs" / f"{number:02d}.sha256"


def verify(args: argparse.Namespace) -> None:
    manifest_path = Path(args.manifest).expanduser().resolve(strict=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fragments = manifest["fragments"]
    number = args.number
    if number < 1 or number > len(fragments):
        raise ValueError(f"Fragment number out of range: {number}")
    record = fragments[number - 1]
    if record["number"] != number:
        raise ValueError("Manifest fragment order is not sequential")
    fragment_path = Path(record["output"]).resolve(strict=True)
    final_text_path = Path(args.final_text).expanduser().resolve(strict=True)
    if final_text_path.samefile(fragment_path):
        raise ValueError("Final reply must be captured separately from the auditor's file")
    final_digest = sha256(final_text_path)
    saved_digest = sha256(fragment_path)
    if final_digest != saved_digest:
        raise ValueError(
            f"Fragment {number} handoff SHA-256 mismatch; "
            f"final={final_digest} saved={saved_digest}"
        )
    receipt = receipt_path(manifest_path, number)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(saved_digest + "\n", encoding="ascii")
    print(f"Verified fragment {number}: {saved_digest}")


def merge(args: argparse.Namespace) -> None:
    manifest_path = Path(args.manifest).expanduser().resolve(strict=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fragments = manifest["fragments"]
    if not fragments:
        raise ValueError("Manifest contains no fragments")
    expected = [Path(record["output"]) for record in fragments]
    actual = list(expected[0].parent.glob("*.md"))
    if set(actual) != set(expected):
        missing = sorted(str(path) for path in set(expected) - set(actual))
        extra = sorted(str(path) for path in set(actual) - set(expected))
        raise ValueError(f"Fragment set mismatch; missing={missing}; extra={extra}")

    content: list[str] = []
    for number, (record, path) in enumerate(zip(fragments, expected), 1):
        if record["number"] != number:
            raise ValueError("Manifest fragment order is not sequential")
        receipt = receipt_path(manifest_path, number)
        if not receipt.is_file() or receipt.read_text(encoding="ascii").strip() != sha256(path):
            raise ValueError(f"Missing or stale SHA-256 handoff verification for fragment {number}")
        text = path.read_bytes().decode("utf-8")
        if not text or text.startswith("\ufeff"):
            raise ValueError(f"Empty or BOM-prefixed fragment: {path}")
        sid = section_id(record["start"])
        level = min(2 + sid.count("."), 6)
        first_line = text.splitlines()[0]
        if not re.match(rf"^#{{{level}}}\s+{re.escape(sid)}(?:\.|\s)", first_line):
            raise ValueError(f"Wrong opening heading in fragment {number}: {first_line!r}")
        if re.search(r"(?im)^#{1,6}\s*(?:references|参考文献)(?:\s|$)", text):
            raise ValueError(f"References heading found in fragment {number}")
        content.append(text)

    merged = content[0]
    for part in content[1:]:
        separator = "" if merged.endswith(("\n\n", "\r\n\r\n")) else "\n" if merged.endswith("\n") else "\n\n"
        merged += separator + part
    output = Path(args.output).expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"Merged output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(merged.encode("utf-8"))
    print(f"Merged {len(content)} fragments into {output}")
    print(f"SHA-256 {sha256(output)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare", help="copy source PDF once per heading interval")
    prep.add_argument("--pdf", required=True)
    prep.add_argument("--headings", required=True, help="UTF-8 JSON array, ending with References")
    prep.add_argument("--workspace", required=True, help="fresh run directory")
    prep.set_defaults(run=prepare)
    checked = commands.add_parser("verify", help="compare SHA-256 of a translator's raw final reply and the auditor's file")
    checked.add_argument("--manifest", required=True)
    checked.add_argument("--number", required=True, type=int)
    checked.add_argument("--final-text", required=True, help="separate file containing the raw final reply")
    checked.set_defaults(run=verify)
    combined = commands.add_parser("merge", help="combine all audited fragments in manifest order")
    combined.add_argument("--manifest", required=True)
    combined.add_argument("--output", required=True)
    combined.set_defaults(run=merge)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
