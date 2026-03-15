"""
memory_core.py — OS-level memory statistics and healing.

Implements the same techniques used by professional RAM optimizers
(Wise Memory Optimizer, CleanMem, RAMMap) on Windows:

  1. Python GC (all 3 generations)
  2. Own-process working-set trim (fast)
  3. System-wide process trim   → iterate ALL PIDs via OpenProcess / EmptyWorkingSet
  4. Standby-list purge          → NtSetSystemInformation (requires admin)

On Linux: malloc_trim + (optional) /proc/sys/vm/drop_caches
"""
import ctypes
from ctypes import wintypes
import gc
import logging
import platform
import psutil
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Windows API constants ────────────────────────────────────────────────────
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_SET_QUOTA        = 0x0100
PROCESS_VM_OPERATION     = 0x0008

# SystemMemoryListInformation command codes
MemoryPurgeStandbyList   = 4   # flush standby (unused-but-cached) pages
MemoryFlushModifiedList  = 3   # flush modified (dirty) pages back to disk


# ── Stats ────────────────────────────────────────────────────────────────────

def get_memory_stats() -> dict:
    """Current system memory statistics including CPU usage."""
    try:
        vm   = psutil.virtual_memory()
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
        logger.error("Error getting memory stats: %s", e)
        return {
            "total": 0, "available": 0, "used": 0, "free": 0,
            "used_percent": 0, "swap_total": 0, "swap_used": 0,
            "swap_percent": 0, "cpu_percent": 0, "cpu_count": 0,
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
        }


