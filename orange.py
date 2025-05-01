#!/usr/bin/env python3
"""
JavaScript formatting tool - implements Black-like formatting and isort-like import sorting for JavaScript files.
Uses a regex-based approach to sort imports in JavaScript/JSX files.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

def format_with_prettier(
    directory: Union[str, Path],
    file_extensions: List[str] = [".js", ".jsx", ".ts", ".tsx"],
    prettier_config: Optional[str] = None,
    ignore_path: Optional[str] = None,
    check_only: bool = False,
    verbose: bool = False,
    auto_install: bool = True,
) -> Tuple[bool, str]:
    """
    Format JavaScript/TypeScript files in a directory using Prettier.
    
    Args:
        directory: Directory containing files to format
        file_extensions: List of file extensions to format
        prettier_config: Path to prettier config file (optional)
        ignore_path: Path to .prettierignore file (optional)
        check_only: Only check if files are formatted (don't format them)
        verbose: Print verbose output
        auto_install: Automatically install Prettier if not found
        
    Returns:
        Tuple of (success, message)
    """
    try:
        if not Path(directory).exists():
            return False, f"Directory not found: {directory}"
            
        # Check if prettier is installed
        try:
            subprocess.run(
                ["npx", "--no-install", "prettier", "--version"],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError:
            if auto_install:
                # Try to install prettier automatically
                print("Checking for Prettier install...")
                if not ensure_prettier_installed(directory, verbose):
                    return False, "Failed to automatically install Prettier. Please run 'npm install --save-dev prettier' first."
            else:
                return False, "Prettier is not installed. Run 'npm install --save-dev prettier' first."
        
        # Build pattern for file extensions
        pattern = f"**/*{{{','.join([ext.lstrip('.') for ext in file_extensions])}}}"        # Build command
        cmd = ["npx", "prettier"]
        
        if check_only:
            cmd.append("--check")
        else:
            cmd.append("--write")
        
        # Check for default prettier config
        default_config = Path(__file__).parent / ".prettierrc"
        has_default_config = default_config.exists()
            
        if prettier_config:
            cmd.extend(["--config", prettier_config])
        elif has_default_config:
            cmd.extend(["--config", str(default_config)])
            if verbose:
                print(f"Using default prettier config: {default_config}")
            
        if ignore_path:
            cmd.extend(["--ignore-path", ignore_path])
            
        # Add the pattern to find files
        cmd.append(pattern)
        
        if verbose:
            print(f"Running: {' '.join(cmd)}")
          # Execute the command in the specified directory
        result = subprocess.run(
            cmd,
            cwd=str(directory),
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            if check_only:
                return True, "All files are formatted correctly."
            else:
                return True, f"Formatting completed successfully.\n{result.stdout}"
        else:
            if check_only:
                # Extract file names that need formatting from stderr
                files_needing_format = []
                
                if result.stderr:
                    for line in result.stderr.splitlines():
                        if line.startswith('[warn]') and not 'Code style issues found in' in line:
                            # Extract the filename (remove the [warn] prefix)
                            filename = line.replace('[warn]', '').strip()
                            if filename:
                                files_needing_format.append(filename)
                
                if files_needing_format:
                    files_msg = '\n'.join(f"  - {file}" for file in files_needing_format)
                    return False, f"The following files need formatting:\n{files_msg}"
                else:
                    return False, f"Some files need formatting."
            else:
                return False, f"Formatting failed:\n{result.stderr}"
                
    except Exception as e:
        return False, f"Error: {str(e)}"


def ensure_prettier_installed(directory: Union[str, Path], verbose: bool = False) -> bool:
    """
    Ensure Prettier is installed in the specified directory.
    If not present, attempts to install it locally.
    
    Args:
        directory: Directory to install prettier in
        verbose: Print verbose output
        
    Returns:
        True if prettier is installed or was successfully installed, False otherwise
    """
    try:
        # Check if prettier is already installed
        result = subprocess.run(
            ["npx", "--no-install", "prettier", "--version"],
            cwd=str(directory),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            if verbose:
                print(f"Prettier version {result.stdout.strip()} is already installed.")
            return True
            
    except Exception:
        # Prettier is not installed, try to install it
        pass
        
    print("Prettier not found. Installing prettier...")
    
    try:
        # Check if package.json exists, create if it doesn't
        package_json = Path(directory) / "package.json"
        if not package_json.exists():
            if verbose:
                print("package.json not found, creating it...")
            subprocess.run(
                ["npm", "init", "-y"],
                cwd=str(directory),
                capture_output=not verbose,
                text=True
            )
            
        # Install prettier as a dev dependency
        install_cmd = ["npm", "install", "--save-dev", "prettier"]
        if verbose:
            print(f"Running: {' '.join(install_cmd)}")
            
        result = subprocess.run(
            install_cmd,
            cwd=str(directory),
            capture_output=not verbose,
            text=True
        )
        
        if result.returncode == 0:
            print("Prettier installed successfully.")
            return True
        else:
            print(f"Failed to install Prettier: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error installing Prettier: {str(e)}")
        return False


def main():
    """Main function to handle command line arguments and execute formatting."""
    parser = argparse.ArgumentParser(
        description="Format and organize JavaScript/TypeScript files using Prettier"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="orange v0.2.0",
        help="Show the version number and exit"
    )
    
    parser.add_argument(
        "directory", 
        nargs="?", 
        default=".", 
        help="Directory containing JavaScript/TypeScript files (default: current directory)"
    )
    
    parser.add_argument(
        "--check", 
        action="store_true", 
        help="Check if files are formatted without modifying them"
    )
    
    parser.add_argument(
        "--extensions", 
        type=str, 
        default=".js,.jsx,.ts,.tsx", 
        help="Comma-separated list of file extensions to format (default: .js,.jsx,.ts,.tsx)"
    )
    
    parser.add_argument(
        "--config", 
        type=str,
        help="Path to Prettier config file"
    )
    
    parser.add_argument(
        "--ignore-path", 
        type=str,
        help="Path to .prettierignore file"
    )

    parser.add_argument(
        "--install", 
        action="store_true",
        help="Force installation of Prettier (Prettier is installed automatically if needed)"
    )
    
    parser.add_argument(
        "-v", 
        "--verbose", 
        action="store_true",
        help="Print verbose output"
    )
    
    args = parser.parse_args()
    
    # Convert directory to Path
    directory = Path(args.directory).resolve()
    
    # Parse extensions
    extensions = [ext.strip() for ext in args.extensions.split(",")]
    extensions = [ext if ext.startswith(".") else f".{ext}" for ext in extensions]
    
    if args.verbose:
        print(f"Processing directory: {directory}")
        print(f"File extensions: {extensions}")
      # Check if prettier is installed, install it if missing or if explicitly requested
    prettier_installed = True
    
    try:
        # Try to check prettier version first
        result = subprocess.run(
            ["npx", "--no-install", "prettier", "--version"],
            cwd=str(directory),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            prettier_installed = False
    except Exception:
        prettier_installed = False
    
    # Install prettier if it's not installed or if explicitly requested
    if not prettier_installed or args.install:
        print("Prettier not found or installation explicitly requested.")
        if not ensure_prettier_installed(directory, args.verbose):
            sys.exit(1)
      # Format files with Prettier
    success, message = format_with_prettier(
        directory=directory,
        file_extensions=extensions,
        prettier_config=args.config,
        ignore_path=args.ignore_path,
        check_only=args.check,
        verbose=args.verbose,
        auto_install=True  # Always attempt to auto-install if needed
    )
    
    print(message)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()


