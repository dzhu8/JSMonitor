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
from .utils import get_latest_package_version, get_installed_packages, check_types_package_exists


def find_js_ts_files(directory_path: str) -> List[str]:
    """
    Find all JavaScript and TypeScript files in a directory recursively.

    Args:
        directory_path: The root directory to search in.

    Returns:
        js_ts_files: A list of file paths to .js, .jsx, .ts, and .tsx files.
    """
    js_ts_files = []
    # Directories to skip
    excluded_dirs = {'node_modules', '.next', '.idea', 'dist', 'build', '.git', 'components', 'src/components'}
    
    for root, dirs, files in os.walk(directory_path):
        # Skip excluded directories by modifying dirs in-place
        dirs[:] = [d for d in dirs if d not in excluded_dirs and not os.path.join(root, d).endswith('src/components')]
            
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
        clean_imports: Set of package names that are being imported.
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
            # Only consider standard scoped packages (like @types/node, @babel/core)
            # Skip imports starting with @ that are likely path aliases
            parts = imp.split('/')
            if len(parts) >= 2:
                # List of common npm scoped packages prefixes to include
                known_scopes = {'@types', '@babel', '@angular', '@vue', '@react', '@mui', '@material', 
                               '@testing-library', '@storybook', '@emotion', '@jest', '@aws', 
                               '@microsoft', '@apollo', '@nestjs', '@sentry', '@chakra-ui', '@next',
                               '@prisma', '@stripe', '@tanstack', '@reduxjs', '@fortawesome'}
                
                if parts[0] in known_scopes:
                    clean_imports.add(f"{parts[0]}/{parts[1]}")
                else:
                    # Skip other @ imports as they're likely path aliases configured in tsconfig/jsconfig
                    print(f"  Skipping likely path alias: {imp}")
        else:
            # For regular packages, just capture the package name
            clean_imports.add(imp.split('/')[0])
    
    return clean_imports


