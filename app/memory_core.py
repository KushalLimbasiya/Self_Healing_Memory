import gc
import logging
import psutil
from datetime import datetime

logger = logging.getLogger(__name__)


def get_memory_stats() -> dict:
    """
    Get current system memory statistics using psutil.
    Cross-platform: works on Windows, Linux, macOS.
    """
    try:
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            "total":        vm.total,
            "available":    vm.available,
            "used":         vm.used,
            "free":         vm.free,
            "used_percent": vm.percent,
            "swap_total":   swap.total,
            "swap_used":    swap.used,
            "swap_percent": swap.percent,
            "timestamp":    datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        return {
            "total": 0, "available": 0, "used": 0, "free": 0,
            "used_percent": 0, "swap_total": 0, "swap_used": 0,
            "swap_percent": 0,
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
        }


def get_top_processes(limit: int = 5) -> list:
    """
    Return top memory-consuming processes (name + memory %).
    """
    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "memory_percent"]):
            try:
                procs.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        procs.sort(key=lambda x: x.get("memory_percent", 0), reverse=True)
        return procs[:limit]
    except Exception as e:
        logger.error(f"Error getting top processes: {e}")
        return []


def release_memory_cache() -> bool:
    """
    Release Python-managed memory via garbage collection.
    On Linux also attempts to drop OS page cache (requires root).
    """
    try:
        collected = gc.collect()
        logger.info(f"gc.collect() freed {collected} objects")
        return True
    except Exception as e:
        logger.error(f"Error releasing memory cache: {e}")
        return False


def simulate_memory_usage(usage_mb: int) -> bool:
    """
    Allocate `usage_mb` MB for 5 seconds, then release.
    Used for testing the monitor + healer agents.
    """
    import time
    try:
        data = [bytearray(1024 * 1024) for _ in range(usage_mb)]
        time.sleep(5)
        del data
        gc.collect()
        return True
    except Exception as e:
        logger.error(f"Error in memory simulation: {e}")
        return False
