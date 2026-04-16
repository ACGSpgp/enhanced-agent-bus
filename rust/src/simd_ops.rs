//! ACGS-2 Enhanced Agent Bus - SIMD Operations
//! Constitutional Hash: 608508a9bd224290
//!
//! Vectorized operations for high-performance numeric processing.
//! Uses multiversion for automatic SIMD dispatch across CPU architectures.

use multiversion::multiversion;


/// Error type for SIMD operations
#[derive(Debug, Clone, PartialEq)]
pub enum SimdError {
    LengthMismatch { expected: usize, actual: usize },
    OutputTooSmall { needed: usize, available: usize },
    EmptyInput,
    InvalidDistribution,
}

impl std::fmt::Display for SimdError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SimdError::LengthMismatch { expected, actual } => {
                write!(f, "Length mismatch: expected {}, got {}", expected, actual)
            }
            SimdError::OutputTooSmall { needed, available } => {
                write!(
                    f,
                    "Output buffer too small: need {}, have {}",
                    needed, available
                )
            }
            SimdError::EmptyInput => write!(f, "Empty input not allowed"),
            SimdError::InvalidDistribution => {
                write!(f, "Invalid probability distribution (q[i]=0 where p[i]>0)")
            }
        }
    }
}

impl std::error::Error for SimdError {}

/// Result type for SIMD operations
pub type Result<T> = std::result::Result<T, SimdError>;

/// Validate input lengths match and output is sufficient
#[inline]
fn validate_lengths(a_len: usize, b_len: usize, out_len: usize) -> Result<()> {
    if a_len == 0 {
        return Err(SimdError::EmptyInput);
    }
    if a_len != b_len {
        return Err(SimdError::LengthMismatch {
            expected: a_len,
            actual: b_len,
        });
    }
    if out_len < a_len {
        return Err(SimdError::OutputTooSmall {
            needed: a_len,
            available: out_len,
        });
    }
    Ok(())
}

/// SIMD-accelerated vector addition
#[multiversion(targets("x86_64+avx2", "x86_64+avx", "x86_64+sse4.1", "x86_64+sse2", "aarch64+neon"))]
pub fn vec_add_simd(a: &[f32], b: &[f32], out: &mut [f32]) -> Result<()> {
    validate_lengths(a.len(), b.len(), out.len())?;

    for i in 0..a.len() {
        out[i] = a[i] + b[i];
    }
    Ok(())
}

/// SIMD-accelerated vector subtraction
#[multiversion(targets("x86_64+avx2", "x86_64+avx", "x86_64+sse4.1", "x86_64+sse2", "aarch64+neon"))]
pub fn vec_sub_simd(a: &[f32], b: &[f32], out: &mut [f32]) -> Result<()> {
    validate_lengths(a.len(), b.len(), out.len())?;

    for i in 0..a.len() {
        out[i] = a[i] - b[i];
    }
    Ok(())
}

/// SIMD-accelerated vector multiplication (element-wise)
#[multiversion(targets("x86_64+avx2", "x86_64+avx", "x86_64+sse4.1", "x86_64+sse2", "aarch64+neon"))]
pub fn vec_mul_simd(a: &[f32], b: &[f32], out: &mut [f32]) -> Result<()> {
    validate_lengths(a.len(), b.len(), out.len())?;

    for i in 0..a.len() {
        out[i] = a[i] * b[i];
    }
    Ok(())
}

/// SIMD-accelerated dot product
#[multiversion(targets("x86_64+avx2", "x86_64+avx", "x86_64+sse4.1", "x86_64+sse2", "aarch64+neon"))]
pub fn vec_dot_simd(a: &[f32], b: &[f32]) -> Result<f32> {
    if a.is_empty() {
        return Err(SimdError::EmptyInput);
    }
    if a.len() != b.len() {
        return Err(SimdError::LengthMismatch {
            expected: a.len(),
            actual: b.len(),
        });
    }

    let mut sum = 0.0f32;
    for i in 0..a.len() {
        sum += a[i] * b[i];
    }
    Ok(sum)
}

