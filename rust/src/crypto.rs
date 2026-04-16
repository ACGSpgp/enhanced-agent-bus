//! ACGS-2 Enhanced Agent Bus - Cryptographic Utilities
//! Constitutional Hash: 608508a9bd224290
//!
//! Security-hardened cryptographic operations:
//! - Constant-time comparison to prevent timing attacks
//! - Memory zeroization for sensitive data
//! - Constitutional hash validation

use std::ops::Drop;
use zeroize::Zeroize;

/// Constitutional hash for ACGS-2 compliance
pub const CONSTITUTIONAL_HASH: &str = "608508a9bd224290";

/// Constant-time byte comparison to prevent timing attacks.
/// Returns true only if both slices have the same length and content.
#[inline]
pub fn constant_time_compare(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }

    // XOR all bytes and accumulate - constant time regardless of where mismatch occurs
    let mut result: u8 = 0;
    for (x, y) in a.iter().zip(b.iter()) {
        result |= x ^ y;
    }

    result == 0
}

/// Constant-time string comparison for hash validation.
#[inline]
pub fn constant_time_str_compare(a: &str, b: &str) -> bool {
    constant_time_compare(a.as_bytes(), b.as_bytes())
}

/// Validate constitutional hash with constant-time comparison.
/// Returns true if the provided hash matches the constitutional hash.
#[inline]
pub fn validate_constitutional_hash(hash: &str) -> bool {
    constant_time_str_compare(hash, CONSTITUTIONAL_HASH)
}

/// A wrapper for sensitive data that automatically zeros memory on drop.
/// Uses the zeroize crate for secure memory clearing.
#[derive(Clone)]
pub struct SecureBuffer {
    data: Vec<u8>,
}

impl SecureBuffer {
    /// Create a new secure buffer with the given capacity.
    pub fn with_capacity(capacity: usize) -> Self {
        Self {
            data: Vec::with_capacity(capacity),
        }
    }

    /// Create a secure buffer from existing data.
    /// The original data should be cleared after this call.
    pub fn from_vec(data: Vec<u8>) -> Self {
        Self { data }
    }

    /// Create a secure buffer from a slice (copies the data).
    pub fn from_slice(data: &[u8]) -> Self {
        Self {
            data: data.to_vec(),
        }
    }

    /// Get a reference to the underlying data.
    #[inline]
    pub fn as_slice(&self) -> &[u8] {
        &self.data
    }

    /// Get a mutable reference to the underlying data.
    #[inline]
    pub fn as_mut_slice(&mut self) -> &mut [u8] {
        &mut self.data
    }

    /// Get the length of the buffer.
    #[inline]
    pub fn len(&self) -> usize {
        self.data.len()
    }

    /// Check if the buffer is empty.
    #[inline]
    pub fn is_empty(&self) -> bool {
        self.data.is_empty()
    }

    /// Push a byte to the buffer.
    #[inline]
    pub fn push(&mut self, byte: u8) {
        self.data.push(byte);
    }

    /// Extend the buffer with bytes from a slice.
    #[inline]
    pub fn extend_from_slice(&mut self, slice: &[u8]) {
        self.data.extend_from_slice(slice);
    }

    /// Clear the buffer (zeros the memory before clearing).
    pub fn clear(&mut self) {
        self.data.zeroize();
        self.data.clear();
    }
}

impl Drop for SecureBuffer {
    fn drop(&mut self) {
        // Zero out memory before deallocation
        self.data.zeroize();
    }
}

impl std::fmt::Debug for SecureBuffer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        // Never print actual contents for security
        write!(f, "SecureBuffer([REDACTED; {} bytes])", self.data.len())
    }
}

/// Secure wrapper for a fixed-size key (e.g., Ed25519 private key).
#[derive(Clone)]
pub struct SecureKey<const N: usize> {
    bytes: [u8; N],
}

impl<const N: usize> SecureKey<N> {
    /// Create a new secure key from bytes.
    pub fn new(bytes: [u8; N]) -> Self {
        Self { bytes }
    }

