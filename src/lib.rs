#[macro_use]
extern crate serde_derive;
extern crate serde;
extern crate serde_json;

use std::slice;
use std::ffi::CString;
use std::os::raw::c_char;

// Include the memory module
pub mod memory;

/// Get memory statistics as a JSON string.
/// 
/// # Returns
/// 
/// A C-compatible string containing memory statistics in JSON format.
/// The caller is responsible for freeing this memory.
#[no_mangle]
pub extern "C" fn get_memory_stats_json() -> *const c_char {
    let stats = memory::get_memory_stats();
    
    // Convert to JSON
    let json = match serde_json::to_string(&stats) {
        Ok(json_str) => json_str,
        Err(_) => String::from("{\"error\": \"Failed to serialize memory statistics\"}"),
    };
    
    // Convert to C string
    let c_str = match CString::new(json) {
        Ok(s) => s,
        Err(_) => CString::new("{\"error\": \"Failed to create C string\"}").unwrap(),
    };
    
    // Return the pointer - the caller is responsible for freeing this memory
    c_str.into_raw()
}

/// Release memory cache.
/// 
/// # Returns
/// 
/// 1 if successful, 0 otherwise.
#[no_mangle]
pub extern "C" fn release_memory_cache() -> i32 {
    match memory::release_memory_cache() {
        true => 1,
        false => 0,
    }
}

/// Free a C string previously returned by this library.
/// 
/// # Arguments
/// 
/// * `s` - Pointer to the C string to free.
#[no_mangle]
pub extern "C" fn free_string(s: *mut c_char) {
    unsafe {
        if s.is_null() {
            return;
        }
        let _ = CString::from_raw(s);
    }
}

/// Simulate memory fragmentation for testing purposes.
/// 
/// # Arguments
/// 
/// * `count` - Number of memory blocks to allocate and free.
/// * `size_kb` - Size of each memory block in kilobytes.
/// 
/// # Returns
/// 
/// 1 if successful, 0 otherwise.
#[no_mangle]
pub extern "C" fn simulate_memory_fragmentation(count: i32, size_kb: i32) -> i32 {
    match memory::simulate_memory_fragmentation(count, size_kb) {
        true => 1,
        false => 0,
    }
}

/// Perform memory defragmentation.
/// 
/// # Returns
/// 
/// 1 if successful, 0 otherwise.
#[no_mangle]
pub extern "C" fn defragment_memory() -> i32 {
    match memory::defragment_memory() {
        true => 1,
        false => 0,
    }
}
