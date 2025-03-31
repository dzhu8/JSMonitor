#!/usr/bin/env python3
"""
Utility functions shared between npm tools.
"""

import json
import os
import urllib.request
import urllib.error
from typing import Dict, Set, List


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


def get_installed_packages(directory_path: str) -> Set[str]:
    """
    Get a set of packages that are currently installed in node_modules.

    Args:
        directory_path: Path to the project directory.

    Returns:
        A set of installed package names.
    """
    node_modules_path = os.path.join(directory_path, 'node_modules')
    
    # If node_modules doesn't exist, no packages are installed
    if not os.path.isdir(node_modules_path):
        return set()
    
    installed_packages = set()
    
    # Check for packages in node_modules
    for item in os.listdir(node_modules_path):
        # Skip hidden directories and scoped packages directory
        if item.startswith('.') or item.startswith('@'):
            continue
        
        package_path = os.path.join(node_modules_path, item)
        if os.path.isdir(package_path):
            installed_packages.add(item)
    
    # Handle scoped packages (e.g., @types/node)
    scoped_packages_path = [os.path.join(node_modules_path, item) 
                           for item in os.listdir(node_modules_path) 
                           if item.startswith('@') and os.path.isdir(os.path.join(node_modules_path, item))]
    
    for scope_path in scoped_packages_path:
        scope_name = os.path.basename(scope_path)
        for package in os.listdir(scope_path):
            package_path = os.path.join(scope_path, package)
            if os.path.isdir(package_path):
                installed_packages.add(f"{scope_name}/{package}")
    
    return installed_packages