    /// Create a secure key from a slice.
    /// Returns None if the slice length doesn't match N.
    pub fn from_slice(slice: &[u8]) -> Option<Self> {
        if slice.len() != N {
            return None;
        }
        let mut bytes = [0u8; N];
        bytes.copy_from_slice(slice);
        Some(Self { bytes })
    }

    /// Get a reference to the key bytes.
    #[inline]
    pub fn as_bytes(&self) -> &[u8; N] {
        &self.bytes
    }

    /// Get a reference as a slice.
    #[inline]
    pub fn as_slice(&self) -> &[u8] {
        &self.bytes
    }
}

impl<const N: usize> Drop for SecureKey<N> {
    fn drop(&mut self) {
        self.bytes.zeroize();
    }
}

impl<const N: usize> std::fmt::Debug for SecureKey<N> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "SecureKey<{}>([REDACTED])", N)
    }
}

/// Type aliases for common key sizes
pub type Ed25519PrivateKey = SecureKey<32>;
pub type Ed25519Seed = SecureKey<32>;
pub type AesKey256 = SecureKey<32>;
pub type AesKey128 = SecureKey<16>;

// ---------------------------------------------------------------------------
// SecurePhiBuffer — mlock-pinned memory for PHI data
// ---------------------------------------------------------------------------

/// A secure buffer that uses mlock to pin memory in RAM, preventing PHI data
/// from being swapped to disk. Falls back gracefully if mlock is unavailable.
pub struct SecurePhiBuffer {
    data: Vec<u8>,
    locked: bool,
}

impl SecurePhiBuffer {
    /// Create a new PHI buffer from existing data, pinning it in RAM via mlock.
    /// If mlock fails (e.g. insufficient privileges), the buffer is still usable
    /// but `is_locked()` will return false.
    pub fn new(data: Vec<u8>) -> Self {
        let locked = Self::mlock_region(data.as_ptr(), data.len());
        Self { data, locked }
    }

    /// Create a PHI buffer from a byte slice.
    pub fn from_slice(data: &[u8]) -> Self {
        Self::new(data.to_vec())
    }

    /// Returns true if the underlying memory is pinned via mlock.
    #[inline]
    pub fn is_locked(&self) -> bool {
        self.locked
    }

    /// Get a reference to the underlying data.
    #[inline]
    pub fn as_slice(&self) -> &[u8] {
        &self.data
    }

    /// Get a mutable reference to the underlying data.
    #[inline]
    pub fn as_mut_slice(&mut self) -> &mut [u8] {
        &mut self.data
    }

    /// Get the length of the buffer.
    #[inline]
    pub fn len(&self) -> usize {
        self.data.len()
    }

    /// Check if the buffer is empty.
    #[inline]
    pub fn is_empty(&self) -> bool {
        self.data.is_empty()
    }

    /// Platform-specific mlock. Returns true on success.
    #[cfg(unix)]
    fn mlock_region(ptr: *const u8, len: usize) -> bool {
        if len == 0 {
            return true;
        }
        // SAFETY: ptr is valid for len bytes (backed by Vec allocation).
        let ret = unsafe { libc::mlock(ptr as *const libc::c_void, len) };
        if ret != 0 {
            tracing::warn!(
                "mlock failed for PHI buffer ({} bytes): errno {}. Memory may be swappable.",
                len,
                std::io::Error::last_os_error()
            );
            false
        } else {
            true
        }
    }

    /// Non-unix platforms: mlock is not available.
    #[cfg(not(unix))]
    fn mlock_region(_ptr: *const u8, _len: usize) -> bool {
        tracing::warn!("mlock not available on this platform. PHI memory may be swappable.");
        false
    }

    /// Platform-specific munlock.
    #[cfg(unix)]
    fn munlock_region(ptr: *const u8, len: usize) {
        if len == 0 {
            return;
        }
        // SAFETY: ptr is valid for len bytes (backed by Vec allocation).
        unsafe {
            libc::munlock(ptr as *const libc::c_void, len);
        }
    }

