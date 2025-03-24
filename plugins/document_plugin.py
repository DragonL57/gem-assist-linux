"""
Document plugin for working with various document formats.
"""
import os
from typing import Dict, Any, List, Optional, Union

from plugins import Plugin, tool, capability
from core_utils import tool_message_print, tool_report_print

class DocumentPlugin(Plugin):
    """Plugin providing document processing capabilities."""
    
    @staticmethod
    @tool(
        categories=["document", "conversion"],
        requires_filesystem=True
    )
    def convert_document(file_path: str, output_format: str = "text") -> str:
        """
        Convert a document to another format or extract its content.
        
        Args:
            file_path: Path to the document file
            output_format: Desired output format (text, html, md)
            
        Returns:
            Extracted or converted document content
        """
        tool_message_print(f"Converting {file_path} to {output_format}")
        
        try:
            if not os.path.exists(file_path):
                return f"Error: File not found: {file_path}"
                
            # Get file extension
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            
            # Handle different document types
            
            # Word documents
            if ext in ['.docx', '.doc']:
                try:
                    import docx
                    
                    doc = docx.Document(file_path)
                    content = []
                    
                    for para in doc.paragraphs:
                        content.append(para.text)
                        
                    if output_format == "html":
                        # Simple HTML conversion
                        html_content = "<html><body>"
                        for para in content:
                            if para.strip():
                                html_content += f"<p>{para}</p>"
                        html_content += "</body></html>"
                        return html_content
                    elif output_format == "md":
                        # Simple Markdown conversion
                        return "\n\n".join(content)
                    else:  # text
                        return "\n\n".join(content)
                except ImportError:
                    return "Error: python-docx package is required for .docx processing"
                except Exception as e:
                    return f"Error processing Word document: {e}"
            
            # PDF documents
            elif ext == '.pdf':
                return DocumentPlugin.read_pdf_text(file_path)
            
            # Excel files
            elif ext in ['.xlsx', '.xls']:
                if output_format == "text":
                    return DocumentPlugin.read_excel_structure(file_path)
                else:
                    return DocumentPlugin.convert_excel_to_format(file_path, output_format)
            
            # Unsupported formats
            else:
                return f"Error: Unsupported file format: {ext}"
                
        except Exception as e:
            return f"Error converting document: {e}"
    
    @staticmethod
    @tool(
        categories=["document", "excel"],
        requires_filesystem=True
    )
    def read_excel_file(file_path: str, sheet_name: str = None, max_rows: int = 100) -> Dict[str, Any]:
        """
        Read an Excel file and return its content as structured data.
        
        Args:
            file_path: Path to the Excel file
            sheet_name: Name of the sheet to read (default: first sheet)
            max_rows: Maximum number of rows to read (default: 100)
            
        Returns:
            Dictionary containing Excel data and metadata
        """
        tool_message_print(f"Reading Excel file: {file_path}")
        
        try:
            import pandas as pd
            
            if not os.path.exists(file_path):
                return {"error": f"File not found: {file_path}"}
                
            # Get Excel file sheet names
            xl = pd.ExcelFile(file_path)
            sheet_names = xl.sheet_names
            
            # Use first sheet if none specified
            if sheet_name is None and sheet_names:
                sheet_name = sheet_names[0]
            
            # Read the specified sheet
            if sheet_name in sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=max_rows)
                
                # Convert DataFrame to dict for JSON serialization
                data = df.to_dict(orient='records')
                
                result = {
                    "file": os.path.basename(file_path),
                    "sheet": sheet_name,
                    "sheet_names": sheet_names,
                    "rows": len(data),
                    "columns": list(df.columns),
                    "data": data,
                }
                
                # Print summary
                tool_report_print(f"Read {len(data)} rows from sheet '{sheet_name}'")
                
                return result
            else:
                return {"error": f"Sheet '{sheet_name}' not found in Excel file"}
                
        except ImportError:
            return {"error": "pandas package is required for Excel processing"}
        except Exception as e:
            return {"error": f"Error reading Excel file: {e}"}
    
    @staticmethod
    @tool(
        categories=["document", "excel"],
        requires_filesystem=True
    )
    def read_excel_structure(file_path: str) -> Dict[str, Any]:
        """
        Read the structure of an Excel file, including sheet names and column headers.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Dictionary containing Excel structure information
        """
        tool_message_print(f"Reading Excel structure: {file_path}")
        
        try:
            import pandas as pd
            
            if not os.path.exists(file_path):
                return {"error": f"File not found: {file_path}"}
                
            # Get Excel file sheet names
            xl = pd.ExcelFile(file_path)
            sheet_names = xl.sheet_names
            
            # Read column headers from each sheet
            structure = {}
            for sheet in sheet_names:
                # Read just the header row
                df_header = pd.read_excel(file_path, sheet_name=sheet, nrows=0)
                columns = list(df_header.columns)
                
                # Get row count for the sheet
                df_info = pd.read_excel(file_path, sheet_name=sheet, header=None)
                row_count = len(df_info)
                
                structure[sheet] = {
                    "columns": columns,
                    "column_count": len(columns),
                    "row_count": row_count
                }
            
            result = {
                "file": os.path.basename(file_path),
                "sheet_count": len(sheet_names),
                "sheet_names": sheet_names,
                "sheets": structure
            }
            
            # Generate text summary
            summary = [f"Excel file: {os.path.basename(file_path)}"]
            summary.append(f"Contains {len(sheet_names)} sheets:")
            
            for sheet, info in structure.items():
                summary.append(f"  - {sheet}: {info['row_count']} rows, {info['column_count']} columns")
                if info['columns']:
                    col_str = ", ".join(str(c) for c in info['columns'][:5])
                    if len(info['columns']) > 5:
                        col_str += "..."
                    summary.append(f"    Columns: {col_str}")
            
            result["summary"] = "\n".join(summary)
            
            # Print summary
            tool_report_print(f"Excel structure: {len(sheet_names)} sheets identified")
            
            return result
                
        except ImportError:
            return {"error": "pandas package is required for Excel processing"}
        except Exception as e:
            return {"error": f"Error reading Excel structure: {e}"}
    
    @staticmethod
    @tool(
        categories=["document", "pdf"],
        requires_filesystem=True
    )
    def read_pdf_text(file_path: str, start_page: int = 1, max_pages: int = None) -> str:
        """
        Extract text content from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            start_page: First page to extract (1-based index)
            max_pages: Maximum number of pages to extract
            
        Returns:
            Extracted text content
        """
        tool_message_print(f"Reading PDF: {file_path}")
        
        try:
            import pypdf
            
            if not os.path.exists(file_path):
                return f"Error: File not found: {file_path}"
            
            # Open the PDF file
            with open(file_path, 'rb') as file:
                # Create a PDF reader object
                reader = pypdf.PdfReader(file)
                
                # Get information about the PDF
                num_pages = len(reader.pages)
                
                # Adjust page range
                start_idx = start_page - 1  # Convert to 0-based index
                if start_idx < 0:
                    start_idx = 0
                
                end_idx = num_pages
                if max_pages is not None:
                    end_idx = min(start_idx + max_pages, num_pages)
                
                # Extract text from each page
                text_content = []
                for i in range(start_idx, end_idx):
                    page = reader.pages[i]
                    text_content.append(page.extract_text())
                
                # Join text content with page separators
                result = ""
                for i, text in enumerate(text_content):
                    result += f"\n--- Page {start_idx + i + 1} ---\n\n"
                    result += text
                    result += "\n\n"
                
                # Print summary
                tool_report_print(f"Extracted text from {len(text_content)} of {num_pages} pages")
                
                return result
                
        except ImportError:
            return "Error: pypdf package is required for PDF processing"
        except Exception as e:
            return f"Error extracting PDF text: {e}"
    
    @staticmethod
    @tool(
        categories=["document", "excel"],
        requires_filesystem=True
    )
    def convert_excel_to_format(file_path: str, output_format: str = "csv", sheet_name: str = None) -> str:
        """
        Convert an Excel file to another format.
        
        Args:
            file_path: Path to the Excel file
            output_format: Output format (csv, json, html, markdown)
            sheet_name: Name of the sheet to convert (default: first sheet)
            
        Returns:
            Converted content as a string
        """
        tool_message_print(f"Converting Excel to {output_format}: {file_path}")
        
        try:
            import pandas as pd
            import json
            
            if not os.path.exists(file_path):
                return f"Error: File not found: {file_path}"
                
            # Get Excel file sheet names
            xl = pd.ExcelFile(file_path)
            sheet_names = xl.sheet_names
            
            # Use first sheet if none specified
            if sheet_name is None and sheet_names:
                sheet_name = sheet_names[0]
            
            # Read the specified sheet
            if sheet_name in sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Convert according to requested format
                if output_format.lower() == "csv":
                    output = df.to_csv(index=False)
                elif output_format.lower() == "json":
                    output = json.dumps(df.to_dict(orient='records'), indent=2)
                elif output_format.lower() == "html":
                    output = df.to_html(index=False)
                elif output_format.lower() == "markdown" or output_format.lower() == "md":
                    output = df.to_markdown(index=False)
                else:
                    return f"Error: Unsupported output format: {output_format}"
                
                # Print summary
                tool_report_print(f"Converted {len(df)} rows to {output_format} format")
                
                return output
            else:
                return f"Error: Sheet '{sheet_name}' not found in Excel file"
                
        except ImportError:
            return "Error: pandas package is required for Excel processing"
        except Exception as e:
            return f"Error converting Excel: {e}"
