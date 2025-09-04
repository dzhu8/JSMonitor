#!/usr/bin/env python3
"""Command-line tool: visual-import-check

Scans source files for visual asset import statements (images, CSS, SVG, etc.)
and verifies that the referenced files exist at the specified location.
Prints missing files with file and line number, and exits with code 1 if any
imports point to non-existent files.

This version parallelizes file checks with a ThreadPoolExecutor, shows a
progress bar, and supports ignore rules via `--ignore` and `--ignore-regex`.
By default folders containing `node_modules` or `dist` are ignored.
"""

from __future__ import annotations
import fnmatch

import argparse
import concurrent.futures
import os
import re
from pathlib import Path
from typing import List, Pattern, Tuple


VISUAL_EXTENSIONS = r"(?:css|png|jpe?g|gif|svg|webp|avif|bmp|ico|tiff?)"

IMPORT_RE = re.compile(rf"^\s*(?:import|export)\s+(?:.*from\s+)?([\'\"])(?P<path>.*?\.{VISUAL_EXTENSIONS})\1\s*;?\s*$")
REQUIRE_RE = re.compile(rf"require\s*\(\s*([\'\"])(?P<path>.*?\.{VISUAL_EXTENSIONS})\1\s*\)")
DYNAMIC_IMPORT_RE = re.compile(rf"import\s*\(\s*([\'\"])(?P<path>.*?\.{VISUAL_EXTENSIONS})\1\s*\)")
IMPORT_PATTERNS = [IMPORT_RE, REQUIRE_RE, DYNAMIC_IMPORT_RE]


def find_source_files(
    directory: Path,
    patterns: List[str],
    ignore_substrings: List[str] | None = None,
    ignore_regexes: List[Pattern] | None = None,
) -> List[Path]:
    """
    Walk `directory` and return files matching any `patterns`.

    Args:
        directory: Root path to walk.
        patterns: Filename patterns to match (e.g., ['*.ts', '*.js']).
        ignore_substrings: Substrings of paths to skip.
        ignore_regexes: Compiled regexes to skip matching paths.

    Returns:
        A sorted list of `Path` objects matching the given patterns and not
        excluded by ignore rules.
    """
    if ignore_substrings is None:
        ignore_substrings = []
    if ignore_regexes is None:
        ignore_regexes = []

    # Normalize ignore directory names (strip trailing slashes)
    ignore_dir_names = [s.rstrip("/\\") for s in ignore_substrings]

    found: List[Path] = []
    for root, dirs, files in os.walk(directory):
        # Prune `dirs` in-place so os.walk won't recurse into them
        pruned_dirs = []
        for d in dirs:
            dpath = Path(root) / d
            dpath_text = dpath.as_posix()
            # skip if the directory path contains any ignore substring
            if any(sub in dpath_text for sub in ignore_substrings):
                continue
            # skip if any ignore-regex matches the directory path
            if any(rx.search(dpath_text) for rx in (ignore_regexes or [])):
                continue
            # optionally skip by exact directory name (helps common-case node_modules)
            if d in ignore_dir_names:
                continue
            pruned_dirs.append(d)
        # replace dirs so walk won't descend into pruned dirs
        dirs[:] = pruned_dirs

        # Now check files in this (non-ignored) directory
        for f in files:
            for pat in patterns:
                if fnmatch.fnmatch(f, pat):
                    found.append(Path(root) / f)
                    break

    # Keep deterministic order
    return sorted(found)