    #[cfg(not(unix))]
    fn munlock_region(_ptr: *const u8, _len: usize) {}
}

impl Drop for SecurePhiBuffer {
    fn drop(&mut self) {
        // Zeroize first, then unlock
        self.data.zeroize();
        if self.locked {
            Self::munlock_region(self.data.as_ptr(), self.data.capacity());
        }
    }
}

impl std::fmt::Debug for SecurePhiBuffer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "SecurePhiBuffer([REDACTED; {} bytes, locked={}])",
            self.data.len(),
            self.locked
        )
    }
}

// ---------------------------------------------------------------------------
// PhiAllocator trait
// ---------------------------------------------------------------------------

/// Trait for allocating PHI-safe memory buffers.
pub trait PhiAllocator: Send + Sync {
    /// Allocate a zeroed PHI buffer of the given size.
    fn alloc_phi(&self, size: usize) -> SecurePhiBuffer;
}

/// Production PHI allocator that uses mlock.
pub struct PhiAllocatorImpl;

impl PhiAllocator for PhiAllocatorImpl {
    fn alloc_phi(&self, size: usize) -> SecurePhiBuffer {
        SecurePhiBuffer::new(vec![0u8; size])
    }
}

/// Mock PHI allocator for testing (no actual mlock).
pub struct MockPhiAllocator;

