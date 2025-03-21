"""
Code execution utilities for the gem-assist package.
Provides a safe environment for executing Python code snippets.
"""

import sys
import io
import traceback
import contextlib
import ast
from typing import Dict, Any, Optional, List, Tuple, Literal
import time

# Handle optional dependencies
PANDAS_AVAILABLE = False
NUMPY_AVAILABLE = False
MATPLOTLIB_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pass

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    pass

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    pass

# Common data manipulation libraries
ALLOWED_IMPORTS = {
    "pandas": "pd",
    "numpy": "np",
    "matplotlib.pyplot": "plt", 
    "requests": "requests",
    "bs4": "bs4",
    "json": "json",
    "re": "re",
    "datetime": "datetime",
    "collections": "collections",
    "math": "math",
    "statistics": "statistics",
    "itertools": "itertools"
}

from .core import tool_message_print, tool_report_print

def execute_python_code(code: str, timeout: int = 30, 
                       allowed_modules: str = None, 
                       show_plots: bool = False) -> Dict[str, Any]:
    """
    Execute Python code in a controlled environment with common data libraries.
    
    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds
        allowed_modules: Comma-separated list of additional allowed modules (e.g., "math,datetime")
        show_plots: Whether to show plots (when using matplotlib)
        
    Returns:
        Dictionary containing execution results, output, and any errors
    """
    tool_message_print("execute_python_code", [
        ("code_length", str(len(code))),
        ("timeout", str(timeout)),
        ("show_plots", str(show_plots))
    ])
    
    # Prepare execution environment
    execution_env = {}
    output_buffer = io.StringIO()
    
    # Parse allowed_modules string into a list if provided
    allowed_modules_list = None
    if allowed_modules:
        allowed_modules_list = [m.strip() for m in allowed_modules.split(",")]
    
    # Track execution time
    start_time = time.time()
    
    # Add specified allowed modules to the execution environment
    modules_to_import = {}
    for module_name, alias in ALLOWED_IMPORTS.items():
        if module_name == "pandas" and not PANDAS_AVAILABLE:
            continue
        if module_name == "numpy" and not NUMPY_AVAILABLE:
            continue
        if module_name == "matplotlib.pyplot" and not MATPLOTLIB_AVAILABLE:
            continue
        modules_to_import[module_name] = alias
    
    if allowed_modules_list:
        for module_name in allowed_modules_list:
            if module_name not in modules_to_import:
                modules_to_import[module_name] = module_name.split(".")[-1]
    
    # Import modules
    successful_imports = []
    failed_imports = []
    
    for module_name, alias in modules_to_import.items():
        try:
            exec(f"import {module_name} as {alias}", execution_env)
            successful_imports.append(module_name)
        except ImportError:
            failed_imports.append(module_name)
    
    # Setup for matplotlib if needed
    if "matplotlib.pyplot" in successful_imports and show_plots:
        exec("import matplotlib.pyplot as plt", execution_env)
        exec("plt.switch_backend('agg')", execution_env)
    
    # Check for potentially dangerous operations
    try:
        parsed_ast = ast.parse(code)
        if not is_code_safe(parsed_ast):
            return {
                "success": False,
                "error": "Code contains potentially unsafe operations",
                "output": "Execution blocked for security reasons"
            }
    except SyntaxError as e:
        return {
            "success": False,
            "error": f"Syntax error: {str(e)}",
            "output": traceback.format_exc()
        }
    
    # Execute the code with timeout
    result = {"success": False, "error": None, "output": None}
    
    try:
        with contextlib.redirect_stdout(output_buffer):
            with contextlib.redirect_stderr(output_buffer):
                # Execute with timeout using the helper function
                exit_code = exec_with_timeout(code, execution_env, timeout)
                
                if exit_code == "timeout":
                    result["error"] = f"Execution timed out after {timeout} seconds"
                else:
                    result["success"] = True
    except Exception as e:
        result["error"] = str(e)
        result["output"] = traceback.format_exc()
    
    # Get the captured output
    output = output_buffer.getvalue()
    result["output"] = output
    
    # Capture any plot if requested and available
    if "matplotlib.pyplot" in successful_imports and show_plots and MATPLOTLIB_AVAILABLE:
        try:
            import matplotlib.pyplot as plt
            import base64
            from io import BytesIO
            
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            plot_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            result["plot"] = plot_base64
            plt.close('all')  # Close all plots to free memory
        except Exception as e:
            result["plot_error"] = str(e)
    
    # Add import information
    result["imports"] = {
        "successful": successful_imports,
        "failed": failed_imports
    }
    
    # Add execution time
    execution_time = time.time() - start_time
    result["execution_time"] = execution_time
    
    # Return variables if execution was successful
    if result["success"]:
        # Filter out modules and system variables
        variables = {}
        for key, value in execution_env.items():
            if (not key.startswith("__") and 
                key not in modules_to_import.values() and
                key not in ["exit", "quit"]):
                try:
                    # Try to convert to a simple type for JSON serialization
                    if PANDAS_AVAILABLE and isinstance(value, (pd.DataFrame, pd.Series)):
                        if len(value) <= 10:
                            variables[key] = value.to_dict()
                        else:
                            variables[key] = f"<DataFrame/Series with {len(value)} rows>"
                    elif NUMPY_AVAILABLE and isinstance(value, np.ndarray):
                        if value.size <= 100:
                            variables[key] = value.tolist()
                        else:
                            variables[key] = f"<ndarray with shape {value.shape}>"
                    elif isinstance(value, (int, float, bool, str, list, dict, tuple, type(None))):
                        if isinstance(value, (list, tuple)) and len(value) > 100:
                            variables[key] = f"<{type(value).__name__} with {len(value)} items>"
                        else:
                            variables[key] = value
                except:
                    variables[key] = str(type(value))
        
        result["variables"] = variables
    
    # Report execution result
    status = "successful" if result["success"] else "failed"
    tool_report_print(
        f"Code execution {status}:", 
        f"Executed in {execution_time:.4f}s with {len(output)} characters of output",
        is_error=not result["success"]
    )
    
    # Add missing dependencies note if needed
    if failed_imports:
        missing_deps = ", ".join(failed_imports)
        result["note"] = f"Some imports failed. To enable all features, install: uv pip install {missing_deps}"
    
    return result

