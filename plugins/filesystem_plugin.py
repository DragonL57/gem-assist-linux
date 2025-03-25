"""
Filesystem plugin providing file and directory operations.
"""
import os
import shutil
import stat
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from plugins import Plugin, tool, capability
from core_utils import tool_message_print, tool_report_print

class FileSystemPlugin(Plugin):
    """Plugin providing file system operations."""
    
    @staticmethod
    @tool(
        categories=["filesystem", "navigation"],
        requires_filesystem=True
    )
    def list_dir(path: str = None) -> List[Dict[str, Any]]:
        """
        List files and directories in the specified path.
        
        Args:
            path: Directory path to list (default: current directory)
            
        Returns:
            List of dictionaries containing file information
        """
        
        if path is None:
            path = os.getcwd()
            
        tool_message_print(f"Listing directory: {path}")
        
        try:
            # Get all entries in the directory
            entries = os.listdir(path)
            results = []
            
            for entry in entries:
                full_path = os.path.join(path, entry)
                try:
                    stats = os.stat(full_path)
                    is_dir = os.path.isdir(full_path)
                    
                    # Format the file size
                    if is_dir:
                        size_str = "<DIR>"
                    else:
                        size = stats.st_size
                        if size < 1024:
                            size_str = f"{size} B"
                        elif size < 1024 * 1024:
                            size_str = f"{size / 1024:.1f} KB"
                        elif size < 1024 * 1024 * 1024:
                            size_str = f"{size / (1024 * 1024):.1f} MB"
                        else:
                            size_str = f"{size / (1024 * 1024 * 1024):.1f} GB"
                    
                    # Format the modification time
                    mod_time = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    
                    results.append({
                        "name": entry,
                        "is_dir": is_dir,
                        "size": size_str,
                        "size_bytes": stats.st_size,
                        "modified": mod_time,
                        "permissions": stat.filemode(stats.st_mode)
                    })
                    
                except Exception as e:
                    results.append({
                        "name": entry,
                        "error": str(e)
                    })
                    
            # Sort by directories first, then by name
            results.sort(key=lambda x: (not x.get("is_dir", False), x["name"].lower()))
            return results
            
        except Exception as e:
            return [{"error": str(e)}]
    
    @staticmethod
    @tool(
        categories=["filesystem", "metadata"],
        requires_filesystem=True
    )
    def get_drives() -> List[Dict[str, Any]]:
        """
        Get available drives on the system.
        
        Returns:
            List of dictionaries containing drive information
        """
        tool_message_print("Getting system drives")
        
        import psutil
        
        partitions = psutil.disk_partitions(all=False)
        results = []
        
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                
                # Calculate percentages and format sizes
                total_gb = usage.total / (1024 * 1024 * 1024)
                used_gb = usage.used / (1024 * 1024 * 1024)
                free_gb = usage.free / (1024 * 1024 * 1024)
                
                results.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "filesystem": partition.fstype,
                    "total_gb": round(total_gb, 2),
                    "used_gb": round(used_gb, 2),
                    "free_gb": round(free_gb, 2),
                    "percent_used": usage.percent
                })
            except Exception as e:
                results.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "filesystem": partition.fstype,
                    "error": str(e)
                })
                
        return results

    # Continue implementing other filesystem tools...
    @staticmethod
    @tool(
        categories=["filesystem", "metadata"],
        requires_filesystem=True
    )
    def get_file_metadata(filepath: str) -> Dict[str, Any]:
        """
        Get detailed metadata for a file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Dictionary containing file metadata
        """
        tool_message_print(f"Getting metadata for: {filepath}")
        
        try:
            stats = os.stat(filepath)
            is_dir = os.path.isdir(filepath)
            
            result = {
                "name": os.path.basename(filepath),
                "path": os.path.abspath(filepath),
                "size_bytes": stats.st_size,
                "is_directory": is_dir,
                "created": datetime.fromtimestamp(stats.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                "modified": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "accessed": datetime.fromtimestamp(stats.st_atime).strftime("%Y-%m-%d %H:%M:%S"),
                "permissions": stat.filemode(stats.st_mode),
                "exists": os.path.exists(filepath)
            }
            
            # Add file extension if it's a file
            if not is_dir:
                _, ext = os.path.splitext(filepath)
                result["extension"] = ext
                
                # Try to detect file type for common formats
                if ext.lower() in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml']:
                    result["type"] = "text"
                elif ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
                    result["type"] = "image"
                elif ext.lower() in ['.mp3', '.wav', '.ogg', '.flac']:
                    result["type"] = "audio"
                elif ext.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
                    result["type"] = "video"
                elif ext.lower() in ['.pdf', '.docx', '.xlsx', '.pptx']:
                    result["type"] = "document"
                else:
                    result["type"] = "unknown"
                
            return result
            
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    @tool(
        categories=["filesystem", "io"],
        requires_filesystem=True,
        example_usage="read_file('path/to/file.txt', auto_detect_type=True)"
    )
    def read_file(filepath: str, auto_detect_type: bool = True, force_text_mode: bool = False) -> str:
        """
        Unified file reading tool that handles both plain text and complex document types.
        
        Args:
            filepath: Path to the file
            auto_detect_type: When True, automatically detect and process file based on extension
            force_text_mode: When True, attempt to read any file as plain text regardless of type
            
        Returns:
            File content as a string
        """
        tool_message_print(f"Reading file: {filepath}")
        
        # Check if file exists
        if not os.path.exists(filepath):
            return f"Error: File not found: {filepath}"
            
        # Check if it's a regular file
        if not os.path.isfile(filepath):
            return f"Error: Not a regular file: {filepath}"
        
        # Get file extension
        _, ext = os.path.splitext(filepath)
        ext = ext.lower()
        
        # Handle based on file type
        try:
            # Force text mode if requested
            if force_text_mode:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    return f.read()
            
            # Process by file type if auto_detect_type is True
            if auto_detect_type:
                # Text files - direct read
                if ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', 
                          '.csv', '.log', '.sh', '.bat', '.ini', '.conf', '.yaml', '.yml']:
                    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                        return f.read()
                
                # PDF - use document utils
                elif ext == '.pdf':
                    from utils.document_utils import read_pdf_text
                    return read_pdf_text(filepath)
                
                # Office documents
                elif ext in ['.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt']:
                    from utils.document_utils import convert_document
                    return convert_document(filepath)
                    
                # Binary files - report file type and size
                else:
                    if force_text_mode:
                        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                            return f.read()
                    else:
                        size = os.path.getsize(filepath)
                        return f"Binary file: {os.path.basename(filepath)} ({size} bytes). Use force_text_mode=True to attempt text reading."
            else:
                # Simple text reading mode (equivalent to old read_file behavior)
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    return f.read()
        
        except Exception as e:
            return f"Error reading file: {e}"

    # Add more filesystem tools as needed...