/// SIMD-accelerated vector sum
#[multiversion(targets("x86_64+avx2", "x86_64+avx", "x86_64+sse4.1", "x86_64+sse2", "aarch64+neon"))]
pub fn vec_sum_simd(a: &[f32]) -> Result<f32> {
    if a.is_empty() {
        return Err(SimdError::EmptyInput);
    }

    let mut sum = 0.0f32;
    for &val in a {
        sum += val;
    }
    Ok(sum)
}

/// SIMD-accelerated vector max
#[multiversion(targets("x86_64+avx2", "x86_64+avx", "x86_64+sse4.1", "x86_64+sse2", "aarch64+neon"))]
pub fn vec_max_simd(a: &[f32]) -> Result<f32> {
    if a.is_empty() {
        return Err(SimdError::EmptyInput);
    }

    let mut max = f32::NEG_INFINITY;
    for &val in a {
        if val > max {
            max = val;
        }
    }
    Ok(max)
}

/// SIMD-accelerated vector min
#[multiversion(targets("x86_64+avx2", "x86_64+avx", "x86_64+sse4.1", "x86_64+sse2", "aarch64+neon"))]
pub fn vec_min_simd(a: &[f32]) -> Result<f32> {
    if a.is_empty() {
        return Err(SimdError::EmptyInput);
    }

    let mut min = f32::INFINITY;
    for &val in a {
        if val < min {
            min = val;
        }
    }
    Ok(min)
}

/// SIMD-accelerated L2 norm (Euclidean length)
#[multiversion(targets("x86_64+avx2", "x86_64+avx", "x86_64+sse4.1", "x86_64+sse2", "aarch64+neon"))]
pub fn vec_l2_norm_simd(a: &[f32]) -> Result<f32> {
    if a.is_empty() {
        return Err(SimdError::EmptyInput);
    }

    let mut sum = 0.0f32;
    for &val in a {
        sum += val * val;
    }
    Ok(sum.sqrt())
}

/// SIMD-accelerated cosine similarity
#[multiversion(targets("x86_64+avx2", "x86_64+avx", "x86_64+sse4.1", "x86_64+sse2", "aarch64+neon"))]
pub fn vec_cosine_similarity_simd(a: &[f32], b: &[f32]) -> Result<f32> {
    if a.is_empty() {
        return Err(SimdError::EmptyInput);
    }
    if a.len() != b.len() {
        return Err(SimdError::LengthMismatch {
            expected: a.len(),
            actual: b.len(),
        });
    }

    let mut dot = 0.0f32;
    let mut norm_a = 0.0f32;
    let mut norm_b = 0.0f32;

    for i in 0..a.len() {
        dot += a[i] * b[i];
        norm_a += a[i] * a[i];
        norm_b += b[i] * b[i];
    }

    let denom = (norm_a.sqrt() * norm_b.sqrt()).max(1e-10);
    Ok(dot / denom)
}

/// SIMD-accelerated softmax
#[multiversion(targets("x86_64+avx2", "x86_64+avx", "x86_64+sse4.1", "x86_64+sse2", "aarch64+neon"))]
pub fn vec_softmax_simd(a: &[f32], out: &mut [f32]) -> Result<()> {
    if a.is_empty() {
        return Err(SimdError::EmptyInput);
    }
    if out.len() < a.len() {
        return Err(SimdError::OutputTooSmall {
            needed: a.len(),
            available: out.len(),
        });
    }

    // Find max for numerical stability
    let max = vec_max_simd(a)?;

    // Compute exp(x - max)
    let mut sum = 0.0f32;
    for i in 0..a.len() {
        out[i] = (a[i] - max).exp();
        sum += out[i];
    }

    // Normalize
    let sum_inv = 1.0 / sum.max(1e-10);
    for out_val in out.iter_mut().take(a.len()) {
        *out_val *= sum_inv;
    }

    Ok(())
}

/// SIMD-accelerated ReLU activation
#[multiversion(targets("x86_64+avx2", "x86_64+avx", "x86_64+sse4.1", "x86_64+sse2", "aarch64+neon"))]
pub fn vec_relu_simd(a: &[f32], out: &mut [f32]) -> Result<()> {
    if a.is_empty() {
        return Err(SimdError::EmptyInput);
    }
    if out.len() < a.len() {
        return Err(SimdError::OutputTooSmall {
            needed: a.len(),
            available: out.len(),
        });
    }

    for i in 0..a.len() {
        out[i] = a[i].max(0.0);
    }
    Ok(())
}

