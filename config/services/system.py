"""
System information service.
"""
import platform
import os
import sys
import psutil
from typing import Dict, Any, Optional
from dataclasses import dataclass
import datetime

@dataclass
class SystemInfo:
    """System information container."""
    os_name: str
    os_version: str
    python_version: str
    cpu_count: int
    memory_total: int
    memory_available: int
    disk_total: int
    disk_free: int
    timezone: str
    encoding: str

    @property
    def formatted(self) -> str:
        """Get formatted system information string."""
        memory_gb = self.memory_total / (1024 * 1024 * 1024)
        disk_gb = self.disk_total / (1024 * 1024 * 1024)
        
        return (
            f"System: {self.os_name} {self.os_version}\n"
            f"Python: {self.python_version}\n"
            f"CPU Cores: {self.cpu_count}\n"
            f"Memory: {memory_gb:.1f} GB total\n"
            f"Disk: {disk_gb:.1f} GB total\n"
            f"Timezone: {self.timezone}\n"
            f"Encoding: {self.encoding}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format.
        
        Returns:
            Dictionary of system information
        """
        return {
            "os_name": self.os_name,
            "os_version": self.os_version,
            "python_version": self.python_version,
            "cpu_count": self.cpu_count,
            "memory_total": self.memory_total,
            "memory_available": self.memory_available,
            "disk_total": self.disk_total,
            "disk_free": self.disk_free,
            "timezone": self.timezone,
            "encoding": self.encoding
        }

class SystemService:
    """Service for accessing system information."""
    
    def __init__(self):
        """Initialize system service."""
        self._info_cache: SystemInfo = None
        self._last_update: float = 0
        self._cache_ttl = 60  # Cache for 60 seconds
        
    def get_system_info(self, force_refresh: bool = False) -> SystemInfo:
        """Get system information, optionally forcing a refresh.
        
        Args:
            force_refresh: Whether to force refresh cached data
            
        Returns:
            SystemInfo instance
        """
        current_time = datetime.datetime.now().timestamp()
        if (
            self._info_cache is None 
            or force_refresh 
            or current_time - self._last_update > self._cache_ttl
        ):
            self._info_cache = self._collect_system_info()
            self._last_update = current_time
        return self._info_cache
        
    def _collect_system_info(self) -> SystemInfo:
        """Collect current system information.
        
        Returns:
            SystemInfo instance
        """
        return SystemInfo(
            os_name=platform.system(),
            os_version=platform.release(),
            python_version=platform.python_version(),
            cpu_count=psutil.cpu_count(),
            memory_total=psutil.virtual_memory().total,
            memory_available=psutil.virtual_memory().available,
            disk_total=psutil.disk_usage('/').total,
            disk_free=psutil.disk_usage('/').free,
            timezone=datetime.datetime.now().astimezone().tzname(),
            encoding=sys.getdefaultencoding()
        )
        
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage information.
        
        Returns:
            Dictionary containing memory usage details
        """
        vm = psutil.virtual_memory()
        return {
            "total_gb": vm.total / (1024 * 1024 * 1024),
            "available_gb": vm.available / (1024 * 1024 * 1024),
            "used_gb": (vm.total - vm.available) / (1024 * 1024 * 1024),
            "percent": vm.percent
        }
        
    def get_disk_usage(self, path: str = '/') -> Dict[str, float]:
        """Get disk usage information for a path.
        
        Args:
            path: Path to check disk usage for
            
        Returns:
            Dictionary containing disk usage details
        """
        du = psutil.disk_usage(path)
        return {
            "total_gb": du.total / (1024 * 1024 * 1024),
            "free_gb": du.free / (1024 * 1024 * 1024),
            "used_gb": du.used / (1024 * 1024 * 1024),
            "percent": du.percent
        }
        
    def get_cpu_usage(self, interval: float = 0.1) -> float:
        """Get current CPU usage percentage.
        
        Args:
            interval: Time period over which to measure CPU usage
            
        Returns:
            CPU usage percentage
        """
        return psutil.cpu_percent(interval=interval)

    def get_process_info(self) -> Dict[str, Any]:
        """Get information about the current process.
        
        Returns:
            Dictionary containing process information
        """
        process = psutil.Process()
        return {
            "pid": process.pid,
            "memory_mb": process.memory_info().rss / (1024 * 1024),
            "cpu_percent": process.cpu_percent(),
            "threads": process.num_threads(),
            "open_files": len(process.open_files()),
            "start_time": datetime.datetime.fromtimestamp(
                process.create_time()
            ).isoformat()
        }

# Global instance
_system_service: Optional[SystemService] = None

def get_system_service() -> SystemService:
    """Get or create SystemService singleton.
    
    Returns:
        SystemService instance
    """
    global _system_service
    if _system_service is None:
        _system_service = SystemService()
    return _system_service

# For backwards compatibility
def get_system_info_string() -> str:
    """Get formatted system information string.
    
    Returns:
        Formatted system information
    """
    service = get_system_service()
    return service.get_system_info().formatted
