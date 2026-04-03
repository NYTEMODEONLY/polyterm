#!/usr/bin/env python3
"""Validate that documentation stays in sync with code modules.

Checks:
1. File existence — every Python module in tracked dirs has a corresponding .md in docs/
2. Broken links — internal markdown links resolve to existing files
3. Stub detection — flag suspiciously short or placeholder doc files
4. Auto-stub generation — optionally generate stub files for missing modules
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Source directories to track (relative to repo root)
TRACKED_DIRS = [
    "polyterm/cli/commands",
    "polyterm/tui/screens",
    "polyterm/api",
    "polyterm/core",
    "polyterm/db",
    "polyterm/utils",
]

# Map source dirs to doc dirs
DOC_DIR_MAP = {
    "polyterm/cli/commands": "docs/cli",
    "polyterm/tui/screens": "docs/tui/screens",
    "polyterm/api": "docs/api",
    "polyterm/core": "docs/core",
    "polyterm/db": "docs/db",
    "polyterm/utils": "docs/utils",
}

# Modules to skip (not user-facing, no docs needed)
SKIP_MODULES = {"__init__.py"}

# Minimum lines for a doc to not be flagged as a stub
MIN_DOC_LINES = 50

# Placeholder patterns that indicate a stub
PLACEHOLDER_PATTERNS = [
    r"\{.*\}",          # Template placeholders like {Feature Name}
    r"TODO",
    r"FIXME",
    r"placeholder",
    r"coming soon",
]


def get_python_modules(src_dir: Path) -> list[Path]:
    """Return non-init .py files in a source directory."""
    if not src_dir.exists():
        return []
    return sorted(
        p for p in src_dir.glob("*.py")
        if p.name not in SKIP_MODULES and not p.name.startswith("_")
    )


def expected_doc_path(module_path: Path, src_dir_rel: str) -> Path:
    """Return the expected .md doc path for a given Python module."""
    doc_dir = DOC_DIR_MAP[src_dir_rel]
    stem = module_path.stem
    return REPO_ROOT / doc_dir / f"{stem}.md"


def check_file_existence() -> tuple[list[str], list[str]]:
    """Check that every tracked module has a corresponding doc file.

    Returns (errors, warnings) lists.
    """
    errors = []
    missing_modules = []

    for src_dir_rel in TRACKED_DIRS:
        src_dir = REPO_ROOT / src_dir_rel
        modules = get_python_modules(src_dir)

        for mod in modules:
            doc_path = expected_doc_path(mod, src_dir_rel)
            if not doc_path.exists():
                errors.append(
                    f"MISSING DOC: {mod.relative_to(REPO_ROOT)} -> "
                    f"expected {doc_path.relative_to(REPO_ROOT)}"
                )
                missing_modules.append((mod, src_dir_rel))

    return errors, missing_modules


def check_broken_links() -> list[str]:
    """Check all internal markdown links resolve to existing files."""
    errors = []
    docs_root = REPO_ROOT / "docs"

    if not docs_root.exists():
        return errors

    link_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")

    for md_file in docs_root.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        for match in link_pattern.finditer(content):
            link_text, link_target = match.group(1), match.group(2)

            # Skip external links and anchors
            if link_target.startswith(("http://", "https://", "#", "mailto:")):
                continue

            # Strip anchor from link
            link_path = link_target.split("#")[0]
            if not link_path:
                continue

            # Resolve relative to the file's directory
            resolved = (md_file.parent / link_path).resolve()
            if not resolved.exists():
                rel_file = md_file.relative_to(REPO_ROOT)
                errors.append(
                    f"BROKEN LINK: {rel_file} -> [{link_text}]({link_target}) "
                    f"(resolved to {resolved.relative_to(REPO_ROOT)})"
                )

    return errors


def check_stubs() -> list[str]:
    """Flag doc files that are suspiciously short or contain placeholder text."""
    warnings = []
    docs_root = REPO_ROOT / "docs"

    if not docs_root.exists():
        return warnings

    for md_file in docs_root.rglob("*.md"):
        # Skip top-level project docs (ROADMAP, etc.)
        if md_file.parent == docs_root:
            continue

        content = md_file.read_text(encoding="utf-8")
        lines = content.strip().splitlines()

        if len(lines) < MIN_DOC_LINES:
            rel = md_file.relative_to(REPO_ROOT)
            warnings.append(
                f"STUB (short): {rel} has only {len(lines)} lines "
                f"(minimum {MIN_DOC_LINES})"
            )

        for pattern in PLACEHOLDER_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                rel = md_file.relative_to(REPO_ROOT)
                warnings.append(
                    f"STUB (placeholder): {rel} contains placeholder "
                    f"text matching /{pattern}/"
                )
                break  # one warning per file

    return warnings


def generate_stub(module_path: Path, src_dir_rel: str) -> str:
    """Generate a documentation stub for a module."""
    stem = module_path.stem
    # Convert snake_case to Title Case
    title = stem.replace("_", " ").title()

    # Try to extract the module docstring
    docstring = ""
    try:
        content = module_path.read_text(encoding="utf-8")
        # Simple docstring extraction (triple-quoted string after module start)
        match = re.search(r'^"""(.*?)"""', content, re.DOTALL)
        if match:
            docstring = match.group(1).strip().split("\n")[0]
    except Exception:
        pass

    description = docstring if docstring else f"Documentation for {stem} module."
    source = f"`{module_path.relative_to(REPO_ROOT)}`"

    return f"""# {title}

