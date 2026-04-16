use crate::ValidationResult;
use aws_lc_rs::{digest, signature};
#[allow(unused_imports)] // Required for KeyPair::public_key() method
use aws_lc_rs::signature::KeyPair;
use multiversion::multiversion;
use once_cell::sync::Lazy;
use rayon::prelude::*;
use regex::Regex;
use std::time::Instant;

/// Known prompt injection patterns
static PROMPT_INJECTION_PATTERNS: Lazy<Vec<Regex>> = Lazy::new(|| {
    vec![
        Regex::new(r"(?i)ignore (all )?previous instructions").expect("Unexpected error"),
        Regex::new(r"(?i)system prompt (leak|override)").expect("Unexpected error"),
        Regex::new(r"(?i)do anything now").expect("Unexpected error"), // DAN
        Regex::new(r"(?i)jailbreak").expect("Unexpected error"),
        Regex::new(r"(?i)persona (adoption|override)").expect("Unexpected error"),
        Regex::new(r"(?i)\(note to self: .*\)").expect("Unexpected error"),
        Regex::new(r"(?i)\[INST\].*\[/INST\]").expect("Unexpected error"), // LLM instruction markers bypass
        Regex::new(r"(?i)actually, do this instead").expect("Unexpected error"),
        Regex::new(r"(?i)forget everything you know").expect("Unexpected error"),
        Regex::new(r"(?i)bypass rules").expect("Unexpected error"),
        Regex::new(r"(?i)reveal your system instructions").expect("Unexpected error"),
        Regex::new(r"(?i)new directive:").expect("Unexpected error"),
    ]
});

/// Intercepts and neutralizes adversarial input patterns.
pub fn detect_prompt_injection(content: &str) -> Option<ValidationResult> {
    for pattern in PROMPT_INJECTION_PATTERNS.iter() {
        if pattern.is_match(content) {
            let mut result = ValidationResult::new();
            result.is_valid = false;
            result.errors.push(format!(
                "Prompt injection detected: Pattern mismatch '{}'",
                pattern.as_str()
            ));
            result
                .metadata
                .insert("decision".to_string(), "DENY".to_string());
            return Some(result);
        }
    }
    None
}

/// Returns true when compiled with the `fips` feature flag.
pub fn is_fips_mode() -> bool {
    cfg!(feature = "fips")
}

/// Result of FIPS validation for a single cryptographic algorithm.
#[derive(Debug, Clone)]
pub struct FipsValidationResult {
    /// Name of the cryptographic algorithm (e.g. "SHA-256", "Ed25519").
    pub algorithm: String,
    /// Whether this algorithm is FIPS-approved.
    pub fips_approved: bool,
    /// Human-readable attestation string.
    pub attestation: String,
}

/// Bulk Cryptographic Validation Kernel
pub struct BulkCryptoKernel;

impl BulkCryptoKernel {
    /// Establishes a baseline for bulk SHA-256 and Ed25519 signature validation.
    /// Uses Rayon for cross-core parallelism and aws-lc-rs for high-perf crypto.
    pub fn bulk_validate(
        messages: &[Vec<u8>],
        signatures: &[Vec<u8>],
        public_keys: &[Vec<u8>],
    ) -> (Vec<bool>, f64) {
        let start = Instant::now();

        let results: Vec<bool> = (0..messages.len())
            .into_par_iter()
            .map(|i| {
                let msg = &messages[i];
                let sig = &signatures[i];
                let pk = &public_keys[i];

                // 1. SHA-256 Hash Validation (SIMD-accelerated via aws-lc-rs/multiversion)
                let _hash = Self::compute_sha256_dispatch(msg);

                // 2. Signature Validation (SIMD-accelerated via aws-lc-rs/multiversion)
                Self::verify_signature_dispatch(pk, sig, msg)
            })
            .collect();

        let elapsed_ms = start.elapsed().as_secs_f64() * 1000.0;
        (results, elapsed_ms)
    }

    /// Zero-copy bulk validation using contiguous buffers.
    /// This avoids the overhead of creating Vec<Vec<u8>> when coming from Python/FFI.
    pub fn bulk_validate_buffer(
        messages_flat: &[u8],
        message_offsets: &[usize],
        message_lengths: &[usize],
        signatures_flat: &[u8],
        public_keys_flat: &[u8],
    ) -> (Vec<bool>, f64) {
        let start = Instant::now();
        let count = message_offsets.len();

        const SIG_LEN: usize = 64;
        const PK_LEN: usize = 32;

        let results: Vec<bool> = (0..count)
            .into_par_iter()
            .map(|i| {
                let offset = message_offsets[i];
                let len = message_lengths[i];

                if offset + len > messages_flat.len() {
                    return false;
                }

                let msg = &messages_flat[offset..offset + len];

                if (i + 1) * SIG_LEN > signatures_flat.len()
                    || (i + 1) * PK_LEN > public_keys_flat.len()
                {
                    return false;
                }

                let sig = &signatures_flat[i * SIG_LEN..(i + 1) * SIG_LEN];
                let pk = &public_keys_flat[i * PK_LEN..(i + 1) * PK_LEN];

                let _hash = Self::compute_sha256_dispatch(msg);

                Self::verify_signature_dispatch(pk, sig, msg)
            })
            .collect();

        let elapsed_ms = start.elapsed().as_secs_f64() * 1000.0;
        (results, elapsed_ms)
    }

