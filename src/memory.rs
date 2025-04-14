use std::time::{SystemTime, UNIX_EPOCH};
use std::collections::HashMap;
use std::thread;
use std::time::Duration;
use std::alloc::{alloc, dealloc, Layout};

#[derive(Serialize, Deserialize, Debug)]
pub struct MemoryStats {
    pub total: u64,       // Total physical memory in bytes
    pub free: u64,        // Free physical memory in bytes
    pub available: u64,   // Available memory in bytes
    pub used: u64,        // Used physical memory in bytes
    pub used_percent: f64, // Used memory as a percentage
    pub buffers: Option<u64>, // Memory used for buffers (Linux specific)
    pub cached: Option<u64>,  // Memory used for cache (Linux specific)
    pub timestamp: String,    // ISO8601 timestamp
}

/// Get current memory statistics.
pub fn get_memory_stats() -> MemoryStats {
    #[cfg(target_os = "linux")]
    return get_memory_stats_linux();
    
    #[cfg(target_os = "macos")]
    return get_memory_stats_macos();
    
    #[cfg(target_os = "windows")]
    return get_memory_stats_windows();
    
    // Default implementation for unsupported platforms
    #[cfg(not(any(target_os = "linux", target_os = "macos", target_os = "windows")))]
    return MemoryStats {
        total: 0,
        free: 0,
        available: 0,
        used: 0,
        used_percent: 0.0,
        buffers: None,
        cached: None,
        timestamp: format_timestamp(),
    };
}

/// Format current time as ISO8601 timestamp.
fn format_timestamp() -> String {
    match SystemTime::now().duration_since(UNIX_EPOCH) {
        Ok(duration) => {
            let secs = duration.as_secs();
            let millis = duration.subsec_millis();
            
            // Format as ISO8601
            let datetime = chrono::NaiveDateTime::from_timestamp(secs as i64, millis * 1_000_000);
            datetime.format("%Y-%m-%dT%H:%M:%S%.3fZ").to_string()
        },
        Err(_) => String::from("1970-01-01T00:00:00.000Z"),
    }
}

/// Get memory statistics on Linux.
#[cfg(target_os = "linux")]
fn get_memory_stats_linux() -> MemoryStats {
    use std::fs::File;
    use std::io::{BufRead, BufReader};
    
    let mut mem_info = HashMap::new();
    
    // Read /proc/meminfo for memory information
    if let Ok(file) = File::open("/proc/meminfo") {
        let reader = BufReader::new(file);
        
        for line in reader.lines() {
            if let Ok(line) = line {
                let parts: Vec<&str> = line.split(':').collect();
                if parts.len() == 2 {
                    let key = parts[0].trim();
                    let value_parts: Vec<&str> = parts[1].trim().split_whitespace().collect();
                    
                    if !value_parts.is_empty() {
                        if let Ok(value) = value_parts[0].parse::<u64>() {
                            let value_in_bytes = if value_parts.len() > 1 && value_parts[1].to_lowercase() == "kb" {
                                value * 1024 // Convert KB to bytes
                            } else {
                                value
                            };
                            
                            mem_info.insert(key.to_string(), value_in_bytes);
                        }
                    }
                }
            }
        }
    }
    
    // Extract values from the map
    let total = mem_info.get("MemTotal").cloned().unwrap_or(0);
    let free = mem_info.get("MemFree").cloned().unwrap_or(0);
    let available = mem_info.get("MemAvailable").cloned().unwrap_or(free);
    let buffers = mem_info.get("Buffers").cloned();
    let cached = mem_info.get("Cached").cloned();
    
    // Calculate used memory
    let used = if let (Some(buffers_val), Some(cached_val)) = (buffers, cached) {
        total - free - buffers_val - cached_val
    } else {
        total - free
    };
    
    // Calculate percentage
    let used_percent = if total > 0 {
        (used as f64 / total as f64) * 100.0
    } else {
        0.0
    };
    
    MemoryStats {
        total,
        free,
        available,
        used,
        used_percent,
        buffers,
        cached,
        timestamp: format_timestamp(),
    }
}

/// Get memory statistics on macOS.
#[cfg(target_os = "macos")]
fn get_memory_stats_macos() -> MemoryStats {
    use std::process::Command;
    
    let mut total: u64 = 0;
    let mut free: u64 = 0;
    let mut active: u64 = 0;
    let mut inactive: u64 = 0;
    let mut speculative: u64 = 0;
    
    // Get total memory using sysctl
    if let Ok(output) = Command::new("sysctl").args(&["-n", "hw.memsize"]).output() {
        if let Ok(output_str) = String::from_utf8(output.stdout) {
            if let Ok(value) = output_str.trim().parse::<u64>() {
                total = value;
            }
        }
    }
    
    // Get memory statistics using vm_stat
    if let Ok(output) = Command::new("vm_stat").output() {
        if let Ok(output_str) = String::from_utf8(output.stdout) {
            let page_size: u64 = 4096; // Default page size in bytes
            
            for line in output_str.lines() {
                let parts: Vec<&str> = line.split(':').collect();
                if parts.len() == 2 {
                    let key = parts[0].trim();
                    let value_str = parts[1].trim().trim_end_matches('.');
                    
                    if let Ok(value) = value_str.parse::<u64>() {
                        match key {
                            "Pages free" => free = value * page_size,
                            "Pages active" => active = value * page_size,
                            "Pages inactive" => inactive = value * page_size,
                            "Pages speculative" => speculative = value * page_size,
                            _ => {}
                        }
                    }
                }
            }
        }
    }
    
    // Calculate available memory (free + inactive)
    let available = free + inactive;
    
    // Calculate used memory
    let used = total - available;
    
    // Calculate percentage
    let used_percent = if total > 0 {
        (used as f64 / total as f64) * 100.0
    } else {
        0.0
    };
    
    MemoryStats {
        total,
        free,
        available,
        used,
        used_percent,
        buffers: None,
        cached: None,
        timestamp: format_timestamp(),
    }
}

