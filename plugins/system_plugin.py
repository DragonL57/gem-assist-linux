"""
System plugin providing system information and operations.
"""
import os
import platform
import subprocess
import time
import datetime
import concurrent.futures
from typing import List, Dict, Any, Optional, Union

from plugins import Plugin, tool, capability, PluginError
from core_utils import tool_message_print, tool_report_print

class SystemPlugin(Plugin):
    """Plugin providing system operations."""
    
    @staticmethod
    @tool(
        categories=["system", "info"],
        requires_filesystem=False
    )
    def get_system_info() -> Dict[str, Any]:
        """
        Get detailed information about the system.
        
        Returns:
            Dictionary containing system information
        """
        import psutil
        
        tool_message_print("Getting system information")
        
        try:
            # Basic system info
            info = {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "hostname": platform.node(),
                "python_version": platform.python_version(),
            }
            
            # CPU information
            cpu_info = {
                "physical_cores": psutil.cpu_count(logical=False),
                "total_cores": psutil.cpu_count(logical=True),
                "cpu_freq_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else "Unknown",
                "cpu_usage_percent": psutil.cpu_percent(interval=1),
            }
            info["cpu"] = cpu_info
            
            # Memory information
            memory = psutil.virtual_memory()
            memory_info = {
                "total_gb": round(memory.total / (1024 ** 3), 2),
                "available_gb": round(memory.available / (1024 ** 3), 2),
                "used_gb": round(memory.used / (1024 ** 3), 2),
                "percent_used": memory.percent,
            }
            info["memory"] = memory_info
            
            # Disk information
            disk_info = []
            for partition in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info.append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "filesystem": partition.fstype,
                        "total_gb": round(usage.total / (1024 ** 3), 2),
                        "used_gb": round(usage.used / (1024 ** 3), 2),
                        "free_gb": round(usage.free / (1024 ** 3), 2),
                        "percent_used": usage.percent,
                    })
                except Exception as e:
                    disk_info.append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "error": str(e)
                    })
            info["disks"] = disk_info
            
            # Network information
            network_info = {}
            for iface, addrs in psutil.net_if_addrs().items():
                network_info[iface] = []
                for addr in addrs:
                    address_info = {
                        "family": str(addr.family),
                        "address": addr.address
                    }
                    network_info[iface].append(address_info)
            info["network"] = network_info
            
            # Current process info
            process = psutil.Process(os.getpid())
            process_info = {
                "pid": process.pid,
                "memory_usage_mb": round(process.memory_info().rss / (1024 * 1024), 2),
                "cpu_usage_percent": process.cpu_percent(interval=1),
                "create_time": datetime.datetime.fromtimestamp(process.create_time()).strftime("%Y-%m-%d %H:%M:%S"),
            }
            info["process"] = process_info
            
            return info
            
        except Exception as e:
            raise PluginError(f"Error getting system info: {e}", plugin_name=SystemPlugin.__name__) from e
    
    @staticmethod
    @tool(
        categories=["system", "shell"],
        requires_filesystem=True,
        example_usage="run_shell_command('ls -la')"
    )
    def run_shell_command(command: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Run a shell command and return the result. 
        
        Args:
            command: Shell command to execute
            timeout: Command timeout in seconds (default: 30)
            
        Returns:
            Dictionary with stdout, stderr, and return code
        """
        tool_message_print(f"Running command: {command}")
        
        try:
            # Run the command with timeout
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                return {
                    "stdout": stdout,
                    "stderr": stderr,
                    "returncode": process.returncode
                }
            except subprocess.TimeoutExpired as e:
                process.kill()
                raise PluginError(f"Command timed out after {timeout} seconds: {e}", plugin_name=SystemPlugin.__name__) from e
                
        except Exception as e:
            raise PluginError(f"Error running shell command: {e}", plugin_name=SystemPlugin.__name__) from e
    
    @staticmethod
    @tool(
        categories=["system", "time"]
    )
    def get_current_datetime() -> Dict[str, str]:
        """
        Get the current date and time.
        
        Returns:
            Dictionary with current date and time information
        """
        tool_message_print("Getting current date and time")
        
        try:        
            now = datetime.datetime.now()
            utc_now = datetime.datetime.utcnow()
            
            return {
                "local_datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                "utc_datetime": utc_now.strftime("%Y-%m-%d %H:%M:%S"),
                "local_date": now.strftime("%Y-%m-%d"),
                "local_time": now.strftime("%H:%M:%S"),
                "timezone": time.tzname[0],
                "timestamp": int(time.time())
            }
            
        except Exception as e:
            raise PluginError(f"Error getting current datetime: {e}", plugin_name=SystemPlugin.__name__) from e
    
    @staticmethod
    @tool(
        categories=["system", "env"]
    )
    def get_environment_variable(variable_name: str) -> Dict[str, Any]:
        """
        Get the value of an environment variable.
        
        Args:
            variable_name: Name of the environment variable
            
        Returns:
            Dictionary with the variable name and value
        """
        tool_message_print(f"Getting environment variable: {variable_name}")
        
        try:
            value = os.environ.get(variable_name)
            
            if value is not None:
                # Mask sensitive values
                if any(keyword in variable_name.lower() for keyword in ['token', 'key', 'secret', 'password', 'credential']):
                    return {
                        "name": variable_name,
                        "exists": True,
                        "value": "[REDACTED]"
                    }
                else:
                    return {
                        "name": variable_name,
                        "exists": True,
                        "value": value
                    }
            else:
                return {
                    "name": variable_name,
                    "exists": False,
                    "value": None
                }
                
        except Exception as e:
            raise PluginError(f"Error getting environment variable: {e}", plugin_name=SystemPlugin.__name__) from e
    
    @staticmethod
    @tool(
        categories=["system", "shell"],
        requires_filesystem=True
    )
    def run_parallel_commands(commands: List[str], timeout: int = 30) -> List[Dict[str, Any]]:
        """
        Run multiple shell commands in parallel.
        
        Args:
            commands: List of shell commands to execute
            timeout: Command timeout in seconds (default: 30)
            
        Returns:
            List of dictionaries with stdout, stderr, and return code for each command
        """
        tool_message_print(f"Running {len(commands)} commands in parallel")
        
        def run_command(cmd):
            try:
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                try:
                    stdout, stderr = process.communicate(timeout=timeout)
                    return {
                        "command": cmd,
                        "stdout": stdout,
                        "stderr": stderr,
                        "returncode": process.returncode
                    }
                except subprocess.TimeoutExpired:
                    process.kill()
                    return {
                        "command": cmd,
                        "error": f"Command timed out after {timeout} seconds",
                        "returncode": -1
                    }
            except Exception as e:
                return {
                    "command": cmd,
                    "error": str(e),
                    "returncode": -1
                }
        
        try:
            # Use ThreadPoolExecutor to run commands in parallel
            results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(commands), 5)) as executor:
                futures = [executor.submit(run_command, cmd) for cmd in commands]
                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())
                    
            return results
            
        except Exception as e:
            raise PluginError(f"Error running parallel commands: {e}", plugin_name=SystemPlugin.__name__) from e