def install_package(package_name: str, directory_path: str, is_dev_dependency: bool = False) -> Tuple[bool, str]:
    """
    Install a package with its latest version to the specific directory.

    Args:
        package_name: The name of the package to install.
        directory_path: The directory where the package should be installed.
        is_dev_dependency: Whether to install as a dev dependency.

    Returns:
        A tuple `(success, version)` where `success` is a boolean indicating if the
        installation was successful, and `version` is the installed version string.
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
            install_flag = "--save-dev" if is_dev_dependency else ""
            install_cmd = f"npm install {package_name}@{latest_version} {install_flag}"
            
            # Run the installation command
            subprocess.check_call(install_cmd, shell=True)
            
            print(f"  ✅ Installed {package_name}@{latest_version} {'as dev dependency' if is_dev_dependency else ''}")
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


def update_package_json(directory_path: str, installed_packages: Dict[str, str], dev_dependencies: Dict[str, str] = None) -> bool:
    """
    Update package.json to include the newly installed packages.

    Args:
        directory_path: Path to the directory containing package.json.
        installed_packages: Dictionary of package names and their versions for dependencies.
        dev_dependencies: Dictionary of package names and their versions for devDependencies.

    Returns:
        True if package.json was updated successfully, False otherwise.
    """
    if not installed_packages and not dev_dependencies:
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
            
        # Ensure devDependencies section exists
        if 'devDependencies' not in package_json:
            package_json['devDependencies'] = {}
        
        # Add all installed packages to dependencies
        if installed_packages:
            for pkg_name, version in installed_packages.items():
                package_json['dependencies'][pkg_name] = f"^{version}"
        
        # Add all dev dependencies
        if dev_dependencies:
            for pkg_name, version in dev_dependencies.items():
                package_json['devDependencies'][pkg_name] = f"^{version}"
        
        # Write updated package.json
        with open(package_json_path, 'w', encoding='utf-8') as f:
            json.dump(package_json, f, indent=2)
            f.write('\n')  # Add newline at end of file
        
        summary = []
        if installed_packages:
            summary.append(f"{len(installed_packages)} new dependencies")
        if dev_dependencies:
            summary.append(f"{len(dev_dependencies)} new devDependencies")
            
        print(f"✅ Updated package.json with {' and '.join(summary)}")
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

    Returns:
        None: Prints progress to stdout and may exit the process on error.
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
        else:
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
        
        # Check for TypeScript types packages regardless of whether regular packages were installed
        has_typescript_files = any(file.endswith(('.ts', '.tsx')) for file in js_ts_files)
        
        if has_typescript_files:
            # Get all installed types packages
            successfully_installed_types = check_and_install_types_packages(directory_path, all_imports)
            
            # Update package.json with any installed types packages
            if successfully_installed_types:
                update_package_json(directory_path, {}, successfully_installed_types)
        
        print("\n----- SUMMARY -----")
        print(f"Scanned {len(js_ts_files)} JavaScript/TypeScript files")
        print(f"Found {len(all_imports)} unique package imports")
        
        # Only if we had missing packages to install
        if missing_packages:
            print(f"Installed {len(successfully_installed)} out of {len(missing_packages)} missing package(s)")
            if successfully_installed:
                print(f"Added {len(successfully_installed)} packages to package.json dependencies")
                
        # Only if we installed types packages
        if has_typescript_files and successfully_installed_types:
            print(f"Installed {len(successfully_installed_types)} TypeScript type definition packages as devDependencies")
            
        print("Installation complete!")

    except FileNotFoundError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"Error checking and installing packages: {str(e)}")
        sys.exit(1)


def check_and_install_types_packages(directory_path: str, import_packages: Set[str]) -> Dict[str, str]:
    """
    Check for missing @types packages and install them as dev dependencies.
    
    Args:
        directory_path: Path to the directory to scan.
        import_packages: Set of package names that are imported in the code.
        
    Returns:
        successfully_installed: Dictionary of successfully installed @types packages and their versions.
    """
    # Get all installed packages
    installed_packages = get_installed_packages(directory_path)
    
    # Filter packages to only include those that might need @types
    # Skip packages that are already @types packages
    potential_types_packages = {pkg for pkg in import_packages 
                               if not pkg.startswith('@types/') and not pkg.startswith('@') and pkg != ''}
    
    # Check which packages have @types versions available
    missing_types_packages = []
    
    print("\nChecking for available TypeScript type definitions (@types packages)...")
    
    for package_name in potential_types_packages:
        types_package = f"@types/{package_name}"
        
        # Skip if types package is already installed
        if types_package in installed_packages:
            print(f"  {types_package} is already installed")
            continue
        
        # Check if types package exists in npm registry
        if check_types_package_exists(package_name):
            missing_types_packages.append(types_package)
            print(f"  Found available type definitions: {types_package}")
    
    if not missing_types_packages:
        print("No missing @types packages found.")
        return {}
    
    print(f"\nFound {len(missing_types_packages)} missing @types packages:")
    for pkg in missing_types_packages:
        print(f"  - {pkg}")
    
    print("\nInstalling @types packages as dev dependencies...")
    
    # Track successfully installed packages for package.json update
    successfully_installed = {}
    
    # Install all missing @types packages
    for package_name in missing_types_packages:
        try:
            print(f"Processing {package_name}...")
            # Install as a dev dependency
            success, version = install_package(package_name, directory_path, is_dev_dependency=True)
            if success:
                successfully_installed[package_name] = version
            else:
                print(f"  Failed to install {package_name}")
        except Exception as e:
            print(f"  Error processing {package_name}: {str(e)}")
    
    return successfully_installed


def main() -> None:
    """
    Main function to parse arguments and execute the scan and install.
    """
    # Add support for --version flag
    if len(sys.argv) > 1 and sys.argv[1] in ['--version', '-v']:
        print("jsmonitor-installer v0.2.0")
        sys.exit(0)
        
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        directory_path = os.path.abspath(sys.argv[1])
    else:
        print('Usage: jsmonitor-installer [--version] <path-to-directory>')
        print('If no path is provided, the current directory will be used.')
        directory_path = os.getcwd()

    check_and_install_missing_packages(directory_path)


if __name__ == "__main__":
    main()