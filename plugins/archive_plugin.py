"""
Archive plugin providing zip file operations.
"""
import os
import zipfile
from typing import List, Dict, Any, Optional, Union

from plugins import Plugin, tool, capability
from core_utils import tool_message_print, tool_report_print

class ArchivePlugin(Plugin):
    """Plugin providing archive operations."""
    
    @staticmethod
    @tool(
        categories=["archive", "filesystem"],
        requires_filesystem=True
    )
    def zip_archive_files(file_name: str, files: List[str]) -> Dict[str, Any]:
        """
        Create a zip archive with the specified files.
        
        Args:
            file_name: Name of the zip file to create
            files: List of file paths to include in the archive
            
        Returns:
            Dictionary with information about the created archive
        """
        tool_message_print(f"Creating zip archive: {file_name}")
        
        try:
            # Ensure the file has .zip extension
            if not file_name.endswith('.zip'):
                file_name += '.zip'
                
            # Create the zip file
            with zipfile.ZipFile(file_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add each file to the archive
                for file in files:
                    if os.path.exists(file):
                        # Add the file with its basename as the archive name
                        zipf.write(file, os.path.basename(file))
                        
            # Get information about the created archive
            archive_size = os.path.getsize(file_name)
            
            return {
                "success": True,
                "archive_name": file_name,
                "archive_size": archive_size,
                "file_count": len(files),
                "files": [os.path.basename(f) for f in files if os.path.exists(f)]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    @tool(
        categories=["archive", "filesystem"],
        requires_filesystem=True
    )
    def zip_extract_files(zip_file: str, extract_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract files from a zip archive.
        
        Args:
            zip_file: Path to the zip file
            extract_path: Directory to extract files to (default: same as zip file)
            
        Returns:
            Dictionary with information about the extracted files
        """
        tool_message_print(f"Extracting zip archive: {zip_file}")
        
        try:
            # Check if the zip file exists
            if not os.path.exists(zip_file):
                return {
                    "success": False,
                    "error": f"Zip file not found: {zip_file}"
                }
                
            # Determine extract path
            if extract_path is None:
                extract_path = os.path.dirname(os.path.abspath(zip_file))
                
            # Create the extract directory if it doesn't exist
            os.makedirs(extract_path, exist_ok=True)
            
            # Extract the zip file
            extracted_files = []
            with zipfile.ZipFile(zip_file, 'r') as zipf:
                # Get the list of files in the archive
                file_list = zipf.namelist()
                
                # Extract all files
                zipf.extractall(extract_path)
                
                # Build the list of extracted files with full paths
                extracted_files = [os.path.join(extract_path, f) for f in file_list]
                
            return {
                "success": True,
                "extract_path": extract_path,
                "file_count": len(extracted_files),
                "files": extracted_files
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
