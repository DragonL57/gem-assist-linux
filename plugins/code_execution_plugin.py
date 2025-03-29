"""
Code execution plugin for running and analyzing Python code.
"""
import os
import sys
import io
import traceback
from typing import Dict, Any, List, Optional, Union
import json

from plugins import Plugin, tool, capability, PluginError
from core_utils import tool_message_print, tool_report_print

class CodeExecutionPlugin(Plugin):
    """Plugin providing code execution capabilities."""
    
    @staticmethod
    @tool(
        categories=["code", "execution"],
        requires_filesystem=True,
        example_usage="execute_python_code('print(\"Hello, world!\")')"
    )
    def execute_python_code(code: str, timeout: int = 60) -> Dict[str, Any]:
        """
        Execute Python code and return the result.
        
        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds
            
        Returns:
            Dictionary with stdout, stderr, and execution result
        """
        tool_message_print("Executing Python code")
        
        # Capture standard output and error
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # Store the original stdout and stderr
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        try:
            # Import common modules that might be useful
            try:
                import numpy as np
                import pandas as pd
                import matplotlib.pyplot as plt
                import datetime
                import re
                import math
                import json
            except ImportError as e:
                raise PluginError(
                    f"Required module not available: {str(e)}", 
                    plugin_name=CodeExecutionPlugin.__name__
                ) from e
            
            # Create locals dictionary with common modules
            local_vars = {
                'np': np,
                'pd': pd,
                'plt': plt,
                'datetime': datetime,
                're': re,
                'math': math,
                'json': json
            }
            
            # Redirect stdout and stderr
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            
            # Execute the code with timeout
            import time
            start_time = time.time()
            
            # Execute in the local scope
            exec_result = exec(code, globals(), local_vars)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Check if there's a variable named 'result' defined in the execution
            result_var = local_vars.get('result')
            
            # Get captured output
            stdout_content = stdout_capture.getvalue()
            stderr_content = stderr_capture.getvalue()
            
            # Create result dictionary
            result = {
                "success": True,
                "stdout": stdout_content,
                "stderr": stderr_content,
                "result": result_var,
                "execution_time": round(execution_time, 4)
            }
            
            # Handle matplotlib plots if any were created
            if 'plt' in local_vars and plt.get_fignums():
                result["has_plots"] = True
                result["plot_count"] = len(plt.get_fignums())
                plt.close('all')  # Close plots to free memory
                
            tool_report_print(f"Code execution completed in {result['execution_time']}s")
            return result
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            error_tb = traceback.format_exc()
            tool_report_print("Code execution failed", error_msg, is_error=True)
            
            return {
                "success": False,
                "stdout": stdout_capture.getvalue(),
                "stderr": stderr_capture.getvalue(),
                "error": error_msg,
                "traceback": error_tb
            }
            
        finally:
            # Restore stdout and stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr
    
    @staticmethod
    @tool(
        categories=["code", "data-analysis"],
        requires_filesystem=True
    )
    def analyze_pandas_dataframe(code: str, summary_only: bool = False) -> Dict[str, Any]:
        """
        Execute code that creates a pandas DataFrame and return analysis of the dataframe. 
        
        Args:
            code: Python code that creates a DataFrame (must define a 'df' variable)
            summary_only: Whether to return only summary statistics (default: False)
            
        Returns:
            Dictionary with DataFrame information and analysis
        """
        tool_message_print("Analyzing pandas DataFrame")
        
        try:
            # Execute the provided code to create the DataFrame
            execution_result = CodeExecutionPlugin.execute_python_code(code)
            
            if not execution_result["success"]:
                raise PluginError(
                    f"Failed to execute code: {execution_result.get('error', 'Unknown error')}",
                    plugin_name=CodeExecutionPlugin.__name__
                )
            
            # Execute analysis code
            analysis_code = """
import pandas as pd
import numpy as np
import json

# Check if 'df' exists and is a DataFrame
if 'df' not in locals() and 'df' not in globals():
    raise ValueError("No DataFrame named 'df' was defined in your code.")
elif not isinstance(df, pd.DataFrame):
    raise ValueError("The variable 'df' is not a pandas DataFrame.")

# Get basic DataFrame information
analysis_result = {
    "success": True,
    "shape": df.shape,
    "columns": df.columns.tolist(),
    "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
    "summary": json.loads(df.describe(include='all').fillna("NA").to_json()),
    "missing_values": df.isna().sum().to_dict(),
}

# Add sample data if not summary_only
if not {summary_only}:
    # Convert to JSON-serializable format
    sample = df.head(5).to_dict(orient='records')
    analysis_result["sample_data"] = sample

# Store the result
result = analysis_result
""".format(summary_only=summary_only)
            
            # Execute the analysis code
            analysis_execution = CodeExecutionPlugin.execute_python_code(analysis_code)
            
            if not analysis_execution["success"]:
                raise PluginError(
                    f"Failed to analyze DataFrame: {analysis_execution.get('error', 'Unknown error')}",
                    plugin_name=CodeExecutionPlugin.__name__
                )
            
            # Get the analysis results
            analysis = analysis_execution.get("result", {})
            if not isinstance(analysis, dict) or not analysis.get("success"):
                raise PluginError(
                    "Invalid analysis result format",
                    plugin_name=CodeExecutionPlugin.__name__
                )
            
            # Print analysis summary
            shape_str = f"{analysis['shape'][0]} rows × {analysis['shape'][1]} columns" if analysis.get("shape") else "unknown shape"
            tool_report_print(f"DataFrame analysis complete: {shape_str}")
            
            return analysis
            
        except PluginError:
            raise
        except Exception as e:
            raise PluginError(f"Error analyzing pandas dataframe: {e}", plugin_name=CodeExecutionPlugin.__name__) from e
