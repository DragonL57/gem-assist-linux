"""
Example plugin demonstrating the plugin architecture with input validation.
"""
from plugins import Plugin, tool, capability, PluginError
import os
from typing import List, Dict, Any
import pathlib

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
        example_usage="find_files_by_type('.txt', '/home/user')",
        params={
            "extension": {
                "type": str,
                "required": True,
                "regex": r"^\.[a-zA-Z0-9]+$",
                "custom": {
                    "validator": lambda x: len(x) >= 2,
                    "message": "Extension must be at least 2 characters (including dot)"
                }
            },
            "directory": {
                "type": str,
                "required": False,
                "custom": {
                    "validator": lambda x: x is None or os.path.exists(x),
                    "message": "Directory must exist"
                }
            }
        }
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
        try:
            if directory is None:
                directory = os.getcwd()
                
            results = []
            
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith(extension):
                        results.append(os.path.join(root, file))
                        
            return results
            
        except Exception as e:
            raise PluginError(f"Error finding files by type: {e}", plugin_name=FileSystemPlugin.__name__) from e
    
    @staticmethod
    @tool(
        categories=["filesystem", "metadata"],
        requires_filesystem=True,
        params={
            "directory": {
                "type": str,
                "required": False, 
                "custom": {
                    "validator": lambda x: x is None or os.path.exists(x),
                    "message": "Directory must exist"
                }
            },
            "max_depth": {
                "type": int,
                "required": False,
                "range": {
                    "min": 1,
                    "max": 10
                }
            }
        }
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
        try:
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
                except Exception as e:
                    return f"Error: {str(e)}"
                    
                return result
                
            return {os.path.basename(directory): scan_dir(directory)}
            
        except Exception as e:
            raise PluginError(f"Error getting directory structure: {e}", plugin_name=FileSystemPlugin.__name__) from e
