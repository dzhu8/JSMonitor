# JSMonitor

Helpful tools for monitoring and managing JavaScript and TypeScript projects.

## Installation

To install JSMonitor, run:

```
pip install -e .
```

This will register the JSMonitor commands for use anywhere on your system. If using a virtual environment or conda environment to use the commands, make sure to activate the environment beforehand. Also make sure you
are in this directory before installing. 

## Available Commands

- `jsmonitor-updater` - Updates npm dependencies to their latest versions
- `jsmonitor-installer` - Checks for and installs missing packages including TypeScript type definitions
- `orange` - Formats and organizes JavaScript/TypeScript files using Prettier

All commands support the `--version` flag to check the installed version:

```bash
jsmonitor-updater --version
jsmonitor-installer --version
orange --version
```

## Using the Prettier Integration (orange)

The `orange` command uses Node.js and Prettier to format JavaScript and TypeScript files.

We recommend that `orange` be called from the outermost directory of the project (this will ensure uniform styling for all project files). Otherwise, prettier must be installed in any isolated directory it is applied to. 

Prettier will be installed automatically if it's not found when you run the command. Alternatively, you can run `npm install --save-dev prettier` manually.

### Python Usage

```
# Format files in the current directory
orange

# Format files in a specific directory
orange /path/to/js/files

# Check formatting without modifying files
orange --check

# Format only specific file extensions
orange --extensions .js,.ts

# Force installation/reinstallation of Prettier
orange --install

# Use a specific Prettier config file
orange --config /path/to/.prettierrc

# Use a specific ignore file
orange --ignore-path /path/to/.prettierignore

# Verbose output
orange -v
```

### JavaScript Alternative

You can also use the JavaScript version directly:

```
# Install dependencies
npm install

# Format files in the current directory
node orangeJS.js

# Format files with options
node orangeJS.js --check --verbose
```

### Prerequisites

- Node.js must be installed on your system
- For the Python version, the script uses `npx` to run Prettier
- For the JavaScript version, the script uses the Prettier library directly