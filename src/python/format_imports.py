import argparse
import glob
import json
import os
import re

# Regex to find import/export statements.
# Handles: import ... from '...'; export ... from '...'; import '...';
IMPORT_REGEX = re.compile(r"""(?:import|export)(?:.*from\s*)?(["'])(.+?)\1""")


def get_tsconfig_paths_and_baseurl(directory):
    """
    Finds tsconfig.json or jsconfig.json and extracts baseUrl and path aliases.
    Processes aliases of the form "alias_prefix/*": ["./target_path/*", ...].

    Args:
        directory: Path to the project root where tsconfig.json or jsconfig.json may live.

    Returns:
        A tuple `(resolved_aliases, abs_base_url)` where `resolved_aliases` is a
        dictionary mapping alias prefixes to lists of absolute target directories,
        and `abs_base_url` is the absolute baseUrl resolved from the config.
        If no config is found or an error occurs, returns `(None, None)`.
    """
    tsconfig_filename = "tsconfig.json"
    tsconfig_path = os.path.join(directory, tsconfig_filename)

    if not os.path.isfile(tsconfig_path):
        jsconfig_filename = "jsconfig.json"
        jsconfig_path = os.path.join(directory, jsconfig_filename)
        if not os.path.isfile(jsconfig_path):
            print(f"No {tsconfig_filename} or {jsconfig_filename} found in {directory}")
            return None, None
        tsconfig_path = jsconfig_path
        print(f"Using {jsconfig_filename} from {directory}")
    else:
        print(f"Using {tsconfig_filename} from {directory}")

    try:
        with open(tsconfig_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {tsconfig_path}")
        return None, None
    except Exception as e:
        print(f"Error reading {tsconfig_path}: {e}")
        return None, None

    compiler_options = config.get("compilerOptions", {})
    base_url_rel = compiler_options.get("baseUrl", ".")
    paths = compiler_options.get("paths", {})

    abs_tsconfig_dir = os.path.dirname(tsconfig_path)
    abs_base_url = os.path.abspath(os.path.join(abs_tsconfig_dir, base_url_rel))

    resolved_aliases = {}
    if paths:
        for alias_pattern, target_patterns_in_tsconfig in paths.items():
            if not alias_pattern.endswith("/*"):
                # print(f"Skipping alias '{alias_pattern}': only 'alias/*' patterns are currently supported.")
                continue

            alias_prefix = alias_pattern[:-1]  # e.g., "@/" from "@/*"

            current_alias_abs_target_dirs = []
            for target_path_pattern in target_patterns_in_tsconfig:
                if not target_path_pattern.endswith("/*"):
                    # print(f"Skipping target '{target_path_pattern}' for alias '{alias_pattern}': only 'target/*' patterns are currently supported.")
                    continue

                target_dir_rel_to_baseurl = target_path_pattern[:-1]  # e.g., "./src/"
                abs_target_dir = os.path.normpath(
                    os.path.join(abs_base_url, target_dir_rel_to_baseurl)
                )
                current_alias_abs_target_dirs.append(abs_target_dir)

            if current_alias_abs_target_dirs:
                resolved_aliases[alias_prefix] = current_alias_abs_target_dirs

    return resolved_aliases, abs_base_url


def format_single_import_path(
    original_module_path, current_file_abs_dir, path_aliases_map, abs_base_url
):
    """
    Attempts to convert an original_module_path to an aliased path.

    Args:
        original_module_path: The module path string from the import statement
            (e.g., '../../utils/helpers').
        current_file_abs_dir: Absolute directory of the file containing the import.
        path_aliases_map: Mapping produced by `get_tsconfig_paths_and_baseurl`,
            e.g. `{"@/": ["/abs/project/src/"]}`.
        abs_base_url: Absolute baseUrl from tsconfig.

    Returns:
        The possibly rewritten import path using the configured alias prefix,
        or the original import path if no alias match was found.
    """
    # Skip non-relative paths (node_modules, built-ins) which don't start with '.'
    # Also skip absolute paths if they are not meant to be aliased (though less common in imports)
    if not original_module_path.startswith(
        "."
    ):  # and not os.path.isabs(original_module_path):
        return original_module_path

    # Resolve the original import path to an absolute path
    if os.path.isabs(
        original_module_path
    ):  # Should generally not happen for typical project imports
        abs_imported_item_path = os.path.normpath(original_module_path)
    else:
        abs_imported_item_path = os.path.normpath(
            os.path.join(current_file_abs_dir, original_module_path)
        )

    best_aliased_path = original_module_path
    longest_target_prefix_match_len = -1

    for alias_prefix_str, abs_target_dirs_for_alias in path_aliases_map.items():
        for abs_target_dir in abs_target_dirs_for_alias:
            # Ensure abs_target_dir ends with a separator for correct prefix matching
            # e.g., /abs/project/src becomes /abs/project/src/
            # This makes '/abs/project/src/foo'.startswith('/abs/project/src/') work correctly.
            target_dir_path_for_match = os.path.join(
                abs_target_dir, ""
            )  # Adds os.sep if not present at end

            if abs_imported_item_path.startswith(target_dir_path_for_match):
                # Calculate the part of the path relative to the target directory
                relative_suffix = abs_imported_item_path[
                    len(target_dir_path_for_match) :
                ]
                relative_suffix = relative_suffix.replace(
                    os.sep, "/"
                )  # Standardize to forward slashes

                potential_new_path = alias_prefix_str + relative_suffix

                current_match_len = len(target_dir_path_for_match)
                if current_match_len > longest_target_prefix_match_len:
                    longest_target_prefix_match_len = current_match_len
                    best_aliased_path = potential_new_path
                elif current_match_len == longest_target_prefix_match_len:
                    # If target prefix match length is the same, prefer the shorter resulting aliased path
                    if len(potential_new_path) < len(best_aliased_path):
                        best_aliased_path = potential_new_path

    return best_aliased_path


def process_file_content(content, file_abs_dir, path_aliases_map, abs_base_url):
    """
    Applies import formatting to the string content of a file.

    Args:
        content: The file contents as a string.
        file_abs_dir: Absolute directory of the file being processed.
        path_aliases_map: Alias mapping from `get_tsconfig_paths_and_baseurl`.
        abs_base_url: Absolute baseUrl from tsconfig.

    Returns:
        The modified file content with imports rewritten where applicable.
    """
    modified_content = content

    def replace_import_path_match(match_obj):
        quote_char = match_obj.group(1)
        original_path = match_obj.group(2)

        if not original_path or original_path.isspace():
            return match_obj.group(0)

        new_path = format_single_import_path(
            original_path, file_abs_dir, path_aliases_map, abs_base_url
        )

        if new_path != original_path:
            # Ensure the full matched string is reconstructed correctly
            # The regex is (?:import|export)(?:.*from\s*)?(["'])(.+?)\1
            # match_obj.group(0) is the whole import statement part like `from "./foo"` or just `"./foo"`
            # We need to replace original_path within quote_char + original_path + quote_char
            return match_obj.group(0).replace(
                quote_char + original_path + quote_char,
                quote_char + new_path + quote_char,
            )
        return match_obj.group(0)

    modified_content = IMPORT_REGEX.sub(replace_import_path_match, modified_content)
    return modified_content


def main():
    """
    Command-line entrypoint for formatting import paths using tsconfig/jsconfig.
    """
    parser = argparse.ArgumentParser(
        description="Format import statements based on tsconfig.json/jsconfig.json paths."
    )
    parser.add_argument(
        "--version",
        action="version",
        version="format-imports v0.2.0",  # Match versioning scheme
        help="Show the version number and exit",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=os.getcwd(),
        help="The root directory to scan for tsconfig/jsconfig and source files (defaults to current directory).",
    )
    args = parser.parse_args()

    root_dir = os.path.abspath(args.directory)
    print(f"Starting import formatting in directory: {root_dir}")

    path_aliases, abs_base_url = get_tsconfig_paths_and_baseurl(root_dir)

    if not path_aliases:
        print(
            "No path aliases found or tsconfig/jsconfig.json processing failed. Exiting."
        )
        return

    print(f"Effective baseUrl: {abs_base_url}")
    print(f"Loaded path aliases: {json.dumps(path_aliases, indent=2)}")

    # Define file extensions to process
    file_patterns = ["**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx", "**/*.vue"]
    files_to_scan = []
    for pattern in file_patterns:
        # glob from root_dir
        glob_pattern = os.path.join(root_dir, pattern)
        files_to_scan.extend(glob.glob(glob_pattern, recursive=True))

    # Filter out files from common ignored directories
    ignored_dirs_parts = {os.sep + "node_modules" + os.sep, os.sep + ".git" + os.sep}

    processed_files_count = 0
    for file_path in files_to_scan:
        # Check if any part of the path indicates an ignored directory
        if any(ignored_part in file_path for ignored_part in ignored_dirs_parts):
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()
        except Exception as e:
            continue

        file_abs_dir = os.path.dirname(
            file_path
        )  # file_path is already absolute from glob
        modified_content = process_file_content(
            original_content, file_abs_dir, path_aliases, abs_base_url
        )

        if modified_content != original_content:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(modified_content)
                print(f"  Formatted imports in {os.path.basename(file_path)}")
                processed_files_count += 1
            except Exception as e:
                print(f"  Error writing updated file: {e}")
        # else:
        # print(f"  No changes for {os.path.basename(file_path)}")

    print(f"Import formatting complete. {processed_files_count} file(s) modified.")


if __name__ == "__main__":
    main()
