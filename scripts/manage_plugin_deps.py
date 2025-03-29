#!/usr/bin/env python3
"""
Plugin dependency management script for gem-assist.
Helps install and manage plugin dependencies.
"""

import argparse
import os
import sys
from pathlib import Path
import subprocess

def get_plugin_requirements():
    """Get all plugin requirement files."""
    req_dir = Path(__file__).parent.parent / 'plugins' / 'requirements'
    return [f for f in req_dir.glob('*.txt') if f.name != 'base.txt']

def install_plugin_deps(plugin_name=None, upgrade=False):
    """Install dependencies for specific plugin or all plugins."""
    req_dir = Path(__file__).parent.parent / 'plugins' / 'requirements'
    
    if plugin_name:
        req_file = req_dir / f'{plugin_name}.txt'
        if not req_file.exists():
            print(f"Error: Requirements file not found for plugin: {plugin_name}")
            sys.exit(1)
        req_files = [req_file]
    else:
        req_files = get_plugin_requirements()
        
    for req_file in req_files:
        plugin = req_file.stem
        print(f"\nInstalling dependencies for {plugin}...")
        
        cmd = [sys.executable, '-m', 'pip', 'install', '-r', str(req_file)]
        if upgrade:
            cmd.append('--upgrade')
            
        try:
            subprocess.run(cmd, check=True)
            print(f"Successfully installed dependencies for {plugin}")
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies for {plugin}: {e}")
            if plugin_name:  # Exit if specific plugin install fails
                sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Manage gem-assist plugin dependencies')
    parser.add_argument('--plugin', help='Specific plugin to install dependencies for')
    parser.add_argument('--upgrade', action='store_true', 
                       help='Upgrade dependencies to latest versions')
    parser.add_argument('--list', action='store_true',
                       help='List available plugin requirement files')
    
    args = parser.parse_args()
    
    if args.list:
        print("\nAvailable plugin requirement files:")
        for req_file in get_plugin_requirements():
            print(f"- {req_file.stem}")
        return
        
    install_plugin_deps(args.plugin, args.upgrade)

if __name__ == '__main__':
    main()
