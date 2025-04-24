#!/usr/bin/env python3
"""
JavaScript formatting tool - implements Black-like formatting and isort-like import sorting for JavaScript files.
Uses a regex-based approach to sort imports in JavaScript/JSX files.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

def extract_imports(js_code: str) -> Tuple[List[str], str]:
    """
    Extract import statements from JavaScript code using regex.
    
    Args:
        js_code: Raw JavaScript code string.
        
    Returns:
        imports: List of import statement strings.
        code_without_imports: The code with import statements removed.
    """
    # Match import statements
    import_pattern = re.compile(r'^import\s+.*?[\'"];?\s*$', re.MULTILINE)
    
    # Find all imports
    imports = import_pattern.findall(js_code)
    
    # Remove imports from code
    code_without_imports = import_pattern.sub('', js_code)
    
    return imports, code_without_imports

def get_import_path_depth(import_path: str) -> int:
    """
    Calculate the depth of an import path.
    
    Args:
        import_path: The import path string to analyze.
        
    Returns:
        depth: Integer representing the directory depth of the import path.
    """
    # Remove leading './' or '../'
    path = import_path.lstrip('./')
    
    # Count directory levels
    return path.count('/') + 1 if '/' in path else 0

def extract_source_from_import(import_stmt: str) -> str:
    """
    Extract the source path from an import statement.
    
    Args:
        import_stmt: An import statement string.
        
    Returns:
        source: The source path of the import.
    """
    match = re.search(r'[\'"]([^\'"]+)[\'"]', import_stmt)
    if not match:
        return ""
    return match.group(1)

def categorize_import(import_stmt: str) -> Tuple[int, str, str]:
    """
    Categorize an import statement for sorting.
    
    Args:
        import_stmt: An import statement string.
        
    Returns:
        category: Integer representing import category (0 for absolute, 1 for relative).
        source: The source path of the import.
        import_stmt: The original import statement.
    """
    # Extract source from import statement
    source = extract_source_from_import(import_stmt)
    if not source:
        # If unable to extract source, return as is
        return (999, "", import_stmt)
    
    # Categorize by source type
    category = 0 if not source.startswith('.') else 1
    
    # For relative imports, count directory levels
    if category == 1:
        depth = source.count('/') + (0 if source.startswith('./') else 2)
        category = 10 + depth
    
    return (category, source.lower(), import_stmt)

def sort_imports(imports: List[str]) -> List[str]:
    """
    Sort import declarations according to a specified priority order.
    
    Args:
        imports: List of import statement strings.
        
    Returns:
        result: Sorted list of import statement strings following these priorities:
            1. Outermost directory imports first (e.g., 'react', 'lodash')
            2. Then imports from same directory (e.g., './components')
            3. Within each source file, imports are sorted alphabetically
            4. Directory distance (closer directories first)
    """
    if not imports:
        return []
        
    # Categorize and sort imports
    categorized = [categorize_import(imp) for imp in imports]
    categorized.sort()  # Sort by category, then by source
    
    # Extract sorted import statements
    return [item[2] for item in categorized]

def format_import(import_stmt: str) -> str:
    """
    Format an import statement by cleaning up whitespace.
    
    Args:
        import_stmt: A JavaScript import statement string.
        
    Returns:
        cleaned: The formatted import statement.
    """
    # Clean up spaces in imports
    cleaned = re.sub(r'import\s+{', 'import {', import_stmt)
    cleaned = re.sub(r'{\s+', '{ ', cleaned)
    cleaned = re.sub(r'\s+}', ' }', cleaned)
    cleaned = re.sub(r',\s+', ', ', cleaned)
    return cleaned

def format_js_imports(js_code: str) -> str:
    """
    Format JavaScript code to apply consistent import sorting.
    
    Args:
        js_code: Raw JavaScript code string to be formatted.
        
    Returns:
        result: Formatted JavaScript code with properly sorted import statements.
    """
    try:
        # Extract import statements
        imports, code_without_imports = extract_imports(js_code)
        
        if not imports:
            return js_code  # No imports to sort
            
        # Sort imports
        sorted_imports = sort_imports(imports)
        
        # Format each import (clean up whitespace)
        formatted_imports = [format_import(imp) for imp in sorted_imports]
        
        # Join formatted imports and add them back to the code
        result = '\n'.join(formatted_imports) + '\n\n' + code_without_imports.lstrip()
        
        return result
        
    except Exception as e:
        print(f"Error formatting JavaScript: {e}")
        return js_code  # Return original code on error

def format_file(file_path: str, check_only: bool = False) -> bool:
    """
    Format imports in a JavaScript file.
    
    Args:
        file_path: Path to the JavaScript file to format.
        check_only: If True, only check if formatting is needed without modifying the file.
        
    Returns:
        success: Boolean indicating whether the operation was successful.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        formatted_content = format_js_imports(content)
        
        if content == formatted_content:
            print(f"✓ {file_path} imports are already sorted.")
            return True
        
        if check_only:
            print(f"✗ {file_path} imports need sorting.")
            return False
            
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(formatted_content)
            
        print(f"✓ Sorted imports in {file_path}")
        return True
        
    except Exception as e:
        print(f"Error formatting {file_path}: {e}")
        return False

def format_directory(directory: str, check_only: bool = False) -> bool:
    """
    Format imports in all JavaScript files in a directory recursively.
    
    Args:
        directory: Path to the directory containing JavaScript files to format.
        check_only: If True, only check if formatting is needed without modifying files.
        
    Returns:
        success: Boolean indicating whether all operations were successful.
    """
    success = True
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.js', '.jsx')):
                file_path = os.path.join(root, file)
                if not format_file(file_path, check_only):
                    success = False
                    
    return success

def main():
    """
    Main entry point for the JavaScript import formatter command-line tool.
    
    Parses command-line arguments and initiates formatting of JS files
    either individually or recursively through directories.
    
    Args:
        None: Arguments are parsed from sys.argv
        
    Returns:
        None: Exits with status code 0 on success, 1 on failure in check mode
    """
    parser = argparse.ArgumentParser(description='Format JavaScript import statements similar to isort for Python.')
    parser.add_argument('paths', nargs='+', help='Files or directories to format')
    parser.add_argument('--check', action='store_true', help='Check if imports are sorted without changing them')
    
    args = parser.parse_args()
    
    success = True
    for path in args.paths:
        if os.path.isdir(path):
            if not format_directory(path, args.check):
                success = False
        elif os.path.isfile(path):
            if not format_file(path, args.check):
                success = False
        else:
            print(f"Error: {path} is not a valid file or directory.")
            success = False
    
    if not success and args.check:
        sys.exit(1)

if __name__ == "__main__":
    main()
