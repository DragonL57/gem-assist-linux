"""
This script helps clean up after migrating from utility.py to the utils module.
"""

import os
import shutil

def backup_original_utility():
    """Create a backup of the original utility.py file"""
    if os.path.exists("utility.py"):
        if not os.path.exists("backups"):
            os.makedirs("backups")
        shutil.copy2("utility.py", "backups/utility.py.bak")
        print(f"Backed up utility.py to backups/utility.py.bak")
    else:
        print("No utility.py file found to backup.")

def create_utility_redirect():
    """Create a redirection file that imports from the utils module"""
    content = """
# This file is a compatibility layer for code still importing from utility.py
# It imports and re-exports all functions from the utils module
# Please update your imports to use the utils module directly

from utils import *

# Provide a warning
import warnings
warnings.warn(
    "Importing from utility.py is deprecated. Please import from the utils module directly.",
    DeprecationWarning, 
    stacklevel=2
)
"""
    with open("utility.py", "w") as f:
        f.write(content.strip())
    print("Created utility.py redirection file")

def main():
    """Main function to run the cleanup tasks"""
    print("Starting cleanup process...")
    backup_original_utility()
    create_utility_redirect()
    print("Cleanup completed.")
    print("\nNOTE: You should update all imports from 'utility' to 'utils' in your codebase.")
    print("The redirection file is provided for compatibility but is not recommended for long-term use.")

if __name__ == "__main__":
    main()
