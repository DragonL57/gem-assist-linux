"""
Archive plugin providing zip file operations.
"""
import os
import zipfile
from typing import List, Dict, Any, Optional, Union

from plugins import Plugin, tool, capability, PluginError
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
            # Validate inputs
            if not files:
                raise PluginError(
                    "No files specified for archiving",
                    plugin_name=ArchivePlugin.__name__
                )
            
            # Check if any files exist
            existing_files = [f for f in files if os.path.exists(f)]
            if not existing_files:
                raise PluginError(
                    "None of the specified files exist",
                    plugin_name=ArchivePlugin.__name__
                )
                
            # Ensure the file has .zip extension
            if not file_name.endswith('.zip'):
                file_name += '.zip'
            
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(os.path.abspath(file_name)), exist_ok=True)
                
            # Create the zip file
            with zipfile.ZipFile(file_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add each existing file to the archive
                archived_files = []
                for file in files:
                    if os.path.exists(file):
                        # Add the file with its basename as the archive name
                        zipf.write(file, os.path.basename(file))
                        archived_files.append(os.path.basename(file))
                        
            # Get information about the created archive
            archive_size = os.path.getsize(file_name)
            
            tool_report_print(f"Created archive with {len(archived_files)} files")
            
            return {
                "archive_name": file_name,
                "archive_size": archive_size,
                "file_count": len(archived_files),
                "files": archived_files
            }
            
        except PluginError:
            raise
        except Exception as e:
            raise PluginError(f"Error creating zip archive: {e}", plugin_name=ArchivePlugin.__name__) from e
    
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
                raise PluginError(
                    f"Zip file not found: {zip_file}",
                    plugin_name=ArchivePlugin.__name__
                )
            
            # Verify it's actually a zip file
            if not zipfile.is_zipfile(zip_file):
                raise PluginError(
                    f"File is not a valid zip archive: {zip_file}",
                    plugin_name=ArchivePlugin.__name__
                )
                
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
                
                if not file_list:
                    raise PluginError(
                        "Zip archive is empty",
                        plugin_name=ArchivePlugin.__name__
                    )
                
                # Extract all files
                zipf.extractall(extract_path)
                
                # Build the list of extracted files with full paths
                extracted_files = [os.path.join(extract_path, f) for f in file_list]
                
            tool_report_print(f"Extracted {len(extracted_files)} files to {extract_path}")
            
            return {
                "extract_path": extract_path,
                "file_count": len(extracted_files),
                "files": extracted_files
            }
            
        except PluginError:
            raise
        except zipfile.BadZipFile as e:
            raise PluginError(
                f"Invalid or corrupted zip file: {e}",
                plugin_name=ArchivePlugin.__name__
            ) from e
        except Exception as e:
            raise PluginError(f"Error extracting zip archive: {e}", plugin_name=ArchivePlugin.__name__) from e
