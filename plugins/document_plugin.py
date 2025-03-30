"""
Document plugin for working with various document formats.
"""
import os
from typing import Dict, Any, List, Optional, Union

from plugins import Plugin, tool, capability, PluginError
from core_utils import tool_message_print, tool_report_print

class DocumentPlugin(Plugin):
    """Plugin providing document processing capabilities."""
    
    # Removed convert_document tool. Use filesystem_plugin.read_file instead.
    
    @staticmethod
    @tool(
        categories=["document_formats"],
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
            try:
                import pandas as pd
            except ImportError:
                raise PluginError(
                    "pandas package is required for Excel processing",
                    plugin_name=DocumentPlugin.__name__
                )
            
            if not os.path.exists(file_path):
                raise PluginError(
                    f"File not found: {file_path}",
                    plugin_name=DocumentPlugin.__name__
                )
                
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
                raise PluginError(
                    f"Sheet '{sheet_name}' not found in Excel file",
                    plugin_name=DocumentPlugin.__name__
                )
                
        except PluginError:
            raise
        except Exception as e:
            raise PluginError(f"Error reading excel file: {e}", plugin_name=DocumentPlugin.__name__) from e
    
    @staticmethod
    @tool(
        categories=["document_formats"],
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
            try:
                import pandas as pd
            except ImportError:
                raise PluginError(
                    "pandas package is required for Excel processing",
                    plugin_name=DocumentPlugin.__name__
                )
            
            if not os.path.exists(file_path):
                raise PluginError(
                    f"File not found: {file_path}",
                    plugin_name=DocumentPlugin.__name__
                )
                
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
                
        except PluginError:
            raise
        except Exception as e:
            raise PluginError(f"Error reading excel structure: {e}", plugin_name=DocumentPlugin.__name__) from e
    
    # Removed read_pdf_text tool. Use filesystem_plugin.read_file instead.
    
    @staticmethod
    @tool(
        categories=["document_formats"],
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
            try:
                import pandas as pd
                import json
            except ImportError:
                raise PluginError(
                    "pandas package is required for Excel processing",
                    plugin_name=DocumentPlugin.__name__
                )
            
            if not os.path.exists(file_path):
                raise PluginError(
                    f"File not found: {file_path}",
                    plugin_name=DocumentPlugin.__name__
                )
                
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
                    raise PluginError(
                        f"Unsupported output format: {output_format}",
                        plugin_name=DocumentPlugin.__name__
                    )
                
                # Print summary
                tool_report_print(f"Converted {len(df)} rows to {output_format} format")
                
                return output
            else:
                raise PluginError(
                    f"Sheet '{sheet_name}' not found in Excel file",
                    plugin_name=DocumentPlugin.__name__
                )
                
        except PluginError:
            raise
        except Exception as e:
            raise PluginError(f"Error converting excel format: {e}", plugin_name=DocumentPlugin.__name__) from e
