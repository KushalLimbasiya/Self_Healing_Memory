import os
import logging
import ctypes
import subprocess
import platform
import json
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# Check if we can use the Rust library
try:
    # Try to load the Rust library if it exists
    lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "target/release/libmemory_core.so")
    
    if os.path.exists(lib_path):
        memory_lib = ctypes.CDLL(lib_path)
        
        # Define function argument and return types
        memory_lib.get_memory_stats_json.restype = ctypes.c_char_p
        
        logger.info("Loaded Rust memory core library")
        RUST_LIB_AVAILABLE = True
    else:
        logger.warning(f"Rust library not found at {lib_path}, using Python fallback")
        RUST_LIB_AVAILABLE = False
except Exception as e:
    logger.warning(f"Could not load Rust library: {str(e)}, using Python fallback")
    RUST_LIB_AVAILABLE = False

def get_memory_stats():
    """
    Get memory statistics from the system.
    
    Returns:
        Dictionary containing memory statistics
    """
    try:
        # Try to use the Rust library if available
        if RUST_LIB_AVAILABLE:
            json_data = memory_lib.get_memory_stats_json()
            stats = json.loads(json_data.decode('utf-8'))
            return stats
        
        # Fall back to Python implementation
        return _get_memory_stats_python()
    except Exception as e:
        logger.error(f"Error getting memory statistics: {str(e)}")
        # Return minimal stats on error
        return {
            "total": 0,
            "free": 0,
            "available": 0,
            "used": 0,
            "used_percent": 0,
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

def _get_memory_stats_python():
    """
    Python implementation of memory statistics collection.
    
    Returns:
        Dictionary containing memory statistics
    """
    system = platform.system().lower()
    
    try:
        if system == "linux":
            return _get_memory_stats_linux()
        elif system == "darwin":  # macOS
            return _get_memory_stats_mac()
        elif system == "windows":
            return _get_memory_stats_windows()
        else:
            raise Exception(f"Unsupported platform: {system}")
    except Exception as e:
        logger.error(f"Error in Python memory stats: {str(e)}")
        raise

def _get_memory_stats_linux():
    """Get memory statistics on Linux."""
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
            
        mem_info = {}
        for line in lines:
            parts = line.split(':')
            if len(parts) == 2:
                key = parts[0].strip()
                value_parts = parts[1].strip().split()
                value = int(value_parts[0])
                # Convert to bytes if unit is kB
                if len(value_parts) > 1 and value_parts[1].lower() == 'kb':
                    value *= 1024
                mem_info[key] = value
        
        total = mem_info.get('MemTotal', 0)
        free = mem_info.get('MemFree', 0)
        available = mem_info.get('MemAvailable', free)
        buffers = mem_info.get('Buffers', 0)
        cached = mem_info.get('Cached', 0)
        
        # Calculate used memory and percentage
        used = total - free - buffers - cached
        used_percent = (used / total) * 100 if total > 0 else 0
        
        return {
            "total": total,
            "free": free,
            "available": available,
            "used": used,
            "buffers": buffers,
            "cached": cached,
            "used_percent": used_percent,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting Linux memory stats: {str(e)}")
        raise

def _get_memory_stats_mac():
    """Get memory statistics on macOS."""
    try:
        # Use vm_stat command on macOS
        vm_stat = subprocess.run(['vm_stat'], stdout=subprocess.PIPE, text=True).stdout.strip().split('\n')
        
        # Parse vm_stat output
        memory_stats = {}
        for line in vm_stat[1:]:  # Skip the first line (header)
            parts = line.split(':')
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip().rstrip('.')
                try:
                    memory_stats[key] = int(value)
                except ValueError:
                    pass
        
        # Get page size
        page_size = 4096  # Default page size in bytes
        
        # Try to get total memory using sysctl
        total_memory = subprocess.run(['sysctl', '-n', 'hw.memsize'], stdout=subprocess.PIPE, text=True)
        total = int(total_memory.stdout.strip())
        
        # Calculate memory values
        free = memory_stats.get('Pages free', 0) * page_size
        inactive = memory_stats.get('Pages inactive', 0) * page_size
        available = free + inactive
        used = total - available
        used_percent = (used / total) * 100 if total > 0 else 0
        
        return {
            "total": total,
            "free": free,
            "available": available,
            "used": used,
            "inactive": inactive,
            "used_percent": used_percent,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting macOS memory stats: {str(e)}")
        raise

def _get_memory_stats_windows():
    """Get memory statistics on Windows."""
    try:
        # On Windows, use ctypes to call Windows API
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
            
        memory_status = MEMORYSTATUSEX()
        memory_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status))
        
        total = memory_status.ullTotalPhys
        available = memory_status.ullAvailPhys
        used = total - available
        used_percent = memory_status.dwMemoryLoad
        
        return {
            "total": total,
            "available": available,
            "used": used,
            "used_percent": used_percent,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting Windows memory stats: {str(e)}")
        raise

def release_memory_cache():
    """
    Release memory cache to free up memory.
    
    Returns:
        Boolean indicating if the operation was successful
    """
    try:
        # Try to use the Rust library if available
        if RUST_LIB_AVAILABLE and hasattr(memory_lib, 'release_memory_cache'):
            success = memory_lib.release_memory_cache()
            return success == 1
        
        # Fall back to Python implementation
        system = platform.system().lower()
        
        if system == "linux":
            # On Linux, sync and drop caches
            subprocess.run(['sync'], check=True)
            try:
                # This requires root privileges, might fail
                with open('/proc/sys/vm/drop_caches', 'w') as f:
                    f.write('3')
                return True
            except:
                logger.warning("Couldn't drop caches, might need root privileges")
                return False
        elif system == "darwin":  # macOS
            # On macOS, use purge (requires sudo)
            try:
                subprocess.run(['purge'], check=True)
                return True
            except:
                logger.warning("Couldn't run purge, might need sudo")
                return False
        elif system == "windows":
            # On Windows, call the garbage collector
            import gc
            gc.collect()
            return True
        else:
            logger.warning(f"Cache release not implemented for {system}")
            return False
            
    except Exception as e:
        logger.error(f"Error releasing memory cache: {str(e)}")
        return False

def simulate_memory_usage(usage_mb):
    """
    Simulate memory usage for testing.
    
    Args:
        usage_mb: Amount of memory to use in megabytes
        
    Returns:
        Boolean indicating if the simulation was successful
    """
    try:
        # Create a list of byte arrays to consume memory
        data = []
        for _ in range(usage_mb):
            # Allocate 1 MB
            data.append(bytearray(1024 * 1024))
        
        # Keep the memory allocated for a moment
        time.sleep(5)
        
        # Release the memory
        data = None
        
        return True
    except Exception as e:
        logger.error(f"Error simulating memory usage: {str(e)}")
        return False
