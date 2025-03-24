"""
System information utilities for gathering detailed system status.
Provides comprehensive information about hardware, software, and resource usage.
"""

import os
import platform
import sys
import subprocess
import socket
import json
import datetime
from typing import Dict, Any, List, Optional, Tuple

# Handle optional dependencies
PSUTIL_AVAILABLE = False
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    pass

from .core import tool_message_print, tool_report_print

class SystemInfoCollector:
    """Collects comprehensive system information."""
    
    @staticmethod
    def get_basic_system_info() -> Dict[str, Any]:
        """Collect basic system information available on all platforms."""
        info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "hostname": socket.gethostname(),
            "python_version": platform.python_version(),
            "date_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        return info
        
    @staticmethod
    def get_advanced_system_info() -> Dict[str, Any]:
        """Collect advanced system information using psutil if available."""
        if not PSUTIL_AVAILABLE:
            return {"psutil_available": False}
            
        info = {}
        
        # CPU information
        info["cpu_count_physical"] = psutil.cpu_count(logical=False)
        info["cpu_count_logical"] = psutil.cpu_count(logical=True)
        info["cpu_percent"] = psutil.cpu_percent(interval=1)
        
        # Memory information
        memory = psutil.virtual_memory()
        info["memory_total"] = memory.total
        info["memory_available"] = memory.available
        info["memory_percent_used"] = memory.percent
        
        # Disk information
        disk = psutil.disk_usage('/')
        info["disk_total"] = disk.total
        info["disk_used"] = disk.used
        info["disk_free"] = disk.free
        info["disk_percent_used"] = disk.percent
        
        # Network information
        info["network_interfaces"] = list(psutil.net_if_addrs().keys())
        
        # Process information
        info["process_count"] = len(list(psutil.process_iter()))
        
        # Boot time
        info["boot_time"] = datetime.datetime.fromtimestamp(
            psutil.boot_time()
        ).strftime("%Y-%m-%d %H:%M:%S")
        
        # Load average (Unix/Linux/Mac only)
        try:
            info["load_average"] = os.getloadavg()
        except (AttributeError, OSError):
            info["load_average"] = None
            
        return info
        
    @staticmethod
    def get_detailed_cpu_info() -> Dict[str, Any]:
        """Get detailed CPU information based on the platform."""
        info = {"vendor": "Unknown", "model": "Unknown", "cores": "Unknown"}
        system = platform.system()
        
        try:
            if system == "Linux":
                # Using lscpu on Linux
                output = subprocess.check_output("lscpu", shell=True).decode()
                for line in output.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        if "vendor" in key.lower():
                            info["vendor"] = value
                        elif "model name" in key.lower():
                            info["model"] = value
                        elif "cpu(s)" == key.lower():
                            info["cores"] = value
                            
            elif system == "Darwin":  # macOS
                # Using sysctl on macOS
                info["vendor"] = subprocess.check_output("sysctl -n machdep.cpu.vendor", shell=True).decode().strip()
                info["model"] = subprocess.check_output("sysctl -n machdep.cpu.brand_string", shell=True).decode().strip()
                info["cores"] = subprocess.check_output("sysctl -n hw.physicalcpu", shell=True).decode().strip()
                
            elif system == "Windows":
                # Using wmic on Windows
                info["model"] = subprocess.check_output("wmic cpu get name", shell=True).decode().strip().split("\n")[1]
                info["vendor"] = subprocess.check_output("wmic cpu get manufacturer", shell=True).decode().strip().split("\n")[1]
                info["cores"] = subprocess.check_output("wmic cpu get numberofcores", shell=True).decode().strip().split("\n")[1]
        except Exception:
            # Fallback to platform module info
            info["model"] = platform.processor()
            
        return info
    
    @staticmethod
    def get_resource_usage() -> Dict[str, Any]:
        """Get current resource usage of the system."""
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not available"}
            
        # Get top processes by memory and CPU usage
        processes_by_memory = []
        processes_by_cpu = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
                info = proc.info
                process_data = {
                    "pid": info['pid'],
                    "name": info['name'],
                    "username": info['username'],
                    "memory_percent": round(info['memory_percent'], 2),
                    "cpu_percent": round(info['cpu_percent'], 2)
                }
                processes_by_memory.append(process_data)
                processes_by_cpu.append(process_data)
                
            # Sort and limit to top 10
            processes_by_memory.sort(key=lambda x: x['memory_percent'], reverse=True)
            processes_by_cpu.sort(key=lambda x: x['cpu_percent'], reverse=True)
            
            top_memory_processes = processes_by_memory[:10]
            top_cpu_processes = processes_by_cpu[:10]
            
            return {
                "system_cpu_percent": psutil.cpu_percent(),
                "system_memory_percent": psutil.virtual_memory().percent,
                "system_disk_percent": psutil.disk_usage('/').percent,
                "top_memory_processes": top_memory_processes,
                "top_cpu_processes": top_cpu_processes
            }
        except Exception as e:
            return {"error": f"Failed to get resource usage: {str(e)}"}
            
    @staticmethod
    def get_network_stats() -> Dict[str, Any]:
        """Get detailed network statistics."""
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not available"}
            
        try:
            # Get network IO counters
            net_io = psutil.net_io_counters(pernic=True)
            net_stats = {}
            
            for interface, stats in net_io.items():
                net_stats[interface] = {
                    "bytes_sent": stats.bytes_sent,
                    "bytes_recv": stats.bytes_recv,
                    "packets_sent": stats.packets_sent,
                    "packets_recv": stats.packets_recv,
                    "errin": getattr(stats, "errin", 0),
                    "errout": getattr(stats, "errout", 0),
                    "dropin": getattr(stats, "dropin", 0),
                    "dropout": getattr(stats, "dropout", 0)
                }
                
            # Get network connection information
            connections = []
            for conn in psutil.net_connections(kind='inet'):
                connection_info = {
                    "fd": conn.fd,
                    "family": conn.family,
                    "type": conn.type,
                    "local_addr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                    "remote_addr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    "status": conn.status,
                    "pid": conn.pid
                }
                connections.append(connection_info)
                
            return {
                "interfaces": net_stats,
                "connections": connections[:20]  # Limit to avoid excessive output
            }
        except Exception as e:
            return {"error": f"Failed to get network statistics: {str(e)}"}
            
    @staticmethod
    def format_bytes(bytes_val: int) -> str:
        """Format bytes into human-readable format."""
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        value = bytes_val
        
        while value >= 1024 and unit_index < len(units) - 1:
            value /= 1024
            unit_index += 1
            
        return f"{value:.2f} {units[unit_index]}"

    @staticmethod
    def get_installed_software() -> Dict[str, Any]:
        """Get list of installed software (platform-specific)."""
        system = platform.system()
        software_list = []
        
        try:
            if system == "Windows":
                # Get installed software on Windows using WMIC
                output = subprocess.check_output("wmic product get name,version", shell=True).decode('utf-8', errors='ignore')
                for line in output.strip().split('\n')[1:]:
                    parts = line.strip().split()
                    if parts:
                        # Extract version (last part) and name (everything else)
                        if len(parts) > 1:
                            version = parts[-1]
                            name = ' '.join(parts[:-1])
                            software_list.append({"name": name, "version": version})
                            
            elif system == "Linux":
                # Get installed packages on Linux using dpkg (Debian/Ubuntu) or rpm (Red Hat/Fedora)
                if os.path.exists("/usr/bin/dpkg"):
                    output = subprocess.check_output("dpkg-query -W -f='${Package} ${Version}\n'", shell=True).decode('utf-8', errors='ignore')
                    for line in output.strip().split('\n'):
                        if line:
                            parts = line.split()
                            if len(parts) >= 2:
                                name = parts[0]
                                version = parts[1]
                                software_list.append({"name": name, "version": version})
                elif os.path.exists("/usr/bin/rpm"):
                    output = subprocess.check_output("rpm -qa --queryformat '%{NAME} %{VERSION}\n'", shell=True).decode('utf-8', errors='ignore')
                    for line in output.strip().split('\n'):
                        if line:
                            parts = line.split()
                            if len(parts) >= 2:
                                name = parts[0]
                                version = parts[1]
                                software_list.append({"name": name, "version": version})
                                
            elif system == "Darwin":  # macOS
                # Get installed apps on macOS
                output = subprocess.check_output("ls -la /Applications", shell=True).decode('utf-8', errors='ignore')
                for line in output.strip().split('\n'):
                    if line.endswith('.app'):
                        name = line.split('/')[-1]
                        software_list.append({"name": name, "version": "N/A"})
                        
            return {
                "system": system,
                "software_count": len(software_list),
                "software": software_list[:50]  # Limit to avoid excessive output
            }
        except Exception as e:
            return {"error": f"Failed to get installed software: {str(e)}"}

