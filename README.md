# JSMonitor

Helpful tools for monitoring and managing JavaScript and TypeScript projects.

## Installation

To install JSMonitor:

If the JSMonitor folder has been copied/exists on the computer, navigate to that folder and run: 

```
pip install -e .
```

If not and installing from Python, {coming soon}.

This will register the JSMonitor commands for use anywhere on your system. If using a virtual environment or conda environment to use the commands, make sure to activate the environment beforehand. Also make sure you
are in this directory before installing. 

## Available Commands

- `jsmonitor-updater` - Updates npm dependencies to their latest versions
- `jsmonitor-installer` - Checks for and installs missing packages including TypeScript type definitions
- `orange` - Formats and organizes JavaScript/TypeScript files using Prettier
- `format-imports` - Formats import statements in JS/TS files based on `tsconfig.json` or `jsconfig.json` path aliases.
 - `image-import-check` - Verifies that imported visual assets (images, `.css`, `.svg`, etc.) referenced from source files actually exist.

All commands support the `--version` flag to check the installed version:

```bash
jsmonitor-updater --version
jsmonitor-installer --version
orange --version
format-imports --version
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

# Use a specific Prettier config file (if not given, the default config will be used- this can be found https://github.com/dzhu8/JSMonitor/blob/main/.prettierrc)
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

## Using the Import Formatter (`format-imports`)

The `jsmonitor-format-imports` command helps to standardize import paths in your JavaScript, TypeScript, JSX, TSX, and Vue files. It reads path aliases defined in `compilerOptions.paths` (along with `compilerOptions.baseUrl`) from a `tsconfig.json` or `jsconfig.json` file in your project and updates relative import statements to use these aliases where applicable.

This is particularly useful for cleaning up long relative paths like `../../../../components/Button` to shorter, more manageable aliased paths like `@/components/Button`.

### Command Usage

```bash
# Format imports in the current directory (looks for tsconfig.json or jsconfig.json)
format-imports

# Format imports in a specific project directory
format-imports /path/to/your/project
```

### How it Works

1.  **Configuration Discovery**: The script searches for `tsconfig.json` in the target directory. If not found, it looks for `jsconfig.json`.
2.  **Path Alias Parsing**: It extracts `compilerOptions.baseUrl` and `compilerOptions.paths` to understand your project's module alias configuration. Only alias patterns ending with `/*` (e.g., `"@/*": ["./src/*"]`) are currently supported.
3.  **File Scanning**: It scans for `.js`, `.ts`, `.jsx`, `.tsx`, and `.vue` files within the target directory (and its subdirectories), excluding `node_modules` and `.git`.
4.  **Import Transformation**: For each eligible file, it parses import and export statements. If an import path can be shortened or standardized using a defined alias, the script rewrites that path.
    *   It prioritizes the alias that corresponds to the longest (most specific) target path. For example, if `abs_imported_item_path` is `/project/src/components/ui/Button.ts`, and aliases are `{"@/": ["./src/*"], "@components/": ["./src/components/*"]}`, it would prefer `@components/ui/Button` over `@/components/ui/Button`.
    *   If multiple aliases result in the same specificity of match, the one producing the shorter final aliased path is chosen.
5.  **File Update**: Files are only modified if changes to import paths are made.

### Prerequisites

- A `tsconfig.json` or `jsconfig.json` file with `compilerOptions.baseUrl` and `compilerOptions.paths` configured in the project directory where you intend to run the command.


## Using the Visual Import Checker (`image-import-check`)

The `image-import-check` command scans your source files (TypeScript, JavaScript, JSX, TSX) for import statements that reference visual assets (for example `.css`, `.png`, `.jpg`, `.svg`, `.webp`) and verifies that the referenced files exist. It prints the file and line number for any missing imports and exits with a non-zero status when missing files are found.

### Command Usage

```bash
# Check the current directory
image-import-check

# Check a specific directory
image-import-check /path/to/project
```

### Options

- `-v`, `--verbose`: Print verbose output
- `--ignore <substring>`: Skip files whose path contains this substring (can be provided multiple times)
- `--ignore-regex <regex>`: Skip files whose path matches this regex (can be provided multiple times)

### Behavior

- Scans files with these extensions: `.ts`, `.tsx`, `.js`, `.jsx`.
- By default ignores `node_modules` and `dist` directories; additional ignore rules may be supplied via `--ignore` or `--ignore-regex`.
- Runs checks in parallel and shows a simple progress indicator.

### Example: run with ignores

```bash
image-import-check /path/to/project --ignore node_modules --ignore dist --ignore-regex "^/path/to/project/generated/"
```

### Exit codes

- `0`: All referenced CSS files were found.
- `1`: Missing CSS import(s) were detected.
- `2`: Directory not found or invalid arguments.

### Prerequisites

- Python 3.6+ (the script uses standard library modules and runs as a console tool)
- Run the command from the project root (or supply the project directory as the first positional argument)
