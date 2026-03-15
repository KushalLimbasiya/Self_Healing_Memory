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
            "cpu_percent":  psutil.cpu_percent(interval=None),
            "cpu_count":    psutil.cpu_count(logical=True),
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


def get_top_processes(limit: int = 8) -> list:
    """
    Return top memory-consuming processes with name, pid, memory MB and %.
    """
    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "memory_info", "memory_percent"]):
            try:
                info = p.info
                mem_mb = round(info["memory_info"].rss / (1024 * 1024), 1) if info.get("memory_info") else 0
                procs.append({
                    "pid":    info["pid"],
                    "name":   info["name"],
                    "mem_mb": mem_mb,
                    "mem_pct": round(info.get("memory_percent", 0), 2),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        procs.sort(key=lambda x: x["mem_mb"], reverse=True)
        return procs[:limit]
    except Exception as e:
        logger.error("Error getting top processes: %s", e)
        return []


def release_memory_cache() -> bool:
    """
    Release as much memory as possible to the OS.

    Strategy:
      1. Full GC (all 3 generations)
      2. Windows: SetProcessWorkingSetSize(-1,-1) + EmptyWorkingSet
         Linux:   malloc_trim via ctypes + drop_caches (requires root)
    """
    try:
        import platform
        import ctypes

        # 1. Full garbage collection across all generations
        collected = gc.collect(2)
        logger.info("gc.collect(2): freed %d objects", collected)

        sys_platform = platform.system()

        if sys_platform == "Windows":
            try:
                kernel32 = ctypes.windll.kernel32
                psapi    = ctypes.windll.psapi
                pid      = kernel32.GetCurrentProcess()

                # Trim working set of the current process
                # SetProcessWorkingSetSize(-1, -1) tells Windows to trim to minimum
                kernel32.SetProcessWorkingSetSize(pid, ctypes.c_size_t(-1), ctypes.c_size_t(-1))

                # EmptyWorkingSet flushes unmodified pages from working set
                psapi.EmptyWorkingSet(pid)

                logger.info("Windows working set trimmed")
            except Exception as win_err:
                logger.debug("Windows trim failed (non-fatal): %s", win_err)

        elif sys_platform == "Linux":
            try:
                ctypes.CDLL("libc.so.6").malloc_trim(0)
                logger.info("Linux malloc_trim performed")
            except Exception as lin_err:
                logger.debug("Linux malloc_trim failed (non-fatal): %s", lin_err)

        return True
    except Exception as e:
        logger.error("Error releasing memory cache: %s", e)
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