def exec_with_timeout(code: str, env: Dict[str, Any], timeout: int) -> str:
    """Helper function to execute code with timeout"""
    import threading
    import ctypes
    
    # Flag to indicate if execution completed
    result = {"status": "running"}
    
    def execute():
        try:
            exec(code, env)
            result["status"] = "completed"
        except Exception:
            result["status"] = "exception"
    
    # Start execution thread
    thread = threading.Thread(target=execute)
    thread.daemon = True
    thread.start()
    
    # Wait for completion or timeout
    thread.join(timeout)
    
    # If still running, it's a timeout
    if thread.is_alive():
        result["status"] = "timeout"
        
        # Try to terminate the thread (works in CPython)
        if hasattr(ctypes, 'pythonapi') and hasattr(ctypes.pythonapi, 'PyThreadState_SetAsyncExc'):
            thread_id = thread.ident
            ctypes.pythonapi.PyThreadState_SetAsyncExc(
                ctypes.c_long(thread_id),
                ctypes.py_object(SystemExit)
            )
    
    return result["status"]

def is_code_safe(node: ast.AST) -> bool:
    """
    Check if the code is potentially unsafe.
    Returns False if any dangerous operations are detected.
    """
    # List of potentially dangerous operations
    dangerous_modules = {
        "os", "subprocess", "sys", "shutil", "pathlib",
        "tempfile", "io", "socket", "pickle"
    }
    
    dangerous_functions = {
        "eval", "exec", "compile", "open", "input", "system"
    }
    
    # Check for dangerous imports
    for node in ast.walk(node):
        # Check for direct imports of dangerous modules
        if isinstance(node, ast.Import):
            for name in node.names:
                if name.name in dangerous_modules:
                    return False
                
        # Check for imports from dangerous modules
        elif isinstance(node, ast.ImportFrom):
            if node.module in dangerous_modules:
                return False
        
        # Check for calls to dangerous functions
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in dangerous_functions:
                return False
    
    return True