> {description}

## Overview

<!-- TODO: Describe what this module does and why it exists -->

## Source

{source}

## Usage

<!-- TODO: Add usage examples -->

## How It Works

<!-- TODO: Explain the underlying logic -->

## Related Features

<!-- TODO: Link to related documentation -->
"""


def auto_generate_stubs(
    missing_modules: list[tuple[Path, str]], dry_run: bool = True
) -> list[str]:
    """Generate stub doc files for modules that lack documentation."""
    messages = []

    for mod, src_dir_rel in missing_modules:
        doc_path = expected_doc_path(mod, src_dir_rel)

        if dry_run:
            messages.append(
                f"WOULD CREATE: {doc_path.relative_to(REPO_ROOT)} "
                f"(stub for {mod.relative_to(REPO_ROOT)})"
            )
        else:
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            stub_content = generate_stub(mod, src_dir_rel)
            doc_path.write_text(stub_content, encoding="utf-8")
            messages.append(
                f"CREATED: {doc_path.relative_to(REPO_ROOT)} "
                f"(stub for {mod.relative_to(REPO_ROOT)})"
            )

    return messages


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate documentation stays in sync with code."
    )
    parser.add_argument(
        "--generate-stubs",
        action="store_true",
        help="Generate stub doc files for missing modules (non-blocking warnings)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what stubs would be generated without creating them",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Documentation Validation")
    print("=" * 60)

    all_errors = []
    all_warnings = []

    # 1. File existence check
    print("\n## Checking module-to-doc file mapping...")
    existence_errors, missing_modules = check_file_existence()
    all_errors.extend(existence_errors)
    if existence_errors:
        for e in existence_errors:
            print(f"  ERROR: {e}")
    else:
        print("  All modules have corresponding documentation files.")

    # 2. Broken link check
    print("\n## Checking for broken internal links...")
    link_errors = check_broken_links()
    all_errors.extend(link_errors)
    if link_errors:
        for e in link_errors:
            print(f"  ERROR: {e}")
    else:
        print("  No broken links found.")

    # 3. Stub detection
    print("\n## Checking for stub/placeholder documentation...")
    stub_warnings = check_stubs()
    all_warnings.extend(stub_warnings)
    if stub_warnings:
        for w in stub_warnings:
            print(f"  WARNING: {w}")
    else:
        print("  No stubs detected.")

    # 4. Auto-stub generation
    if missing_modules and (args.generate_stubs or args.dry_run):
        dry_run = args.dry_run or not args.generate_stubs
        action = "Previewing" if dry_run else "Generating"
        print(f"\n## {action} stub documentation files...")
        stub_messages = auto_generate_stubs(missing_modules, dry_run=dry_run)
        all_warnings.extend(stub_messages)
        for m in stub_messages:
            print(f"  {m}")

    # Summary
    print("\n" + "=" * 60)
    print(f"Errors: {len(all_errors)}  |  Warnings: {len(all_warnings)}")
    print("=" * 60)

    if all_errors:
        print("\nFAILED: Documentation validation found blocking errors.")
        return 1
    elif all_warnings:
        print("\nPASSED with warnings.")
        return 0
    else:
        print("\nPASSED: All documentation is in sync.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
