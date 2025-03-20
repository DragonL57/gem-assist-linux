"""
Archive utility functions for the gem-assist package.
These functions are used for working with zip files.
"""

import os
import zipfile
from .core import tool_message_print, tool_report_print

def zip_archive_files(file_name: str, files: list[str]) -> str:
    """
    Zip files into a single zip file.

    Args:
      file_name: The name of the zip file (needs to include .zip).
      files: A list of file paths to zip.

    Returns: The path to the zip file.
    """
    tool_message_print("zip_archive_files", [("file_name", file_name), ("files", str(files))])
    try:
        with zipfile.ZipFile(file_name, "w") as zipf:
            for file in files:
                # Add file to zip with just its basename to avoid including full path
                zipf.write(file, arcname=os.path.basename(file))
        tool_report_print("Status:", "Files zipped successfully")
        return file_name
    except Exception as e:
        tool_report_print("Error zipping files:", str(e), is_error=True)
        return f"Error zipping files: {e}"

def zip_extract_files(zip_file: str, extract_path: str | None) -> list[str]:
    """
    Extract files from a zip archive.

    Args:
      zip_file: The path to the zip file to extract.
      extract_path: The directory to extract files to. If None, extracts to current directory.

    Returns: A list of paths to the extracted files.
    """
    tool_message_print("zip_extract_files", [("zip_file", zip_file), ("extract_path", str(extract_path))])
    try:
        if extract_path is None:
            extract_path = os.getcwd()
        
        # Create the extraction directory if it doesn't exist
        os.makedirs(extract_path, exist_ok=True)
        
        extracted_files = []
        with zipfile.ZipFile(zip_file, 'r') as zipf:
            zipf.extractall(path=extract_path)
            # Get list of all extracted files
            extracted_files = [os.path.join(extract_path, filename) for filename in zipf.namelist()]
        
        tool_report_print("Status:", f"Files extracted successfully to {extract_path}")
        return extracted_files
    except Exception as e:
        tool_report_print("Error extracting zip file:", str(e), is_error=True)
        return f"Error extracting zip file: {e}"