/// SIMD-accelerated vector normalization (in-place)
#[multiversion(targets("x86_64+avx2", "x86_64+avx", "x86_64+sse4.1", "x86_64+sse2", "aarch64+neon"))]
pub fn vec_normalize_simd(a: &mut [f32]) -> Result<()> {
    if a.is_empty() {
        return Err(SimdError::EmptyInput);
    }

    let norm = vec_l2_norm_simd(a)?;
    if norm < 1e-10 {
        return Ok(()); // Don't normalize near-zero vectors
    }

    let norm_inv = 1.0 / norm;
    for val in a.iter_mut() {
        *val *= norm_inv;
    }
    Ok(())
}

/// Scalar fallback for vector addition
pub fn vec_add_scalar(a: &[f32], b: &[f32], out: &mut [f32]) -> Result<()> {
    validate_lengths(a.len(), b.len(), out.len())?;

    for i in 0..a.len() {
        out[i] = a[i] + b[i];
    }
    Ok(())
}

/// Result of embedding drift detection
#[derive(Debug, Clone, PartialEq)]
pub struct DriftResult {
    pub cosine_sim: f32,
    pub l2_delta: f32,
    pub is_drifted: bool,
}

/// SIMD-accelerated KL divergence: KL(P||Q) = sum(p[i] * ln(p[i]/q[i]))
/// Skips terms where p[i] == 0. Returns Err if q[i] == 0 and p[i] > 0.
#[multiversion(targets("x86_64+avx2", "x86_64+avx", "x86_64+sse4.1", "x86_64+sse2", "aarch64+neon"))]
pub fn vec_kl_divergence_simd(p: &[f32], q: &[f32]) -> Result<f32> {
    if p.is_empty() {
        return Err(SimdError::EmptyInput);
    }
    if p.len() != q.len() {
        return Err(SimdError::LengthMismatch {
            expected: p.len(),
            actual: q.len(),
        });
    }

    let mut sum = 0.0f32;
    for i in 0..p.len() {
        if p[i] == 0.0 {
            continue;
        }
        if q[i] == 0.0 {
            return Err(SimdError::InvalidDistribution);
        }
        sum += p[i] * (p[i] / q[i]).ln();
    }
    Ok(sum)
}

/// SIMD-accelerated Jensen-Shannon divergence: JS(P||Q) = 0.5*KL(P||M) + 0.5*KL(Q||M)
/// where M = 0.5*(P+Q). Bounded [0, ln2], symmetric.
#[multiversion(targets("x86_64+avx2", "x86_64+avx", "x86_64+sse4.1", "x86_64+sse2", "aarch64+neon"))]
pub fn vec_js_divergence_simd(p: &[f32], q: &[f32]) -> Result<f32> {
    if p.is_empty() {
        return Err(SimdError::EmptyInput);
    }
    if p.len() != q.len() {
        return Err(SimdError::LengthMismatch {
            expected: p.len(),
            actual: q.len(),
        });
    }

    let mut m = vec![0.0f32; p.len()];
    for i in 0..p.len() {
        m[i] = 0.5 * (p[i] + q[i]);
    }

    // KL(P||M)
    let mut kl_pm = 0.0f32;
    for i in 0..p.len() {
        if p[i] == 0.0 {
            continue;
        }
        if m[i] == 0.0 {
            return Err(SimdError::InvalidDistribution);
        }
        kl_pm += p[i] * (p[i] / m[i]).ln();
    }

    // KL(Q||M)
    let mut kl_qm = 0.0f32;
    for i in 0..q.len() {
        if q[i] == 0.0 {
            continue;
        }
        if m[i] == 0.0 {
            return Err(SimdError::InvalidDistribution);
        }
        kl_qm += q[i] * (q[i] / m[i]).ln();
    }

    Ok(0.5 * kl_pm + 0.5 * kl_qm)
}