def analyze_pandas_dataframe(code: str, df_var_name: str) -> Dict[str, Any]:
    """
    Execute code and provide detailed analysis of a pandas DataFrame variable.
    
    Args:
        code: Python code that creates/manipulates a DataFrame
        df_var_name: Variable name of the DataFrame to analyze
        
    Returns:
        Dictionary with analysis results and statistics about the DataFrame
    """
    tool_message_print("analyze_pandas_dataframe", [
        ("code_length", str(len(code))),
        ("df_var_name", df_var_name)
    ])
    
    if not PANDAS_AVAILABLE:
        error_message = "pandas library is not installed. Please install it with: uv pip install pandas"
        tool_report_print("Error analyzing DataFrame:", error_message, is_error=True)
        return {
            "success": False,
            "error": error_message
        }
    
    # First execute the provided code
    result = execute_python_code(code, timeout=30)
    
    if not result["success"]:
        return result
    
    # Check if the specified DataFrame variable exists
    if df_var_name not in result.get("variables", {}):
        return {
            "success": False,
            "error": f"DataFrame variable '{df_var_name}' not found in execution results",
            "code_output": result["output"]
        }
    
    # Add additional analysis code
    analysis_code = f"""
# Analyze the DataFrame
import pandas as pd
import json
import io

df = {df_var_name}

# Basic information
df_info_buffer = io.StringIO()
df.info(buf=df_info_buffer)
df_info = df_info_buffer.getvalue()

# Get column types
column_types = df.dtypes.astype(str).to_dict()

# Basic statistics
try:
    numeric_stats = df.describe().to_dict()
except:
    numeric_stats = {{"error": "Could not generate numeric statistics"}}

# Missing values
missing_values = df.isna().sum().to_dict()
missing_percentage = (df.isna().sum() / len(df) * 100).to_dict()

# Sample data (first 5 rows)
sample_data = df.head().to_dict()

# Shape information
row_count, col_count = df.shape

# Column unique values (for categorical columns)
unique_values = {{}}
for col in df.select_dtypes(include=['object', 'category']).columns:
    if df[col].nunique() < 20:  # Only for columns with fewer unique values
        unique_values[col] = df[col].value_counts().head().to_dict()

analysis_result = {{
    "shape": {{"rows": row_count, "columns": col_count}},
    "column_types": column_types,
    "numeric_stats": numeric_stats,
    "missing_values": missing_values,
    "missing_percentage": missing_percentage,
    "sample_data": sample_data,
    "unique_value_counts": unique_values,
    "df_info": df_info
}}

print(json.dumps(analysis_result))
"""
    
    # Execute the analysis code
    analysis_result = execute_python_code(analysis_code, timeout=30)
    
    if not analysis_result["success"]:
        return {
            "success": False,
            "error": "Failed to analyze DataFrame",
            "analysis_error": analysis_result["error"],
            "code_output": result["output"]
        }
    
    # Parse the JSON output from the analysis
    try:
        import json
        output_lines = analysis_result["output"].strip().split('\n')
        # Find the JSON part (last line should be our JSON)
        json_line = output_lines[-1]
        analysis_data = json.loads(json_line)
        
        tool_report_print("DataFrame analysis complete:", 
                         f"Analyzed {df_var_name} with shape {analysis_data['shape']['rows']}x{analysis_data['shape']['columns']}")
        
        return {
            "success": True,
            "code_output": result["output"],
            "analysis": analysis_data
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to parse analysis results: {str(e)}",
            "code_output": result["output"],
            "analysis_output": analysis_result["output"]
        }
