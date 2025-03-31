#!/usr/bin/env python3
"""
NPM Import Scanner and Installer

This script scans JavaScript and TypeScript files in a directory for import statements,
identifies packages that are not installed in node_modules, and installs them.
It also updates the package.json file to include these newly installed packages.
"""

import json
import os
import sys
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Set, Tuple

# Import shared utility functions
from utils import get_latest_package_version, get_installed_packages


def find_js_ts_files(directory_path: str) -> List[str]:
    """
    Find all JavaScript and TypeScript files in a directory recursively.

    Args:
        directory_path: The root directory to search in.

    Returns:
        A list of file paths to .js, .jsx, .ts, and .tsx files.
    """
    js_ts_files = []
    # Directories to skip
    excluded_dirs = {'node_modules', '.next', '.idea', 'dist', 'build', '.git'}
    
    for root, dirs, files in os.walk(directory_path):
        # Skip excluded directories by modifying dirs in-place
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
            
        for file in files:
            if file.endswith(('.js', '.jsx', '.ts', '.tsx')):
                js_ts_files.append(os.path.join(root, file))
    
    return js_ts_files


def extract_imports(file_path: str) -> Set[str]:
    """
    Extract import/require statements from a JavaScript or TypeScript file.

    Args:
        file_path: Path to the JS/TS file.

    Returns:
        A set of package names that are being imported.
    """
    imports = set()
    
    # Patterns for different types of imports
    # ES6 import patterns
    es6_patterns = [
        r'import\s+.*\s+from\s+[\'"]([^./][^\'"]*)(?:/[^\'"]*)??[\'"]',  # import x from 'package'
        r'import\s+[\'"]([^./][^\'"]*)(?:/[^\'"]*)??[\'"]',              # import 'package'
        r'export\s+.*\s+from\s+[\'"]([^./][^\'"]*)(?:/[^\'"]*)??[\'"]',  # export x from 'package'
    ]
    
    # CommonJS require pattern
    require_pattern = r'(?:const|let|var)\s+.*\s*=\s*require\s*\(\s*[\'"]([^./][^\'"]*)(?:/[^\'"]*)??[\'"]\s*\)'
    
    # Dynamic import pattern
    dynamic_import = r'import\s*\(\s*[\'"]([^./][^\'"]*)(?:/[^\'"]*)??[\'"]\s*\)'
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Check all ES6 import patterns
            for pattern in es6_patterns:
                for match in re.finditer(pattern, content):
                    imports.add(match.group(1))
            
            # Check CommonJS require pattern
            for match in re.finditer(require_pattern, content):
                imports.add(match.group(1))
                
            # Check dynamic import pattern
            for match in re.finditer(dynamic_import, content):
                imports.add(match.group(1))
                
    except Exception as e:
        print(f"Error reading {file_path}: {str(e)}")
    
    # Clean up package names (handle scoped packages and subpaths)
    clean_imports = set()
    for imp in imports:
        if imp.startswith('@'):
            # For scoped packages, capture the scope and the package name
            parts = imp.split('/')
            if len(parts) >= 2:
                clean_imports.add(f"{parts[0]}/{parts[1]}")
        else:
            # For regular packages, just capture the package name
            clean_imports.add(imp.split('/')[0])
    
    return clean_imports


def install_package(package_name: str, directory_path: str) -> Tuple[bool, str]:
    """
    Install a package with its latest version to the specific directory.

    Args:
        package_name: The name of the package to install.
        directory_path: The directory where the package should be installed.

    Returns:
        A tuple of (success, version) where success is a boolean indicating if the installation
        was successful, and version is the installed version string.
    """
    try:
        latest_version = get_latest_package_version(package_name)
        print(f"  Latest version of {package_name}: {latest_version}")
        
        # Get the current directory to return to it later
        original_dir = os.getcwd()
        
        try:
            # Change to the target directory before running npm
            os.chdir(directory_path)
            print(f"  Installing to directory: {directory_path}")
            
            # Construct the install command
            install_cmd = f"npm install {package_name}@{latest_version}"
            
            # Run the installation command
            subprocess.check_call(install_cmd, shell=True)
            
            print(f"  ✅ Installed {package_name}@{latest_version}")
            return True, latest_version
            
        finally:
            # Always change back to the original directory
            os.chdir(original_dir)
            
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Failed to install {package_name}: {str(e)}")
        return False, ""
    except Exception as e:
        print(f"  ❌ Error installing {package_name}: {str(e)}")
        return False, ""