/// SIMD-accelerated Chi-Squared statistic: sum((observed[i] - expected[i])^2 / expected[i])
/// Skips terms where expected[i] == 0.
#[multiversion(targets("x86_64+avx2", "x86_64+avx", "x86_64+sse4.1", "x86_64+sse2", "aarch64+neon"))]
pub fn vec_chi_squared_simd(observed: &[f32], expected: &[f32]) -> Result<f32> {
    if observed.is_empty() {
        return Err(SimdError::EmptyInput);
    }
    if observed.len() != expected.len() {
        return Err(SimdError::LengthMismatch {
            expected: observed.len(),
            actual: expected.len(),
        });
    }

    let mut sum = 0.0f32;
    for i in 0..observed.len() {
        if expected[i] == 0.0 {
            continue;
        }
        let diff = observed[i] - expected[i];
        sum += (diff * diff) / expected[i];
    }
    Ok(sum)
}

/// SIMD-accelerated Welch's t-statistic: t = (mean_a - mean_b) / sqrt(var_a/n_a + var_b/n_b)
/// Single-pass mean and variance computation.
#[multiversion(targets("x86_64+avx2", "x86_64+avx", "x86_64+sse4.1", "x86_64+sse2", "aarch64+neon"))]
pub fn vec_welch_t_simd(group_a: &[f32], group_b: &[f32]) -> Result<f32> {
    if group_a.is_empty() || group_b.is_empty() {
        return Err(SimdError::EmptyInput);
    }

    let n_a = group_a.len() as f32;
    let n_b = group_b.len() as f32;

    // Single-pass mean
    let mut sum_a = 0.0f32;
    for &v in group_a {
        sum_a += v;
    }
    let mean_a = sum_a / n_a;

    let mut sum_b = 0.0f32;
    for &v in group_b {
        sum_b += v;
    }
    let mean_b = sum_b / n_b;

    // Single-pass variance (using mean from above)
    let mut var_a = 0.0f32;
    for &v in group_a {
        let d = v - mean_a;
        var_a += d * d;
    }
    var_a /= n_a;

    let mut var_b = 0.0f32;
    for &v in group_b {
        let d = v - mean_b;
        var_b += d * d;
    }
    var_b /= n_b;

    let denom = (var_a / n_a + var_b / n_b).sqrt();
    if denom < 1e-10 {
        return Ok(0.0);
    }

    Ok((mean_a - mean_b) / denom)
}

/// SIMD-accelerated embedding drift detection.
/// Computes cosine similarity and L2 delta between baseline and current embeddings.
/// `is_drifted` is true if cosine_sim < threshold OR l2_delta > (2.0 * (1.0 - threshold)).
#[multiversion(targets("x86_64+avx2", "x86_64+avx", "x86_64+sse4.1", "x86_64+sse2", "aarch64+neon"))]
pub fn vec_embedding_drift_simd(
    baseline: &[f32],
    current: &[f32],
    threshold: f32,
) -> Result<DriftResult> {
    if baseline.is_empty() {
        return Err(SimdError::EmptyInput);
    }
    if baseline.len() != current.len() {
        return Err(SimdError::LengthMismatch {
            expected: baseline.len(),
            actual: current.len(),
        });
    }

    let cosine_sim = vec_cosine_similarity_simd(baseline, current)?;

    // L2 delta = norm of difference vector
    let mut l2_sum = 0.0f32;
    for i in 0..baseline.len() {
        let d = current[i] - baseline[i];
        l2_sum += d * d;
    }
    let l2_delta = l2_sum.sqrt();

    let l2_threshold = 2.0 * (1.0 - threshold);
    let is_drifted = cosine_sim < threshold || l2_delta > l2_threshold;

    Ok(DriftResult {
        cosine_sim,
        l2_delta,
        is_drifted,
    })
}

