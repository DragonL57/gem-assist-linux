#!/usr/bin/env python3
"""
Utility script to upgrade deprecated dependencies to recommended alternatives.
"""

import os
import sys
import subprocess
from typing import List, Tuple
import pkg_resources

def check_installed_packages() -> List[Tuple[str, str]]:
    """Check for installed packages that should be upgraded."""
    packages_to_upgrade = []
    
    # List of packages to check with their recommended alternatives
    check_packages = [
        ("PyPDF2", "pypdf", "PyPDF2 is deprecated. Please use pypdf instead."),
        # Add other packages to check in the future
    ]
    
    installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
    
    for old_pkg, new_pkg, message in check_packages:
        if old_pkg.lower() in installed_packages:
            packages_to_upgrade.append((old_pkg, new_pkg, message))
    
    return packages_to_upgrade

def upgrade_packages(packages: List[Tuple[str, str, str]], use_uv: bool = True) -> None:
    """Upgrade packages to their recommended alternatives."""
    if not packages:
        print("No packages need upgrading.")
        return
    
    print("The following packages should be upgraded:")
    for old_pkg, new_pkg, message in packages:
        print(f"- {old_pkg} → {new_pkg}: {message}")
    
    # Ask for confirmation
    response = input("\nDo you want to upgrade these packages? (y/n): ")
    if response.lower() != "y":
        print("Upgrade canceled.")
        return
    
    # Upgrade each package
    for old_pkg, new_pkg, _ in packages:
        print(f"\nUpgrading {old_pkg} to {new_pkg}...")
        
        try:
            # Uninstall old package
            if use_uv:
                subprocess.check_call([sys.executable, "-m", "uv", "pip", "uninstall", "-y", old_pkg])
            else:
                subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", old_pkg])
            
            # Install new package
            if use_uv:
                subprocess.check_call([sys.executable, "-m", "uv", "pip", "install", new_pkg])
            else:
                subprocess.check_call([sys.executable, "-m", "pip", "install", new_pkg])
                
            print(f"Successfully upgraded {old_pkg} to {new_pkg}")
        except subprocess.CalledProcessError as e:
            print(f"Error upgrading {old_pkg} to {new_pkg}: {e}")

def update_code_references() -> None:
    """Update code references in the project files."""
    # Update imports in Python files
    replacements = [
        ("import pypdf", "import pypdf"),
        ("from pypdf import", "from pypdf import"),
        # Add more replacements as needed
    ]
    
    # Walk through the project directory
    processed_files = 0
    updated_files = 0
    
    for root, _, files in os.walk(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                processed_files += 1
                
                # Read the file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Apply replacements
                updated_content = content
                for old, new in replacements:
                    updated_content = updated_content.replace(old, new)
                
                # If changes were made, write back to the file
                if updated_content != content:
                    updated_files += 1
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)
    
    print(f"\nProcessed {processed_files} Python files, updated {updated_files} files with new import references.")

def main() -> None:
    """Main function to run the upgrade process."""
    print("Checking for deprecated packages...")
    packages_to_upgrade = check_installed_packages()
    
    if packages_to_upgrade:
        # Use uv by default if available
        use_uv = True
        try:
            subprocess.check_call([sys.executable, "-m", "uv", "--version"], 
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, FileNotFoundError):
            use_uv = False
            print("Note: uv package manager not found, falling back to pip.")
        
        # Upgrade the packages
        upgrade_packages(packages_to_upgrade, use_uv)
        
        # Update code references
        response = input("\nDo you want to update code references in the project? (y/n): ")
        if response.lower() == "y":
            update_code_references()
    else:
        print("No deprecated packages found.")

if __name__ == "__main__":
    main()