# Export a helper function for getting a formatted system info report
def get_system_info_report(include_processes: bool = False) -> str:
    """
    Get a comprehensive system information report formatted as text.
    
    Args:
        include_processes: Whether to include process information
        
    Returns:
        Formatted system information report
    """
    collector = SystemInfoCollector()
    
    # Collect all information
    basic_info = collector.get_basic_system_info()
    
    # Format the report
    report = []
    report.append("# System Information Report")
    report.append(f"Generated: {basic_info['date_time']}")
    report.append("")
    
    report.append("## Basic System Information")
    report.append(f"- Platform: {basic_info['platform']} {basic_info['platform_release']} {basic_info['platform_version']}")
    report.append(f"- Architecture: {basic_info['architecture']}")
    report.append(f"- Processor: {basic_info['processor']}")
    report.append(f"- Hostname: {basic_info['hostname']}")
    report.append(f"- Python Version: {basic_info['python_version']}")
    report.append("")
    
    # Add advanced info if psutil is available
    if PSUTIL_AVAILABLE:
        advanced_info = collector.get_advanced_system_info()
        cpu_info = collector.get_detailed_cpu_info()
        
        report.append("## CPU Information")
        report.append(f"- Vendor: {cpu_info['vendor']}")
        report.append(f"- Model: {cpu_info['model']}")
        report.append(f"- Physical Cores: {advanced_info.get('cpu_count_physical', 'Unknown')}")
        report.append(f"- Logical Cores: {advanced_info.get('cpu_count_logical', 'Unknown')}")
        report.append(f"- Current Usage: {advanced_info.get('cpu_percent', 'Unknown')}%")
        report.append("")
        
        report.append("## Memory Information")
        report.append(f"- Total Memory: {collector.format_bytes(advanced_info.get('memory_total', 0))}")
        report.append(f"- Available Memory: {collector.format_bytes(advanced_info.get('memory_available', 0))}")
        report.append(f"- Memory Usage: {advanced_info.get('memory_percent_used', 'Unknown')}%")
        report.append("")
        
        report.append("## Disk Information")
        report.append(f"- Total Disk Space: {collector.format_bytes(advanced_info.get('disk_total', 0))}")
        report.append(f"- Used Disk Space: {collector.format_bytes(advanced_info.get('disk_used', 0))}")
        report.append(f"- Free Disk Space: {collector.format_bytes(advanced_info.get('disk_free', 0))}")
        report.append(f"- Disk Usage: {advanced_info.get('disk_percent_used', 'Unknown')}%")
        report.append("")
        
        report.append("## Network Information")
        report.append(f"- Network Interfaces: {', '.join(advanced_info.get('network_interfaces', ['Unknown']))}")
        report.append("")
        
        # Add process information if requested
        if include_processes:
            resources = collector.get_resource_usage()
            
            report.append("## Top CPU Processes")
            for proc in resources.get("top_cpu_processes", []):
                report.append(f"- {proc['name']} (PID: {proc['pid']}): {proc['cpu_percent']}% CPU")
            report.append("")
            
            report.append("## Top Memory Processes")
            for proc in resources.get("top_memory_processes", []):
                report.append(f"- {proc['name']} (PID: {proc['pid']}): {proc['memory_percent']}% Memory")
            report.append("")
    else:
        report.append("## Advanced Information")
        report.append("(psutil not available - install using: 'uv pip install psutil' for detailed system information)")
        report.append("")
    
    return "\n".join(report)