/// Get memory statistics on Windows.
#[cfg(target_os = "windows")]
fn get_memory_stats_windows() -> MemoryStats {
    use winapi::um::sysinfoapi::{GlobalMemoryStatusEx, MEMORYSTATUSEX};
    use winapi::um::winnt::DWORD;
    
    let mut memory_status = MEMORYSTATUSEX {
        dwLength: std::mem::size_of::<MEMORYSTATUSEX>() as DWORD,
        dwMemoryLoad: 0,
        ullTotalPhys: 0,
        ullAvailPhys: 0,
        ullTotalPageFile: 0,
        ullAvailPageFile: 0,
        ullTotalVirtual: 0,
        ullAvailVirtual: 0,
        ullAvailExtendedVirtual: 0,
    };
    
    unsafe {
        if GlobalMemoryStatusEx(&mut memory_status) == 0 {
            // Error getting memory status
            return MemoryStats {
                total: 0,
                free: 0,
                available: 0,
                used: 0,
                used_percent: 0.0,
                buffers: None,
                cached: None,
                timestamp: format_timestamp(),
            };
        }
    }
    
    let total = memory_status.ullTotalPhys;
    let available = memory_status.ullAvailPhys;
    let free = available; // On Windows, free is the same as available
    let used = total - available;
    let used_percent = memory_status.dwMemoryLoad as f64;
    
    MemoryStats {
        total,
        free,
        available,
        used,
        used_percent,
        buffers: None,
        cached: None,
        timestamp: format_timestamp(),
    }
}

/// Release memory cache to free up memory.
pub fn release_memory_cache() -> bool {
    #[cfg(target_os = "linux")]
    return release_memory_cache_linux();
    
    #[cfg(target_os = "macos")]
    return release_memory_cache_macos();
    
    #[cfg(target_os = "windows")]
    return release_memory_cache_windows();
    
    // Default implementation for unsupported platforms
    #[cfg(not(any(target_os = "linux", target_os = "macos", target_os = "windows")))]
    return false;
}

/// Release memory cache on Linux.
#[cfg(target_os = "linux")]
fn release_memory_cache_linux() -> bool {
    use std::process::Command;
    use std::fs::File;
    use std::io::Write;
    
    // First, sync to disk to ensure data is safe
    let sync_result = Command::new("sync").status();
    
    // Try to drop caches
    let drop_caches_result = File::create("/proc/sys/vm/drop_caches")
        .and_then(|mut file| file.write_all(b"3"))
        .is_ok();
    
    sync_result.is_ok() || drop_caches_result
}

/// Release memory cache on macOS.
#[cfg(target_os = "macos")]
fn release_memory_cache_macos() -> bool {
    use std::process::Command;
    
    // On macOS, the purge command can clear inactive memory
    Command::new("purge").status().is_ok()
}

/// Release memory cache on Windows.
#[cfg(target_os = "windows")]
fn release_memory_cache_windows() -> bool {
    use winapi::um::processthreadsapi::GetCurrentProcess;
    use winapi::um::psapi::EmptyWorkingSet;
    
    // On Windows, we can empty the working set of the current process
    unsafe {
        let handle = GetCurrentProcess();
        EmptyWorkingSet(handle) != 0
    }
}

/// Simulate memory fragmentation for testing purposes.
pub fn simulate_memory_fragmentation(count: i32, size_kb: i32) -> bool {
    // Vector to hold allocations
    let mut allocations = Vec::new();
    let size = (size_kb as usize) * 1024;
    
    // Perform allocations in a pattern that tends to cause fragmentation
    for i in 0..count {
        // Create a layout for our allocation
        let layout = Layout::from_size_align(size, 64).unwrap();
        
        unsafe {
            // Allocate memory
            let ptr = alloc(layout);
            if !ptr.is_null() {
                // Write some data to ensure it's actually allocated
                for j in 0..size.min(1024) {
                    *ptr.add(j) = (i % 255) as u8;
                }
                
                // Store the allocation if we'll keep some
                if i % 3 != 0 {
                    allocations.push((ptr, layout));
                } else {
                    // Free immediately to create fragmentation
                    dealloc(ptr, layout);
                }
            }
        }
        
        // Short sleep to make it more realistic
        if i % 10 == 0 {
            thread::sleep(Duration::from_millis(1));
        }
    }
    
    // Free remaining allocations
    for (ptr, layout) in allocations {
        unsafe {
            dealloc(ptr, layout);
        }
    }
    
    true
}

/// Perform memory defragmentation.
/// 
/// Note: This is a simulated function since true memory defragmentation
/// is typically handled by the operating system or memory allocator.
pub fn defragment_memory() -> bool {
    // In a real implementation, this might:
    // 1. Compact memory if the allocator supports it
    // 2. Call OS-specific memory compaction functions
    // 3. Perform application-specific optimizations
    
    // For now, we'll simulate the operation with a small delay
    thread::sleep(Duration::from_millis(500));
    
    // Report success
    true
}