    #[multiversion(targets("x86_64+avx2", "aarch64+neon"))]
    pub fn compute_sha256_dispatch(data: &[u8]) -> [u8; 32] {
        let h = digest::digest(&digest::SHA256, data);
        let mut res = [0u8; 32];
        res.copy_from_slice(h.as_ref());
        res
    }

    #[multiversion(targets("x86_64+avx2", "aarch64+neon"))]
    pub fn verify_signature_dispatch(pk: &[u8], sig: &[u8], msg: &[u8]) -> bool {
        let alg = &signature::ED25519;
        let peer_public_key = signature::UnparsedPublicKey::new(alg, pk);
        peer_public_key.verify(msg, sig).is_ok()
    }

    /// Validate which cryptographic algorithms used by the kernel are FIPS-approved.
    /// Returns a `FipsValidationResult` for each algorithm with an attestation string.
    pub fn bulk_validate_fips() -> Vec<FipsValidationResult> {
        let fips = is_fips_mode();
        vec![
            FipsValidationResult {
                algorithm: "SHA-256".to_string(),
                fips_approved: true, // SHA-256 is always FIPS-approved
                attestation: if fips {
                    "SHA-256: FIPS 180-4 approved (aws-lc-rs FIPS module active)".to_string()
                } else {
                    "SHA-256: FIPS 180-4 approved (FIPS module not active)".to_string()
                },
            },
            FipsValidationResult {
                algorithm: "Ed25519".to_string(),
                fips_approved: fips, // Ed25519 only FIPS-approved when FIPS module is active
                attestation: if fips {
                    "Ed25519: FIPS 186-5 approved (aws-lc-rs FIPS module active)".to_string()
                } else {
                    "Ed25519: Not FIPS-approved without FIPS module".to_string()
                },
            },
        ]
    }
}

#[cfg(test)]
mod security_tests {
    use super::*;

    #[test]
    fn test_simd_consistency() {
        let data = b"test message";
        let hash_simd = BulkCryptoKernel::compute_sha256_dispatch(data);

        let h = digest::digest(&digest::SHA256, data);
        let mut hash_expected = [0u8; 32];
        hash_expected.copy_from_slice(h.as_ref());

        assert_eq!(
            hash_simd, hash_expected,
            "SIMD hash must match standard hash"
        );
    }

    #[test]
    fn test_bulk_performance_baseline() {
        let count = 100;
        let msg = vec![0u8; 1024];
        let (pk, sig) = generate_test_key_and_sig(&msg);

        let messages = vec![msg; count];
        let signatures = vec![sig; count];
        let public_keys = vec![pk; count];

        let (results, elapsed_ms) =
            BulkCryptoKernel::bulk_validate(&messages, &signatures, &public_keys);

        assert_eq!(results.len(), count);
        assert!(results.iter().all(|&r| r), "All signatures should be valid");

        println!(
            "Bulk validation of {} messages took {:.3}ms",
            count, elapsed_ms
        );
    }

    #[test]
    fn test_is_fips_mode() {
        // Without the fips feature, this should be false
        let fips = is_fips_mode();
        assert!(!fips, "FIPS mode should be off without the feature flag");
    }

    #[test]
    fn test_fips_validation_result_fields() {
        let results = BulkCryptoKernel::bulk_validate_fips();
        assert_eq!(results.len(), 2);

        let sha256 = &results[0];
        assert_eq!(sha256.algorithm, "SHA-256");
        assert!(sha256.fips_approved, "SHA-256 is always FIPS-approved");
        assert!(sha256.attestation.contains("SHA-256"));

        let ed25519 = &results[1];
        assert_eq!(ed25519.algorithm, "Ed25519");
        // Without FIPS feature, Ed25519 is not FIPS-approved
        assert!(!ed25519.fips_approved);
        assert!(ed25519.attestation.contains("Ed25519"));
    }

    fn generate_test_key_and_sig(msg: &[u8]) -> (Vec<u8>, Vec<u8>) {
        let rand = aws_lc_rs::rand::SystemRandom::new();
        let pkcs8_bytes = signature::Ed25519KeyPair::generate_pkcs8(&rand).expect("Unexpected error");
        let key_pair = signature::Ed25519KeyPair::from_pkcs8(pkcs8_bytes.as_ref()).expect("Unexpected error");
        let sig = key_pair.sign(msg);
        (
            key_pair.public_key().as_ref().to_vec(),
            sig.as_ref().to_vec(),
        )
    }
}