/// SIMD-accelerated stratified accuracy: per-group accuracy where correct = |pred - label| < 0.5
#[multiversion(targets("x86_64+avx2", "x86_64+avx", "x86_64+sse4.1", "x86_64+sse2", "aarch64+neon"))]
pub fn vec_stratified_accuracy_simd(
    predictions: &[f32],
    labels: &[f32],
    group_ids: &[u32],
    n_groups: u32,
) -> Result<Vec<f32>> {
    if predictions.is_empty() {
        return Err(SimdError::EmptyInput);
    }
    if predictions.len() != labels.len() {
        return Err(SimdError::LengthMismatch {
            expected: predictions.len(),
            actual: labels.len(),
        });
    }
    if predictions.len() != group_ids.len() {
        return Err(SimdError::LengthMismatch {
            expected: predictions.len(),
            actual: group_ids.len(),
        });
    }

    let ng = n_groups as usize;
    let mut correct = vec![0.0f32; ng];
    let mut total = vec![0.0f32; ng];

    for i in 0..predictions.len() {
        let g = group_ids[i] as usize;
        if g >= ng {
            continue;
        }
        total[g] += 1.0;
        if (predictions[i] - labels[i]).abs() < 0.5 {
            correct[g] += 1.0;
        }
    }

    let mut accuracies = vec![0.0f32; ng];
    for g in 0..ng {
        if total[g] > 0.0 {
            accuracies[g] = correct[g] / total[g];
        }
    }

    Ok(accuracies)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vec_add_basic() {
        let a = [1.0, 2.0, 3.0, 4.0];
        let b = [5.0, 6.0, 7.0, 8.0];
        let mut out = [0.0; 4];

        vec_add_simd(&a, &b, &mut out).expect("Unexpected error");
        assert_eq!(out, [6.0, 8.0, 10.0, 12.0]);
    }

    #[test]
    fn test_vec_add_length_mismatch() {
        let a = [1.0, 2.0, 3.0];
        let b = [4.0, 5.0];
        let mut out = [0.0; 3];

        let result = vec_add_simd(&a, &b, &mut out);
        assert!(matches!(result, Err(SimdError::LengthMismatch { .. })));
    }

    #[test]
    fn test_vec_add_output_too_small() {
        let a = [1.0, 2.0, 3.0];
        let b = [4.0, 5.0, 6.0];
        let mut out = [0.0; 2];

        let result = vec_add_simd(&a, &b, &mut out);
        assert!(matches!(result, Err(SimdError::OutputTooSmall { .. })));
    }

    #[test]
    fn test_vec_add_empty() {
        let a: [f32; 0] = [];
        let b: [f32; 0] = [];
        let mut out: [f32; 0] = [];

        let result = vec_add_simd(&a, &b, &mut out);
        assert!(matches!(result, Err(SimdError::EmptyInput)));
    }

    #[test]
    fn test_vec_dot() {
        let a = [1.0, 2.0, 3.0, 4.0];
        let b = [5.0, 6.0, 7.0, 8.0];

        let dot = vec_dot_simd(&a, &b).expect("Unexpected error");
        assert!((dot - 70.0).abs() < 0.001);
    }

    #[test]
    fn test_vec_cosine_similarity() {
        let a = [1.0, 0.0, 0.0];
        let b = [1.0, 0.0, 0.0];

        let sim = vec_cosine_similarity_simd(&a, &b).expect("Unexpected error");
        assert!((sim - 1.0).abs() < 0.001);

        let c = [0.0, 1.0, 0.0];
        let sim2 = vec_cosine_similarity_simd(&a, &c).expect("Unexpected error");
        assert!(sim2.abs() < 0.001);
    }

    #[test]
    fn test_vec_softmax() {
        let a = [1.0, 2.0, 3.0];
        let mut out = [0.0; 3];

        vec_softmax_simd(&a, &mut out).expect("Unexpected error");

        // Sum should be 1.0
        let sum: f32 = out.iter().sum();
        assert!((sum - 1.0).abs() < 0.001);

        // Values should be in increasing order
        assert!(out[0] < out[1] && out[1] < out[2]);
    }

    #[test]
    fn test_vec_relu() {
        let a = [-1.0, 0.0, 1.0, -0.5, 2.0];
        let mut out = [0.0; 5];

        vec_relu_simd(&a, &mut out).expect("Unexpected error");
        assert_eq!(out, [0.0, 0.0, 1.0, 0.0, 2.0]);
    }

    #[test]
    fn test_vec_normalize() {
        let mut a = [3.0, 4.0];

        vec_normalize_simd(&mut a).expect("Unexpected error");

        let norm = vec_l2_norm_simd(&a).expect("Unexpected error");
        assert!((norm - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_vec_l2_norm() {
        let a = [3.0, 4.0];
        let norm = vec_l2_norm_simd(&a).expect("Unexpected error");
        assert!((norm - 5.0).abs() < 0.001);
    }

    // --- Life-science governance kernel tests ---

    #[test]
    fn test_kl_divergence_known() {
        // P = [0.5, 0.5], Q = [0.25, 0.75]
        // KL = 0.5*ln(0.5/0.25) + 0.5*ln(0.5/0.75)
        //    = 0.5*ln(2) + 0.5*ln(2/3)
        //    = 0.5*0.6931 + 0.5*(-0.4055) = 0.3466 - 0.2027 = 0.1438
        let p = [0.5, 0.5];
        let q = [0.25, 0.75];
        let kl = vec_kl_divergence_simd(&p, &q).expect("Unexpected error");
        assert!((kl - 0.1438).abs() < 0.001);
    }

    #[test]
    fn test_kl_divergence_skip_zero_p() {
        // When p[i] == 0, that term is skipped
        let p = [0.0, 1.0];
        let q = [0.5, 0.5];
        let kl = vec_kl_divergence_simd(&p, &q).expect("Unexpected error");
        // KL = 0 + 1.0*ln(1.0/0.5) = ln(2) = 0.6931
        assert!((kl - 0.6931).abs() < 0.001);
    }

    #[test]
    fn test_kl_divergence_invalid_distribution() {
        // q[i] == 0 where p[i] > 0 should error
        let p = [0.5, 0.5];
        let q = [0.0, 1.0];
        let result = vec_kl_divergence_simd(&p, &q);
        assert!(matches!(result, Err(SimdError::InvalidDistribution)));
    }

    #[test]
    fn test_kl_divergence_empty() {
        let p: [f32; 0] = [];
        let q: [f32; 0] = [];
        assert!(matches!(
            vec_kl_divergence_simd(&p, &q),
            Err(SimdError::EmptyInput)
        ));
    }

    #[test]
    fn test_js_divergence_symmetric() {
        let p = [0.5, 0.5];
        let q = [0.25, 0.75];
        let js_pq = vec_js_divergence_simd(&p, &q).expect("Unexpected error");
        let js_qp = vec_js_divergence_simd(&q, &p).expect("Unexpected error");
        // JS divergence is symmetric
        assert!((js_pq - js_qp).abs() < 0.001);
    }

    #[test]
    fn test_js_divergence_bounded() {
        let p = [0.5, 0.5];
        let q = [0.25, 0.75];
        let js = vec_js_divergence_simd(&p, &q).expect("Unexpected error");
        // JS is bounded [0, ln2]
        assert!(js >= 0.0);
        assert!(js <= 2.0_f32.ln() + 0.001);
    }

    #[test]
    fn test_js_divergence_identical() {
        let p = [0.25, 0.25, 0.25, 0.25];
        let js = vec_js_divergence_simd(&p, &p).expect("Unexpected error");
        assert!(js.abs() < 0.001);
    }

    #[test]
    fn test_chi_squared_known() {
        // observed = [10, 20, 30], expected = [15, 15, 20]
        // chi2 = (10-15)^2/15 + (20-15)^2/15 + (30-20)^2/20
        //      = 25/15 + 25/15 + 100/20 = 1.667 + 1.667 + 5.0 = 8.333
        let observed = [10.0, 20.0, 30.0];
        let expected = [15.0, 15.0, 20.0];
        let chi2 = vec_chi_squared_simd(&observed, &expected).expect("Unexpected error");
        assert!((chi2 - 8.333).abs() < 0.01);
    }

    #[test]
    fn test_chi_squared_skip_zero_expected() {
        let observed = [5.0, 10.0];
        let expected = [0.0, 10.0];
        let chi2 = vec_chi_squared_simd(&observed, &expected).expect("Unexpected error");
        // Only second term: (10-10)^2/10 = 0
        assert!(chi2.abs() < 0.001);
    }

    #[test]
    fn test_chi_squared_perfect_fit() {
        let data = [10.0, 20.0, 30.0];
        let chi2 = vec_chi_squared_simd(&data, &data).expect("Unexpected error");
        assert!(chi2.abs() < 0.001);
    }

    #[test]
    fn test_welch_t_equal_groups() {
        // Two identical groups -> t = 0
        let a = [1.0, 2.0, 3.0, 4.0, 5.0];
        let t = vec_welch_t_simd(&a, &a).expect("Unexpected error");
        assert!(t.abs() < 0.001);
    }

    #[test]
    fn test_welch_t_different_means() {
        // group_a mean=2, group_b mean=4
        let a = [1.0, 2.0, 3.0];
        let b = [3.0, 4.0, 5.0];
        let t = vec_welch_t_simd(&a, &b).expect("Unexpected error");
        // t should be negative (mean_a < mean_b)
        assert!(t < 0.0);
        // |t| should be meaningful
        assert!(t.abs() > 1.0);
    }

    #[test]
    fn test_welch_t_empty() {
        let a: [f32; 0] = [];
        let b = [1.0, 2.0];
        assert!(matches!(
            vec_welch_t_simd(&a, &b),
            Err(SimdError::EmptyInput)
        ));
    }

    #[test]
    fn test_embedding_drift_no_drift() {
        let baseline = [1.0, 0.0, 0.0];
        let current = [1.0, 0.0, 0.0];
        let result =
            vec_embedding_drift_simd(&baseline, &current, 0.9).expect("Unexpected error");
        assert!((result.cosine_sim - 1.0).abs() < 0.001);
        assert!(result.l2_delta.abs() < 0.001);
        assert!(!result.is_drifted);
    }

    #[test]
    fn test_embedding_drift_orthogonal() {
        let baseline = [1.0, 0.0, 0.0];
        let current = [0.0, 1.0, 0.0];
        let result =
            vec_embedding_drift_simd(&baseline, &current, 0.9).expect("Unexpected error");
        assert!(result.cosine_sim.abs() < 0.001);
        assert!(result.is_drifted);
    }

    #[test]
    fn test_embedding_drift_length_mismatch() {
        let baseline = [1.0, 0.0];
        let current = [1.0, 0.0, 0.0];
        assert!(matches!(
            vec_embedding_drift_simd(&baseline, &current, 0.9),
            Err(SimdError::LengthMismatch { .. })
        ));
    }

    #[test]
    fn test_stratified_accuracy_basic() {
        // 2 groups, group 0: 2 correct out of 3, group 1: 1 correct out of 2
        let predictions = [1.0, 1.0, 2.0, 3.0, 3.0];
        let labels = [1.0, 2.0, 2.0, 3.0, 4.0];
        let group_ids = [0, 0, 0, 1, 1];
        let acc =
            vec_stratified_accuracy_simd(&predictions, &labels, &group_ids, 2)
                .expect("Unexpected error");
        assert_eq!(acc.len(), 2);
        // group 0: |1-1|<0.5 yes, |1-2|<0.5 no, |2-2|<0.5 yes => 2/3
        assert!((acc[0] - 2.0 / 3.0).abs() < 0.01);
        // group 1: |3-3|<0.5 yes, |3-4|<0.5 no => 1/2
        assert!((acc[1] - 0.5).abs() < 0.01);
    }

    #[test]
    fn test_stratified_accuracy_all_correct() {
        let predictions = [1.0, 2.0, 3.0];
        let labels = [1.0, 2.0, 3.0];
        let group_ids = [0, 0, 0];
        let acc =
            vec_stratified_accuracy_simd(&predictions, &labels, &group_ids, 1)
                .expect("Unexpected error");
        assert!((acc[0] - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_stratified_accuracy_empty() {
        let p: [f32; 0] = [];
        let l: [f32; 0] = [];
        let g: [u32; 0] = [];
        assert!(matches!(
            vec_stratified_accuracy_simd(&p, &l, &g, 1),
            Err(SimdError::EmptyInput)
        ));
    }
}
