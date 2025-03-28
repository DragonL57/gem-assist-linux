"""
Example plugin demonstrating the plugin architecture.
"""
from plugins import Plugin, tool, capability
import os
from typing import List, Dict, Any

class FileSystemPlugin(Plugin):
    """Plugin providing enhanced file system operations."""
    
    @classmethod
    def register(cls):
        """Register all tool methods from this plugin."""
        # The base implementation will automatically register
        # methods decorated with @tool, but we could do custom
        # registration here if needed
        pass
    
    @staticmethod
    @tool(
        categories=["filesystem", "search"],
        requires_filesystem=True,
        example_usage="find_files_by_type('.txt', '/home/user')"
    )
    def find_files_by_type(extension: str, directory: str = None) -> List[str]:
        """
        Find all files with the specified extension in the directory.
        
        Args:
            extension: File extension to search for (e.g., '.txt')
            directory: Directory to search in (default: current directory)
            
        Returns:
            List of file paths matching the extension
        """
        if directory is None:
            directory = os.getcwd()
            
        results = []
        
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(extension):
                    results.append(os.path.join(root, file))
                    
        return results
    
    @staticmethod
    @tool(
        categories=["filesystem", "metadata"],
        requires_filesystem=True
    )
    def get_directory_structure(directory: str = None, max_depth: int = 3) -> Dict[str, Any]:
        """
        Get a structured representation of a directory.
        
        Args:
            directory: Directory to analyze (default: current directory)
            max_depth: Maximum depth to traverse
            
        Returns:
            Dictionary representing the directory structure
        """
        if directory is None:
            directory = os.getcwd()
            
        def scan_dir(path, depth=0):
            if depth > max_depth:
                return "..."
                
            result = {}
            try:
                with os.scandir(path) as entries:
                    for entry in entries:
                        if entry.is_dir():
                            result[entry.name] = scan_dir(entry.path, depth + 1)
                        else:
                            result[entry.name] = os.path.getsize(entry.path)
            except PermissionError:
                return "Permission denied"
                
            return result
            
        return {os.path.basename(directory): scan_dir(directory)}
