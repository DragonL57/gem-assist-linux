"""
Document utilities for file format conversion.
"""
import os
import subprocess
import tempfile
from typing import Optional

def convert_document(source_file: str, target_format: str, output_dir: Optional[str] = None) -> dict:
    """
    Convert a document to a different format using LibreOffice.
    
    Args:
        source_file: The path to the source file
        target_format: The target format (e.g., 'pdf', 'docx', 'odt')
        output_dir: The directory to save the output file (default: same as source file)
    
    Returns:
        A dictionary with conversion status and output file path
    """
    # Verify source file exists
    if not os.path.exists(source_file):
        return {
            "success": False,
            "error": f"Source file does not exist: {source_file}",
            "output_file": None
        }
    
    # Get absolute paths
    source_file = os.path.abspath(source_file)
    
    # Set output directory
    if not output_dir:
        output_dir = os.path.dirname(source_file)
    output_dir = os.path.abspath(output_dir)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get base filename without extension
    base_name = os.path.splitext(os.path.basename(source_file))[0]
    output_file = os.path.join(output_dir, f"{base_name}.{target_format}")
    
    # Create a temporary script to handle conversion
    # This avoids issues with special characters in filenames
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as script:
        script.write('#!/bin/bash\n')
        script.write(f'cd "{os.path.dirname(source_file)}"\n')
        script.write(f'libreoffice --headless --convert-to {target_format} "{source_file}" --outdir "{output_dir}"\n')
    
    try:
        # Make the script executable
        os.chmod(script.name, 0o755)
        
        # Run the conversion script
        process = subprocess.Popen(
            [script.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        
        # Check if conversion was successful
        if process.returncode == 0 and os.path.exists(output_file):
            return {
                "success": True,
                "output_file": output_file,
                "stdout": stdout,
                "stderr": stderr
            }
        else:
            return {
                "success": False,
                "error": f"Conversion failed: {stderr}",
                "output_file": None,
                "stdout": stdout,
                "stderr": stderr
            }
    finally:
        # Clean up the temporary script
        os.unlink(script.name)