def get_top_processes(limit: int = 8) -> list:
    """Return top memory-consuming processes with name, pid, memory MB and %."""
    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "memory_info", "memory_percent"]):
            try:
                info   = p.info
                mem_mb = round(info["memory_info"].rss / (1024 * 1024), 1) if info.get("memory_info") else 0
                procs.append({
                    "pid":     info["pid"],
                    "name":    info["name"],
                    "mem_mb":  mem_mb,
                    "mem_pct": round(info.get("memory_percent", 0), 2),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        procs.sort(key=lambda x: x["mem_mb"], reverse=True)
        return procs[:limit]
    except Exception as e:
        logger.error("Error getting top processes: %s", e)
        return []


# ── Core heal actions ────────────────────────────────────────────────────────

def release_memory_cache() -> bool:
    """
    Trim working set of THIS process only (fast, always safe).

    Used by the healer agent's clear_cache action.
    Returns True on success.
    """
    try:
        collected = gc.collect(2)
        logger.info("gc.collect(2): freed %d objects", collected)

        if platform.system() == "Windows":
            try:
                kernel32 = ctypes.windll.kernel32
                psapi    = ctypes.windll.psapi
                pid      = kernel32.GetCurrentProcess()
                kernel32.SetProcessWorkingSetSize(pid, ctypes.c_size_t(-1), ctypes.c_size_t(-1))
                psapi.EmptyWorkingSet(pid)
                logger.info("Windows working set trimmed (own process)")
            except Exception as win_err:
                logger.debug("Windows trim failed (non-fatal): %s", win_err)
        elif platform.system() == "Linux":
            try:
                ctypes.CDLL("libc.so.6").malloc_trim(0)
            except Exception:
                pass
        return True
    except Exception as e:
        logger.error("release_memory_cache error: %s", e)
        return False


def full_system_optimize() -> dict:
    """
    Deep system-wide memory optimization — mirrors professional RAM tools.

    Steps:
      1. Python GC
      2. Own-process working set trim
      3. Iterate ALL processes → OpenProcess → EmptyWorkingSet (CleanMem technique)
      4. (Windows admin only) Flush Standby list via NtSetSystemInformation

    Returns a dict with:
      freed_mb   – estimated MB freed
      trimmed    – number of processes successfully trimmed
      standby_flushed – whether the standby list was cleared
      errors     – list of non-fatal error strings
    """
    before_mb   = psutil.virtual_memory().used / (1024 * 1024)
    trimmed     = 0
    errors      = []
    standby_ok  = False

    # ── Step 1: GC ──────────────────────────────────────────────────────────
    collected = gc.collect(2)
    logger.info("[Optimizer] GC: freed %d objects", collected)

    sys = platform.system()

    if sys == "Windows":
        kernel32 = ctypes.windll.kernel32
        psapi    = ctypes.windll.psapi

        # ── Step 2: Own-process trim ────────────────────────────────────────
        own = kernel32.GetCurrentProcess()
        kernel32.SetProcessWorkingSetSize(own, ctypes.c_size_t(-1), ctypes.c_size_t(-1))
        psapi.EmptyWorkingSet(own)

        # ── Step 3: System-wide trim (CleanMem / Wise Memory Optimizer) ─────
        OPEN_FLAGS = PROCESS_SET_QUOTA | PROCESS_VM_OPERATION
        for proc in psutil.process_iter(["pid"]):
            try:
                pid = proc.info["pid"]
                if pid == 0:
                    continue  # skip System Idle
                hProc = kernel32.OpenProcess(OPEN_FLAGS, False, pid)
                if hProc:
                    kernel32.SetProcessWorkingSetSize(
                        hProc, ctypes.c_size_t(-1), ctypes.c_size_t(-1)
                    )
                    psapi.EmptyWorkingSet(hProc)
                    kernel32.CloseHandle(hProc)
                    trimmed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            except Exception as ex:
                errors.append(str(ex))

        logger.info("[Optimizer] Trimmed working sets for %d processes", trimmed)

        # ── Step 4: Standby list flush (admin required) ──────────────────────
        try:
            advapi32 = ctypes.windll.advapi32

            # SeProfileSingleProcessPrivilege is the required privilege for
            # NtSetSystemInformation / SystemMemoryListInformation
            SE_PRIVILEGE_NAME    = "SeProfileSingleProcessPrivilege"
            TOKEN_ADJUST_PRIVILEGES = 0x0020
            TOKEN_QUERY          = 0x0008
            SE_PRIVILEGE_ENABLED = 0x00000002

            class LUID(ctypes.Structure):
                _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]

            class LUID_AND_ATTRIBUTES(ctypes.Structure):
                _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]

            class TOKEN_PRIVILEGES(ctypes.Structure):
                _fields_ = [("PrivilegeCount", wintypes.DWORD),
                            ("Privileges", LUID_AND_ATTRIBUTES * 1)]

            hToken = wintypes.HANDLE()
            priv_ok = False
            if advapi32.OpenProcessToken(own, TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                         ctypes.byref(hToken)):
                luid = LUID()
                if advapi32.LookupPrivilegeValueW(None, SE_PRIVILEGE_NAME,
                                                  ctypes.byref(luid)):
                    tp = TOKEN_PRIVILEGES()
                    tp.PrivilegeCount = 1
                    tp.Privileges[0].Luid = luid
                    tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
                    
                    status = advapi32.AdjustTokenPrivileges(
                        hToken, False, ctypes.byref(tp), ctypes.sizeof(tp), None, None)
                    err = kernel32.GetLastError()
                    priv_ok = bool(status) and err == 0
                    
                kernel32.CloseHandle(hToken)

            logger.info("[Optimizer] SeProfileSingleProcessPrivilege acquired: %s", priv_ok)

            # Flush modified list first, then purge standby
            ntdll   = ctypes.windll.ntdll
            success = False
            for cmd_val in (MemoryFlushModifiedList, MemoryPurgeStandbyList):
                mem_cmd = ctypes.c_int(cmd_val)
                status  = ntdll.NtSetSystemInformation(
                    80,                    # SystemMemoryListInformation
                    ctypes.byref(mem_cmd),
                    ctypes.sizeof(mem_cmd),
                )
                nts = status & 0xFFFFFFFF
                logger.info("[Optimizer] NtSetSystemInfo cmd=%d → NTSTATUS=0x%08X", cmd_val, nts)
                if nts == 0:
                    success = True

            if success:
                standby_ok = True
                logger.info("[Optimizer] Standby list flushed successfully")
            else:
                errors.append("Standby flush failed — run Python as Administrator (UAC elevated).")
        except Exception as e:
            logger.debug("[Optimizer] Standby flush not available: %s", e)

    elif sys == "Linux":
        try:
            ctypes.CDLL("libc.so.6").malloc_trim(0)
            trimmed += 1
        except Exception as e:
            errors.append(str(e))

        # drop_caches requires root
        try:
            with open("/proc/sys/vm/drop_caches", "w") as f:
                f.write("3")
            standby_ok = True
            logger.info("[Optimizer] Linux drop_caches=3 applied")
        except Exception as e:
            logger.debug("[Optimizer] drop_caches not available (no root): %s", e)

    after_mb  = psutil.virtual_memory().used / (1024 * 1024)
    freed_mb  = round(before_mb - after_mb, 1)

    logger.info("[Optimizer] Complete: freed ~%.1f MB | trimmed=%d | standby=%s",
                freed_mb, trimmed, standby_ok)

    return {
        "freed_mb":       freed_mb,
        "trimmed":        trimmed,
        "standby_flushed": standby_ok,
        "before_mb":      round(before_mb, 1),
        "after_mb":       round(after_mb, 1),
        "errors":         errors[:5],   # cap error list
    }


def simulate_memory_usage(usage_mb: int) -> bool:
    """Allocate `usage_mb` MB for 5 s then release. Used for testing."""
    import time
    try:
        data = [bytearray(1024 * 1024) for _ in range(usage_mb)]
        time.sleep(5)
        del data
        gc.collect()
        return True
    except Exception as e:
        logger.error("Memory simulation error: %s", e)
        return False