def update_package_json(directory_path: str, installed_packages: Dict[str, str]) -> bool:
    """
    Update package.json to include the newly installed packages.

    Args:
        directory_path: Path to the directory containing package.json.
        installed_packages: Dictionary of package names and their versions.

    Returns:
        True if package.json was updated successfully, False otherwise.
    """
    if not installed_packages:
        return True
        
    package_json_path = os.path.join(directory_path, 'package.json')
    
    try:
        # Check if package.json exists
        if not os.path.isfile(package_json_path):
            print(f"package.json not found at {package_json_path}. Creating new file...")
            package_json = {
                "name": os.path.basename(directory_path),
                "version": "1.0.0",
                "description": "Project with detected dependencies",
                "dependencies": {},
                "devDependencies": {}
            }
        else:
            # Load existing package.json
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_json = json.load(f)
        
        # Ensure dependencies section exists
        if 'dependencies' not in package_json:
            package_json['dependencies'] = {}
        
        # Add all installed packages to dependencies
        for pkg_name, version in installed_packages.items():
            package_json['dependencies'][pkg_name] = f"^{version}"
        
        # Write updated package.json
        with open(package_json_path, 'w', encoding='utf-8') as f:
            json.dump(package_json, f, indent=2)
            f.write('\n')  # Add newline at end of file
        
        print(f"✅ Updated package.json with {len(installed_packages)} new dependencies")
        return True
        
    except Exception as e:
        print(f"❌ Error updating package.json: {str(e)}")
        return False


def check_and_install_missing_packages(directory_path: str) -> None:
    """
    Check for packages imported in JS/TS files that are not installed and install them.
    Also updates package.json with the newly installed packages.

    Args:
        directory_path: Path to the directory to scan.

    Raises:
        FileNotFoundError: If the directory is not found.
        Exception: For other errors during processing.
    """
    try:
        # Check if directory exists
        if not os.path.isdir(directory_path):
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        print(f"\nScanning for JavaScript and TypeScript files in: {directory_path}\n")

        # Find all JS/TS files
        js_ts_files = find_js_ts_files(directory_path)
        
        if not js_ts_files:
            print("No JavaScript or TypeScript files found in the directory.")
            return
            
        print(f"Found {len(js_ts_files)} JavaScript/TypeScript files to analyze.\n")
        
        # Get all installed packages
        installed_packages = get_installed_packages(directory_path)
        
        # Collect all imported packages from all files
        all_imports = set()
        
        for file_path in js_ts_files:
            # Get relative path for display
            rel_path = os.path.relpath(file_path, directory_path)
            print(f"Analyzing imports in {rel_path}")
            
            # Extract imports from this file
            file_imports = extract_imports(file_path)
            
            if file_imports:
                print(f"  Found {len(file_imports)} import(s): {', '.join(file_imports)}")
                all_imports.update(file_imports)
            else:
                print("  No imports found")
        
        # Find missing packages
        missing_packages = [pkg for pkg in all_imports if pkg not in installed_packages and pkg != '']
        
        if not missing_packages:
            print("\nAll imported packages are already installed!")
            return
        
        print(f"\nFound {len(missing_packages)} uninstalled package(s):")
        for pkg in missing_packages:
            print(f"  - {pkg}")
        
        # Confirm installation
        print("\nInstalling missing packages...")
        
        # Track successfully installed packages for package.json update
        successfully_installed = {}
        
        # Install all missing packages
        for package_name in missing_packages:
            try:
                print(f"Processing {package_name}...")
                # Pass directory_path to install_package
                success, version = install_package(package_name, directory_path)
                if success:
                    successfully_installed[package_name] = version
                else:
                    print(f"  Failed to install {package_name}")
            except Exception as e:
                print(f"  Error processing {package_name}: {str(e)}")
        
        # Update package.json with the newly installed packages
        if successfully_installed:
            update_package_json(directory_path, successfully_installed)
        
        print("\n----- SUMMARY -----")
        print(f"Scanned {len(js_ts_files)} JavaScript/TypeScript files")
        print(f"Found {len(all_imports)} unique package imports")
        print(f"Installed {len(successfully_installed)} out of {len(missing_packages)} missing package(s)")
        if successfully_installed:
            print(f"Added {len(successfully_installed)} packages to package.json")
        print("Installation complete!")

    except FileNotFoundError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"Error checking and installing packages: {str(e)}")
        sys.exit(1)


def main() -> None:
    """
    Main function to parse arguments and execute the scan and install.
    """
    if len(sys.argv) > 1:
        directory_path = os.path.abspath(sys.argv[1])
    else:
        print('Usage: npm_check_uninstalled_versions.py <path-to-directory>')
        print('If no path is provided, the current directory will be used.')
        directory_path = os.getcwd()
    print(directory_path)

    check_and_install_missing_packages(directory_path)


if __name__ == "__main__":
    main()