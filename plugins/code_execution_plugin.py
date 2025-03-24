"""
Code execution plugin for running and analyzing Python code.
"""
import os
import sys
import io
import traceback
from typing import Dict, Any, List, Optional, Union
import json

from plugins import Plugin, tool, capability
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
        
        # Set up result dictionary
        result = {
            "success": False,
            "stdout": "",
            "stderr": "",
            "result": None,
            "error": None,
            "execution_time": 0
        }
        
        try:
            # Redirect stdout and stderr
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            
            # Import common modules that might be useful
            import numpy as np
            import pandas as pd
            import matplotlib.pyplot as plt
            import datetime
            import re
            import math
            import json
            
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
            
            # Execute the code with timeout
            import time
            start_time = time.time()
            
            # Execute in the local scope
            exec_result = exec(code, globals(), local_vars)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Check if there's a variable named 'result' defined in the execution
            result_var = local_vars.get('result')
            
            # Update result dictionary
            result.update({
                "success": True,
                "stdout": stdout_capture.getvalue(),
                "stderr": stderr_capture.getvalue(),
                "result": result_var,
                "execution_time": round(execution_time, 4)
            })
            
            # Handle matplotlib plots if any were created
            if 'plt' in local_vars and plt.get_fignums():
                result["has_plots"] = True
                result["plot_count"] = len(plt.get_fignums())
                # Note: In a real implementation, we might save plots to files
                plt.close('all')  # Close plots to free memory
            
        except Exception as e:
            # Capture the error
            result.update({
                "success": False,
                "stdout": stdout_capture.getvalue(),
                "stderr": stderr_capture.getvalue(),
                "error": f"{type(e).__name__}: {str(e)}",
                "traceback": traceback.format_exc()
            })
        finally:
            # Restore stdout and stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr
        
        # Print execution summary
        if result["success"]:
            tool_report_print(f"Code execution completed in {result['execution_time']}s")
        else:
            tool_report_print("Code execution failed", result["error"], is_error=True)
        
        return result
    
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
        
        # Create a dictionary to store the analysis results
        analysis = {
            "success": False,
            "error": None,
            "shape": None,
            "columns": None,
            "dtypes": None,
            "summary": None,
            "sample_data": None,
            "missing_values": None,
            "execution_details": {}
        }
        
        # Execute the provided code to create the DataFrame
        execution_result = CodeExecutionPlugin.execute_python_code(code)
        analysis["execution_details"] = {
            "success": execution_result["success"],
            "stdout": execution_result["stdout"],
            "stderr": execution_result["stderr"],
            "error": execution_result["error"]
        }
        
        if not execution_result["success"]:
            analysis["error"] = "Failed to execute code"
            return analysis
        
        # Execute analysis code on the DataFrame
        analysis_code = """
import pandas as pd
import numpy as np
import json

# Check if 'df' exists and is a DataFrame
if 'df' not in locals() and 'df' not in globals():
    print("Error: No DataFrame named 'df' was defined in your code.")
    analysis_result = {"success": False, "error": "No DataFrame found"}
else:
    try:
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
    except Exception as e:
        analysis_result = {
            "success": False,
            "error": str(e)
        }

# Store the result in a variable
result = analysis_result
""".format(summary_only=summary_only)
        
        # Execute the analysis code
        analysis_execution = CodeExecutionPlugin.execute_python_code(analysis_code)
        
        if not analysis_execution["success"]:
            analysis["error"] = "Failed to analyze DataFrame: " + str(analysis_execution["error"])
            return analysis
        
        # Extract analysis results
        if isinstance(analysis_execution["result"], dict):
            # Update our analysis dictionary with the results
            analysis.update(analysis_execution["result"])
        
        # Print analysis summary
        if analysis["success"]:
            shape_str = f"{analysis['shape'][0]} rows × {analysis['shape'][1]} columns" if analysis["shape"] else "unknown shape"
            tool_report_print(f"DataFrame analysis complete: {shape_str}")
        else:
            tool_report_print("DataFrame analysis failed", analysis["error"], is_error=True)
        
        return analysis
