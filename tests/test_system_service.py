"""
Tests for the system information service.
"""
import pytest
from typing import Dict
import platform
import psutil
from datetime import datetime
from unittest.mock import patch, Mock

from config.services.system import (
    SystemService,
    SystemInfo,
    get_system_service,
    get_system_info_string
)

@pytest.fixture
def system_service() -> SystemService:
    """Create a SystemService instance for testing."""
    return SystemService()

def test_system_info_creation():
    """Test creation of SystemInfo object."""
    info = SystemInfo(
        os_name="Test OS",
        os_version="1.0",
        python_version="3.9.0",
        cpu_count=4,
        memory_total=8589934592,  # 8GB
        memory_available=4294967296,  # 4GB
        disk_total=128849018880,  # 120GB
        disk_free=64424509440,  # 60GB
        timezone="UTC",
        encoding="utf-8"
    )
    
    # Test conversion to dictionary
    data = info.to_dict()
    assert data["os_name"] == "Test OS"
    assert data["python_version"] == "3.9.0"
    assert data["cpu_count"] == 4
    
    # Test formatted string
    formatted = info.formatted
    assert "Test OS 1.0" in formatted
    assert "Python: 3.9.0" in formatted
    assert "CPU Cores: 4" in formatted
    assert "8.0 GB total" in formatted

def test_system_info_collection(system_service: SystemService):
    """Test collecting real system information."""
    info = system_service.get_system_info()
    
    # Basic validation of collected data
    assert info.os_name == platform.system()
    assert info.python_version == platform.python_version()
    assert info.cpu_count > 0
    assert info.memory_total > 0
    assert info.disk_total > 0

def test_system_info_caching(system_service: SystemService):
    """Test system info caching behavior."""
    # Get initial info
    info1 = system_service.get_system_info()
    
    # Immediately get info again - should return cached version
    info2 = system_service.get_system_info()
    assert info1 is info2  # Should be same object instance
    
    # Force refresh
    info3 = system_service.get_system_info(force_refresh=True)
    assert info3 is not info1  # Should be new object instance

@patch('psutil.virtual_memory')
def test_memory_usage(mock_virtual_memory: Mock, system_service: SystemService):
    """Test memory usage information."""
    mock_vm = Mock()
    mock_vm.total = 8589934592  # 8GB
    mock_vm.available = 4294967296  # 4GB
    mock_vm.percent = 50.0
    mock_virtual_memory.return_value = mock_vm
    
    usage = system_service.get_memory_usage()
    
    assert usage["total_gb"] == 8.0
    assert usage["available_gb"] == 4.0
    assert usage["used_gb"] == 4.0
    assert usage["percent"] == 50.0

@patch('psutil.disk_usage')
def test_disk_usage(mock_disk_usage: Mock, system_service: SystemService):
    """Test disk usage information."""
    mock_usage = Mock()
    mock_usage.total = 128849018880  # 120GB
    mock_usage.free = 64424509440  # 60GB
    mock_usage.used = 64424509440  # 60GB
    mock_usage.percent = 50.0
    mock_disk_usage.return_value = mock_usage
    
    usage = system_service.get_disk_usage("/")
    
    assert usage["total_gb"] == 120.0
    assert usage["free_gb"] == 60.0
    assert usage["used_gb"] == 60.0
    assert usage["percent"] == 50.0

@patch('psutil.cpu_percent')
def test_cpu_usage(mock_cpu_percent: Mock, system_service: SystemService):
    """Test CPU usage information."""
    mock_cpu_percent.return_value = 25.5
    
    usage = system_service.get_cpu_usage()
    assert usage == 25.5
    mock_cpu_percent.assert_called_once_with(interval=0.1)

@patch('psutil.Process')
def test_process_info(mock_process: Mock, system_service: SystemService):
    """Test process information."""
    mock_proc = Mock()
    mock_proc.pid = 1234
    mock_proc.memory_info().rss = 104857600  # 100MB
    mock_proc.cpu_percent.return_value = 10.0
    mock_proc.num_threads.return_value = 4
    mock_proc.open_files.return_value = ["file1", "file2"]
    mock_proc.create_time.return_value = datetime.now().timestamp()
    mock_process.return_value = mock_proc
    
    info = system_service.get_process_info()
    
    assert info["pid"] == 1234
    assert info["memory_mb"] == 100.0
    assert info["cpu_percent"] == 10.0
    assert info["threads"] == 4
    assert info["open_files"] == 2
    assert "start_time" in info

def test_singleton_pattern():
    """Test system service singleton pattern."""
    service1 = get_system_service()
    service2 = get_system_service()
    assert service1 is service2

def test_backwards_compatibility():
    """Test backwards compatible system info string."""
    info_string = get_system_info_string()
    assert isinstance(info_string, str)
    assert "System:" in info_string
    assert "Python:" in info_string
    assert "CPU Cores:" in info_string