impl PhiAllocator for MockPhiAllocator {
    fn alloc_phi(&self, size: usize) -> SecurePhiBuffer {
        // Bypass mlock entirely — just create the buffer directly.
        SecurePhiBuffer {
            data: vec![0u8; size],
            locked: false,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_constant_time_compare_equal() {
        let a = [1u8, 2, 3, 4, 5];
        let b = [1u8, 2, 3, 4, 5];
        assert!(constant_time_compare(&a, &b));
    }

    #[test]
    fn test_constant_time_compare_different() {
        let a = [1u8, 2, 3, 4, 5];
        let b = [1u8, 2, 3, 4, 6];
        assert!(!constant_time_compare(&a, &b));
    }

    #[test]
    fn test_constant_time_compare_different_length() {
        let a = [1u8, 2, 3, 4, 5];
        let b = [1u8, 2, 3, 4];
        assert!(!constant_time_compare(&a, &b));
    }

    #[test]
    fn test_constant_time_compare_empty() {
        let a: [u8; 0] = [];
        let b: [u8; 0] = [];
        assert!(constant_time_compare(&a, &b));
    }

    #[test]
    fn test_validate_constitutional_hash_valid() {
        assert!(validate_constitutional_hash("608508a9bd224290"));
    }

    #[test]
    fn test_validate_constitutional_hash_invalid() {
        assert!(!validate_constitutional_hash("invalid_hash"));
        assert!(!validate_constitutional_hash("cdd01ef066bc6cf3")); // One char different
        assert!(!validate_constitutional_hash("")); // Empty
    }

    #[test]
    fn test_secure_buffer_zeroization() {
        let mut buffer = SecureBuffer::from_slice(&[1, 2, 3, 4, 5]);
        assert_eq!(buffer.len(), 5);

        // Clear should zero the data
        buffer.clear();
        assert!(buffer.is_empty());
    }

    #[test]
    fn test_secure_buffer_debug_redaction() {
        let buffer = SecureBuffer::from_slice(&[1, 2, 3, 4, 5]);
        let debug_str = format!("{:?}", buffer);
        assert!(debug_str.contains("REDACTED"));
        assert!(!debug_str.contains("1")); // Actual data should not appear
    }

    #[test]
    fn test_secure_key_from_slice() {
        let data = [1u8, 2, 3, 4, 5, 6, 7, 8];
        let key: Option<SecureKey<8>> = SecureKey::from_slice(&data);
        assert!(key.is_some());

        // Wrong size should return None
        let key: Option<SecureKey<8>> = SecureKey::from_slice(&[1, 2, 3]);
        assert!(key.is_none());
    }

    #[test]
    fn test_secure_key_debug_redaction() {
        let key = Ed25519PrivateKey::new([0u8; 32]);
        let debug_str = format!("{:?}", key);
        assert!(debug_str.contains("REDACTED"));
    }

    #[test]
    fn test_constant_time_str_compare() {
        assert!(constant_time_str_compare("hello", "hello"));
        assert!(!constant_time_str_compare("hello", "world"));
        assert!(!constant_time_str_compare("hello", "hell"));
    }

    // -----------------------------------------------------------------------
    // SecurePhiBuffer tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_secure_phi_buffer_creation() {
        let buf = SecurePhiBuffer::from_slice(&[0xDE, 0xAD, 0xBE, 0xEF]);
        assert_eq!(buf.len(), 4);
        assert!(!buf.is_empty());
        assert_eq!(buf.as_slice(), &[0xDE, 0xAD, 0xBE, 0xEF]);
    }

    #[test]
    fn test_secure_phi_buffer_empty() {
        let buf = SecurePhiBuffer::new(vec![]);
        assert!(buf.is_empty());
        assert_eq!(buf.len(), 0);
    }

    #[test]
    fn test_secure_phi_buffer_zeroization_on_drop() {
        let data = vec![1u8, 2, 3, 4, 5, 6, 7, 8];
        let ptr = data.as_ptr();
        let len = data.len();
        let buf = SecurePhiBuffer::new(data);
        assert_eq!(buf.len(), len);
        drop(buf);
        // After drop, we cannot safely read ptr (UB), but we verify drop runs
        // without panicking. The zeroize + munlock sequence completes cleanly.
    }

    #[test]
    fn test_secure_phi_buffer_debug_redaction() {
        let buf = SecurePhiBuffer::from_slice(&[0x41, 0x42, 0x43]); // "ABC"
        let debug_str = format!("{:?}", buf);
        assert!(debug_str.contains("REDACTED"), "Debug must redact PHI data");
        assert!(debug_str.contains("3 bytes"));
        // Actual byte values must not appear
        assert!(!debug_str.contains("41"));
        assert!(!debug_str.contains("ABC"));
    }

    #[test]
    fn test_secure_phi_buffer_debug_shows_lock_status() {
        let buf = SecurePhiBuffer::from_slice(&[1, 2, 3]);
        let debug_str = format!("{:?}", buf);
        assert!(
            debug_str.contains("locked="),
            "Debug output must show lock status"
        );
    }

    #[test]
    fn test_secure_phi_buffer_mlock_attempt() {
        // On most CI/test systems mlock may or may not succeed depending on
        // ulimits. We just verify it doesn't panic.
        let buf = SecurePhiBuffer::new(vec![0u8; 4096]);
        // is_locked() returns a valid bool regardless of platform/privileges
        let _locked = buf.is_locked();
    }

    #[test]
    fn test_secure_phi_buffer_mut_access() {
        let mut buf = SecurePhiBuffer::from_slice(&[0, 0, 0]);
        buf.as_mut_slice()[0] = 0xFF;
        assert_eq!(buf.as_slice()[0], 0xFF);
    }

    // -----------------------------------------------------------------------
    // PhiAllocator tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_mock_phi_allocator() {
        let alloc = MockPhiAllocator;
        let buf = alloc.alloc_phi(64);
        assert_eq!(buf.len(), 64);
        assert!(!buf.is_locked(), "Mock allocator must not mlock");
        // Buffer should be zeroed
        assert!(buf.as_slice().iter().all(|&b| b == 0));
    }

    #[test]
    fn test_phi_allocator_impl() {
        let alloc = PhiAllocatorImpl;
        let buf = alloc.alloc_phi(128);
        assert_eq!(buf.len(), 128);
        // Buffer should be zeroed
        assert!(buf.as_slice().iter().all(|&b| b == 0));
    }

    #[test]
    fn test_phi_allocator_trait_object() {
        // Verify the trait is object-safe (Send + Sync)
        let alloc: Box<dyn PhiAllocator> = Box::new(MockPhiAllocator);
        let buf = alloc.alloc_phi(32);
        assert_eq!(buf.len(), 32);
    }
}
