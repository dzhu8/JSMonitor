#!/usr/bin/env python3
"""
NPM Dependency Updater

This script updates dependencies and devDependencies in a package.json file to their latest versions.
It fetches the latest versions from the npm registry and updates the package.json file with the "^" prefix.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple


def get_latest_package_version(package_name: str) -> str:
    """
    Get the latest version of a package from npm registry.

    Args:
        package_name: The name of the npm package to query.

    Returns:
        The latest version string of the package.

    Raises:
        Exception: If the package cannot be found or there's an error connecting to the npm registry.
    """
    url = f"https://registry.npmjs.org/{package_name}"

    try:
        with urllib.request.urlopen(url) as response:
            if response.status == 200:
                package_data = json.loads(response.read().decode('utf-8'))
                return package_data['dist-tags']['latest']
            else:
                raise Exception(f"Failed to get package info. Status code: {response.status}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise Exception(f"Package {package_name} not found")
        else:
            raise Exception(f"HTTP error for {package_name}: {e}")
    except Exception as e:
        raise Exception(f"Request error for {package_name}: {str(e)}")


def update_dependency(package_name: str, current_version: str, dependency_dict: Dict[str, str]) -> bool:
    """
    Update a single dependency with its latest version.

    Args:
        package_name: The name of the package to update.
        current_version: The current version string in package.json.
        dependency_dict: The dictionary of dependencies to modify.

    Returns:
        True if update was successful, False otherwise.
    """
    try:
        latest_version = get_latest_package_version(package_name)

        # Clean up version strings for comparison
        clean_current = current_version.lstrip("^~>=<")

        # Update the dependency
        dependency_dict[package_name] = f"^{latest_version}"

        # Print status with clear indication of out-of-date packages
        if clean_current != latest_version:
            print(f"  {package_name}: {current_version} → ^{latest_version} [OUT OF DATE]")
        else:
            print(f"  {package_name}: {current_version} → ^{latest_version} [CURRENT]")

        return True
    except Exception as e:
        print(f"  Failed to update {package_name}: {str(e)}")
        return False


def update_dependency_section(section: Dict[str, str], section_name: str):
    """
    Update all dependencies in a section (dependencies or devDependencies).

    Args:
        section: The dictionary of dependencies to update.
        section_name: The name of the section (for logging).
    """
    if not section:
        return

    print(f"Updating {section_name}...")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for package_name, current_version in section.items():
            futures.append(
                executor.submit(update_dependency, package_name, current_version, section)
            )

        # Wait for all updates to complete
        for future in futures:
            future.result()


def update_package_versions(directory_path: str) -> None:
    """
    Update package.json dependencies to their latest versions.

    Args:
        directory_path: Path to the directory containing package.json.

    Raises:
        FileNotFoundError: If the directory or package.json file is not found.
        Exception: For other errors during processing.
    """
    try:
        # Check if directory exists
        if not os.path.isdir(directory_path):
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        # Read package.json file
        package_json_path = os.path.join(directory_path, 'package.json')
        if not os.path.isfile(package_json_path):
            raise FileNotFoundError(f"package.json not found in {directory_path}")

        with open(package_json_path, 'r', encoding='utf-8') as f:
            package_json = json.load(f)

        print(f"\nChecking dependencies in: {package_json_path}\n")

        # Store out-of-date packages for summary
        out_of_date: List[Tuple[str, str, str]] = []

        # Track callback to collect out-of-date packages
        def track_outdated(package_name: str, current_version: str, latest_version: str) -> None:
            clean_current = current_version.lstrip("^~>=<")
            if clean_current != latest_version:
                out_of_date.append((package_name, current_version, latest_version))

        # Modify dependency sections to track out-of-date packages
        global update_dependency
        original_update = update_dependency

        def tracked_update(package_name: str, current_version: str, dependency_dict: Dict[str, str]) -> bool:
            try:
                latest_version = get_latest_package_version(package_name)
                clean_current = current_version.lstrip("^~>=<")
                dependency_dict[package_name] = f"^{latest_version}"

                if clean_current != latest_version:
                    print(f"  {package_name}: {current_version} → ^{latest_version} [OUT OF DATE]")
                    out_of_date.append((package_name, current_version, latest_version))
                else:
                    print(f"  {package_name}: {current_version} → ^{latest_version} [CURRENT]")

                return True
            except Exception as e:
                print(f"  Failed to update {package_name}: {str(e)}")
                return False

        # Replace function temporarily
        update_dependency = tracked_update

        # Update dependencies
        update_dependency_section(package_json.get('dependencies', {}), 'dependencies')

        # Update devDependencies
        update_dependency_section(package_json.get('devDependencies', {}), 'devDependencies')

        # Restore original function
        update_dependency = original_update

        # Write updated package.json
        with open(package_json_path, 'w', encoding='utf-8') as f:
            json.dump(package_json, f, indent=2)
            f.write('\n')  # Add newline at end of file

        # Print summary of out-of-date packages
        print("\n----- SUMMARY -----")
        if out_of_date:
            print(f"Found {len(out_of_date)} out-of-date package(s):")
            for pkg, old_ver, new_ver in out_of_date:
                print(f"{pkg}: {old_ver} --> {new_ver}")
        else:
            print("All packages are up to date!")

        print(f"\npackage.json has been updated successfully!")

    except FileNotFoundError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"Error updating package.json: {str(e)}")
        sys.exit(1)


def main() -> None:
    """
    Main function to parse arguments and execute the update.
    """
    if len(sys.argv) > 1:
        directory_path = os.path.abspath(sys.argv[1])
    else:
        print('Usage: npm_package_update.py <path-to-directory>')
        print('If no path is provided, the current directory will be used.')
        directory_path = os.getcwd()

    update_package_versions(directory_path)


if __name__ == "__main__":
    main()