// Continuous trust engine (paper, Section 6.2): T(x) = sum_k w_k c_k(x), c_k = 1 - x_k for anomaly features.
export const W = { b: 0.30, d: 0.15, n: 0.15, g: 0.20, v: 0.15, t: 0.05 };
const ANOM = new Set(["g", "v", "t"]);
export function score(x) { let s = 0; for (const k of Object.keys(W)) s += W[k] * (ANOM.has(k) ? 1 - x[k] : x[k]); return s; }
export function decide(T) { return T >= 0.75 ? "ALLOW" : T >= 0.5 ? "STEP_UP" : "DENY"; }
// seeded PRNG so every run sees the same request contexts
export function rng(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const clip = v => Math.min(1, Math.max(0, v));
export function legitContext(r) { const n = () => (r() + r() + r() - 1.5) / 1.5; // ~[-1,1]
  return { b: clip(0.92 + 0.05 * n()), d: clip(0.9 + 0.08 * n()), n: clip(0.9 + 0.08 * n()), g: clip(0.05 + 0.05 * n()), v: clip(0.1 + 0.08 * n()), t: clip(0.15 + 0.1 * n()) }; }
