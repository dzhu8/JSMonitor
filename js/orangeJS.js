#!/usr/bin/env node

/**
 * JavaScript formatting tool using Prettier
 * This script formats JavaScript/TypeScript files in a specified directory
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const glob = require('glob');

// Check if prettier is available
function isPrettierInstalled() {
  try {
    require.resolve('prettier');
    return true;
  } catch (e) {
    return false;
  }
}

// Install prettier if not available
function installPrettier() {
  console.log('Prettier not found. Installing prettier...');
  try {
    execSync('npm install --save-dev prettier', { stdio: 'inherit' });
    console.log('Prettier installed successfully.');
    return true;
  } catch (error) {
    console.error('Failed to install prettier:', error.message);
    return false;
  }
}

/**
 * Format files using Prettier
 * 
 * @param {Object} options - Options for formatting
 * @param {string} options.directory - Directory containing files to format
 * @param {string[]} options.extensions - File extensions to format
 * @param {string} [options.config] - Path to prettier config file
 * @param {string} [options.ignorePath] - Path to .prettierignore file
 * @param {boolean} [options.checkOnly=false] - Only check if files are formatted
 * @param {boolean} [options.verbose=false] - Print verbose output
 * @returns {boolean} - Success status
 */
function formatWithPrettier(options) {
  const { 
    directory = '.', 
    extensions = ['.js', '.jsx', '.ts', '.tsx'],
    config,
    ignorePath,
    checkOnly = false,
    verbose = false
  } = options;
  
  if (!fs.existsSync(directory)) {
    console.error(`Directory not found: ${directory}`);
    return false;
  }
  
  // Ensure prettier is available
  if (!isPrettierInstalled()) {
    if (!installPrettier()) {
      return false;
    }
  }
    try {
    // Import prettier now that we know it's installed
    const prettier = require('prettier');
    
    // Find all matching files
    const extensionPattern = `**/*{${extensions.map(ext => ext.replace(/^\./, '')).join(',')}}`;
    const globOptions = { cwd: directory, absolute: true };
    
    // Check for default prettier config
    const defaultConfigPath = path.join(__dirname, '.prettierrc');
    const hasDefaultConfig = fs.existsSync(defaultConfigPath);
    
    if (verbose) {
      console.log(`Looking for files matching pattern: ${extensionPattern}`);
      if (hasDefaultConfig && !config) {
        console.log(`Using default prettier config from ${defaultConfigPath}`);
      }
    }
    
    // Get list of files
    const files = glob.sync(extensionPattern, globOptions);
    
    if (verbose) {
      console.log(`Found ${files.length} files to process`);
    }
    
    // Process each file
    let formatted = 0;
    let unformatted = 0;
    let errors = 0;
    
    for (const filePath of files) {
      try {
        if (verbose) {
          console.log(`Processing ${filePath}`);
        }
        
        const fileContent = fs.readFileSync(filePath, 'utf8');
          // Get prettier options - respect .prettierrc file if exists
        const defaultConfigPath = path.join(__dirname, '.prettierrc');
        const hasDefaultConfig = fs.existsSync(defaultConfigPath);

        const options = {
          // Use provided config path, or default config path if it exists
          ...(config ? { configPath: config } : (hasDefaultConfig ? { configPath: defaultConfigPath } : {})),
          ...(ignorePath ? { ignorePath } : {}),
          filepath: filePath
        };
        
        // Check if file formatting is needed
        const isFormatted = prettier.check(fileContent, options);
        
        if (!isFormatted) {
          if (checkOnly) {
            console.log(`${filePath} needs formatting`);
            unformatted++;
          } else {
            // Format the file
            const formattedContent = prettier.format(fileContent, options);
            fs.writeFileSync(filePath, formattedContent, 'utf8');
            console.log(`${filePath} formatted successfully`);
            formatted++;
          }
        } else if (verbose) {
          console.log(`${filePath} already properly formatted`);
        }
      } catch (error) {
        console.error(`Error processing ${filePath}: ${error.message}`);
        errors++;
      }
    }
    
    // Summary
    if (checkOnly) {
      console.log(`\nCheck complete: ${files.length} files checked, ${unformatted} need formatting, ${errors} errors`);
      return unformatted === 0 && errors === 0;
    } else {
      console.log(`\nFormatting complete: ${files.length} files processed, ${formatted} formatted, ${errors} errors`);
      return errors === 0;
    }
    
  } catch (error) {
    console.error(`Error: ${error.message}`);
    return false;
  }
}

// Version info
const VERSION = '0.2.0';

// Process command line args
function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    directory: '.',
    extensions: ['.js', '.jsx', '.ts', '.tsx'],
    checkOnly: false,
    verbose: false
  };
  
  // Print version and exit if requested
  if (args.includes('--version') || args.includes('-V')) {
    console.log(`orangeJS v${VERSION}`);
    process.exit(0);
  }
  
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    
    if (arg === '--check') {
      options.checkOnly = true;
    } else if (arg === '--verbose' || arg === '-v') {
      options.verbose = true;
    } else if (arg === '--config' && i + 1 < args.length) {
      options.config = args[++i];
    } else if (arg === '--ignore-path' && i + 1 < args.length) {
      options.ignorePath = args[++i];
    } else if (arg === '--extensions' && i + 1 < args.length) {
      options.extensions = args[++i].split(',')
        .map(ext => ext.trim())
        .map(ext => ext.startsWith('.') ? ext : `.${ext}`);
    } else if (!arg.startsWith('--')) {
      options.directory = arg;
    }
  }
  
  return options;
}

// Main execution
if (require.main === module) {
  const options = parseArgs();
  const success = formatWithPrettier(options);
  process.exit(success ? 0 : 1);
}

module.exports = {
  formatWithPrettier
};
