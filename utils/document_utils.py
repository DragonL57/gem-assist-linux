"""
Document utilities for file format conversion.
"""
import os
import subprocess
import tempfile
from typing import Optional, Dict, Any, List, Union, Literal
from io import BytesIO

# Handle optional dependencies
PANDAS_AVAILABLE = False
PYPDF2_AVAILABLE = False
DOCX_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pass

# For PDF handling
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    pass

# For docx handling
try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    pass

from .core import tool_message_print, tool_report_print

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

def read_excel_file(filepath: str, sheet_name: Literal["0", "1", "2"] = "0", 
                   return_format: Literal["json", "csv", "dict", "dataframe"] = "json") -> Dict[str, Any]:
    """
    Read Excel files (.xlsx, .xls) directly using pandas without external conversion.
    
    Args:
        filepath: Path to the Excel file
        sheet_name: Sheet to read (0 by default for first sheet, can be name or index)
        return_format: Format to return data in ("json", "csv", "dict", "dataframe")
        
    Returns:
        The content of the Excel file in the requested format
    """
    tool_message_print("read_excel_file", [
        ("filepath", filepath),
        ("sheet_name", str(sheet_name)),
        ("return_format", return_format)
    ])
    
    if not PANDAS_AVAILABLE:
        error_message = "pandas library is not installed. Please install it with: uv pip install pandas"
        tool_report_print("Error reading Excel file:", error_message, is_error=True)
        return f"Error: {error_message}"
    
    try:
        # Read the Excel file
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        
        # Return data in the requested format
        if return_format.lower() == "json":
            result = df.to_json(orient="records")
            tool_report_print("Excel data converted to JSON:", f"{len(df)} rows from {filepath}")
            return result
        elif return_format.lower() == "csv":
            result = df.to_csv(index=False)
            tool_report_print("Excel data converted to CSV:", f"{len(df)} rows from {filepath}")
            return result
        elif return_format.lower() == "dict":
            result = df.to_dict(orient="records")
            tool_report_print("Excel data converted to dict:", f"{len(df)} rows from {filepath}")
            return result
        elif return_format.lower() == "dataframe":
            tool_report_print("Excel data loaded as DataFrame:", f"{len(df)} rows from {filepath}")
            return df
        else:
            raise ValueError(f"Unsupported return format: {return_format}")
    
    except Exception as e:
        tool_report_print("Error reading Excel file:", str(e), is_error=True)
        return f"Error reading Excel file: {str(e)}"

def read_excel_structure(filepath: str) -> Dict:
    """
    Read the structure of an Excel file including sheet names and column headers.
    
    Args:
        filepath: Path to the Excel file
        
    Returns:
        A dictionary containing the structure of the Excel file
    """
    tool_message_print("read_excel_structure", [("filepath", filepath)])
    
    if not PANDAS_AVAILABLE:
        error_message = "pandas library is not installed. Please install it with: uv pip install pandas"
        tool_report_print("Error reading Excel structure:", error_message, is_error=True)
        return {"error": error_message}
    
    try:
        # Read Excel file with pandas
        excel_file = pd.ExcelFile(filepath)
        sheet_names = excel_file.sheet_names
        
        structure = {
            "filename": os.path.basename(filepath),
            "sheets": {}
        }
        
        # Get column headers for each sheet
        for sheet in sheet_names:
            # Read just the header row to get column names
            df = pd.read_excel(filepath, sheet_name=sheet, nrows=0)
            structure["sheets"][sheet] = {
                "columns": df.columns.tolist(),
                "row_count": len(pd.read_excel(filepath, sheet_name=sheet))
            }
        
        tool_report_print("Excel structure read:", f"{len(sheet_names)} sheets in {filepath}")
        return structure
    
    except Exception as e:
        tool_report_print("Error reading Excel structure:", str(e), is_error=True)
        return {"error": str(e)}

def read_pdf_text(filepath: str, page_numbers: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Extract text content from a PDF file.
    
    Args:
        filepath: Path to the PDF file
        page_numbers: List of specific page numbers to extract (0-indexed, None for all pages)
        
    Returns:
        The extracted text content or a dictionary with page texts
    """
    tool_message_print("read_pdf_text", [
        ("filepath", filepath),
        ("page_numbers", str(page_numbers) if page_numbers else "all")
    ])
    
    if not PYPDF2_AVAILABLE:
        error_message = "PyPDF2 library is not installed. Please install it with: uv pip install PyPDF2"
        tool_report_print("Error reading PDF file:", error_message, is_error=True)
        return f"Error: {error_message}"
    
    try:
        with open(filepath, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            total_pages = len(reader.pages)
            
            if page_numbers is None:
                # Extract all pages
                pages_to_read = range(total_pages)
                result = ""
                for i in pages_to_read:
                    page = reader.pages[i]
                    result += page.extract_text() + "\n\n"
                
                tool_report_print("PDF text extracted:", f"{total_pages} pages from {filepath}")
                return result
            else:
                # Extract specific pages
                result = {}
                for page_num in page_numbers:
                    if 0 <= page_num < total_pages:
                        page = reader.pages[page_num]
                        result[f"page_{page_num+1}"] = page.extract_text()
                
                tool_report_print("PDF text extracted:", f"{len(page_numbers)} specified pages from {filepath}")
                return result
    
    except Exception as e:
        tool_report_print("Error reading PDF file:", str(e), is_error=True)
        return f"Error reading PDF file: {str(e)}"

def convert_excel_to_format(filepath: str, output_format: Literal["csv", "json", "html"], 
                           output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Convert Excel file to other formats (CSV, JSON, HTML) using pandas.
    
    Args:
        filepath: Path to the Excel file
        output_format: Target format (csv, json, html)
        output_path: Path to save the converted file (None for auto-generate)
        
    Returns:
        A dictionary with the result of the conversion
    """
    tool_message_print("convert_excel_to_format", [
        ("filepath", filepath),
        ("output_format", output_format),
        ("output_path", output_path or "auto-generated")
    ])
    
    if not PANDAS_AVAILABLE:
        error_message = "pandas library is not installed. Please install it with: uv pip install pandas"
        tool_report_print("Error converting Excel file:", error_message, is_error=True)
        return {
            "success": False,
            "error": error_message,
            "output_file": None
        }
    
    try:
        # Generate output path if not provided
        if output_path is None:
            base_name = os.path.splitext(os.path.basename(filepath))[0]
            output_dir = os.path.dirname(filepath)
            output_path = os.path.join(output_dir, f"{base_name}.{output_format}")
        
        # Read the Excel file
        df = pd.read_excel(filepath)
        
        # Convert to the requested format
        if output_format.lower() == "csv":
            df.to_csv(output_path, index=False)
        elif output_format.lower() == "json":
            df.to_json(output_path, orient="records", indent=4)
        elif output_format.lower() == "html":
            df.to_html(output_path, index=False)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
        
        tool_report_print("Excel conversion successful:", f"Converted to {output_format}: {output_path}")
        return {
            "success": True,
            "output_file": output_path,
            "rows_processed": len(df)
        }
    
    except Exception as e:
        tool_report_print("Error converting Excel file:", str(e), is_error=True)
        return {
            "success": False,
            "error": str(e),
            "output_file": None
        }