def check_css_imports(
    directory: Path,
    ignore_substrings: List[str] | None = None,
    ignore_regexes: List[Pattern] | None = None,
    verbose: bool = False,
) -> Tuple[int, List[str]]:
    """Scan source files and return (num_missing, messages).

    Args:
        directory: Directory to scan.
        ignore_substrings: Optional list of path substrings to ignore.
        ignore_regexes: Optional list of regex patterns to ignore.
        verbose: Print verbose output.

    Returns:
        A tuple `(num_missing, messages)` where `num_missing` is the number of
        missing CSS imports found and `messages` contains detailed strings.
    """
    patterns = ["*.ts", "*.tsx", "*.js", "*.jsx"]
    all_files = find_source_files(directory, patterns)

    if ignore_substrings is None:
        ignore_substrings = []
    if ignore_regexes is None:
        ignore_regexes = []

    # Filter files according to ignore substrings and regexes
    src_files: List[Path] = []
    skipped = 0
    for p in all_files:
        path_text = str(p.as_posix())
        if any(sub in path_text for sub in ignore_substrings):
            skipped += 1
            continue
        if any(rx.search(path_text) for rx in ignore_regexes):
            skipped += 1
            continue
        src_files.append(p)

    total_files = len(src_files)
    missing_messages: List[str] = []

    if total_files == 0:
        if verbose:
            print(f"No files to check (skipped {skipped} files by ignore rules).")
        return 0, []

    # Print total count
    print(f"Checking {total_files} files for CSS imports...")

    def check_file(src: Path) -> List[str]:
        """Check a single file for missing CSS imports.

        Args:
            src: Path to the source file to check.

        Returns:
            A list of message strings describing missing imports or read errors.
        """
        file_msgs: List[str] = []
        try:
            text = src.read_text(encoding="utf-8")
        except Exception as e:
            return [f"Failed reading {src}: {e}"]

            for lineno, line in enumerate(text.splitlines(), start=1):
                import_path = None

                for pat in IMPORT_PATTERNS:
                    m = pat.search(line)
                    if m:
                        import_path = m.group("path")
                        break

                if not import_path:
                    continue

                # Normalize and ignore remote URLs
                import_path_clean = import_path.split('?', 1)[0].split('#', 1)[0]
                if import_path_clean.startswith(('http://', 'https://')):
                    continue

                # Only attempt to resolve relative or absolute filesystem paths.
                # If the import does not start with '.' or '/', assume it's a module
                # import and skip it.
                try:
                    if import_path_clean.startswith('.'):
                        resolved = (src.parent / import_path_clean).resolve()
                    elif import_path_clean.startswith('/'):
                        resolved = Path(import_path_clean).resolve()
                    else:
                        # Likely a package import (e.g., from an asset loader). Skip.
                        continue

                    if not resolved.exists():
                        file_msgs.append(
                            f"{src} (line {lineno}): \nVisual asset not found: '{import_path}'\n"
                        )
                except Exception as e:
                    file_msgs.append(f"Failed resolving {src} (line {lineno}): {e}")

        return file_msgs

    # Use a ThreadPoolExecutor for IO-bound work (file reading)
    max_workers = min(32, (os.cpu_count() or 1) * 5)
    checked = 0
    bar_width = 40

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as exc:
        futures = {exc.submit(check_file, src): src for src in src_files}

        for fut in concurrent.futures.as_completed(futures):
            checked += 1
            try:
                file_msgs = fut.result()
            except Exception as exc_err:
                missing_messages.append(f"Error checking {futures[fut]}: {exc_err}")
                file_msgs = []

            if file_msgs:
                missing_messages.extend(file_msgs)

            # update progress bar
            progress = checked / total_files
            filled = int(bar_width * progress)
            bar = "#" * filled + "-" * (bar_width - filled)
            print(f"\r[{bar}] {checked}/{total_files}", end="", flush=True)

    print()

    return len(missing_messages), missing_messages


def compile_regex_list(patterns: List[str]) -> List[Pattern]:
    out: List[Pattern] = []
    for p in patterns:
        try:
            out.append(re.compile(p))
        except re.error:
            print(f"Warning: invalid regex in ignore-regex: {p}")
    return out


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that imported .css files referenced in source files actually exist."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to scan (default: current directory)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print verbose output",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        help="Ignore files whose path contains this substring. Can be provided multiple times.",
    )
    parser.add_argument(
        "--ignore-regex",
        action="append",
        default=[],
        help="Ignore files whose path matches this regex. Can be provided multiple times.",
    )

    args = parser.parse_args(argv)
    directory = Path(args.directory).resolve()

    if not directory.exists() or not directory.is_dir():
        print(f"Directory not found: {directory}")
        return 2

    default_ignores = ["node_modules", "dist"]
    ignore_substrings = default_ignores + args.ignore
    ignore_regexes = compile_regex_list(args.ignore_regex)

    missing_count, messages = check_css_imports(
        directory, ignore_substrings=ignore_substrings, ignore_regexes=ignore_regexes, verbose=args.verbose
    )

    if messages:
        for m in messages:
            print(m)

    if missing_count:
        print(f"\nTotal missing CSS imports: {missing_count}")
        return 1

    if args.verbose:
        print("All referenced CSS files were found.")

    return 0
