# WAD18 Deterministic Rail Velocity Sentinel (CAI-TRANS-01)
**Reference model, capsule v1.0.0.** Reproducible, integer-only reference implementation of braking-envelope, moving-block clearance, curve-limit and position-refinement logic.

> **Scope and honesty statement.** This is a deterministic *reference model and test oracle*. It is **not** a certified safety system (EN 50126/50128/50129, IEC 61508 SIL-4 would be required for deployment). All physical parameters in `demo.py` are **PLACEHOLDERS**. The braking model is a simplified constant-deceleration model; it does not model brake-force rise curves, rotating-mass effects, per-vehicle adhesion variance, or lead-train motion.

## 1. Axioms
- **A1 (WAD18).** Every quantity is an integer `x` denoting the real value `x / 10^18`. No floating-point value, literal, division operator (`/`) or `float()` call exists in the source; a static test enforces this via the AST.
- **A2 (Totality).** No function raises on any integer input. Division by zero and overflow saturate to `±MAXV = ±(2^127 − 1)`; malformed decimal strings return `(0, False)`.
- **A3 (Directed conservatism).** Quantities that enlarge a hazard round **up** (distances, run-on); quantities that grant capability round **down** (deceleration, speed caps).
- **A4 (Bit parity).** Python integers are arbitrary precision and `//` has defined floor semantics, so outputs are identical on every platform. `demo_expected.txt` pins this; `tools/verify_capsule.py` checks it.

## 2. WAD18 arithmetic
With `S = 10^18`: `mul_down(a,b)=⌊ab/S⌋`, `mul_up(a,b)=⌈ab/S⌉`, `div_down(a,b)=⌊aS/b⌋`, `div_up(a,b)=⌈aS/b⌉`, `sqrt_down(x)=⌊√(xS)⌋ = isqrt(xS)`.
**Lemma 1.** `mul_down(a,b) ≤ ab/S ≤ mul_up(a,b)`, each within 1 ulp. *Proof:* floor/ceiling of the exact rational. ∎
**Lemma 2.** `sqrt_down(x)` is the largest integer `r` with `r² ≤ xS`, i.e. the exact floor of the real square root at 18 places. ∎

## 3. Braking envelope
Effective deceleration (small-angle grade, positive = uphill):
`a_eff = min(a_brake, μ·g) + g·grade`, `g = 9.80665`, computed with `mul_down`.
Stopping distance for speed `v`, reaction time `t_r`, brake build-up `t_b` (train assumed to coast at constant `v` through `t_r+t_b`, the worst case under this model):
`d(v) = v(t_r+t_b) + v² / (2 a_eff)`, with `mul_up`/`div_up`. If `a_eff ≤ 0`, `d = MAXV` (fail-safe: no braking authority ⇒ unsafe).
**Theorem 1 (conservative stopping distance).** The computed `d̂(v) ≥ d(v)` for the exact real model. *Proof:* each term is rounded up by Lemma 1, sums of upward-rounded terms are upper bounds, and `2·a_eff` is exact. (Tested over a grid with the integer inequality `(d̂ − run_on)·2a ≥ v²`.) ∎

## 4. Moving-block clearance
Brick-wall assumption: the lead train may stop instantly at its rear end. With margin `m ≥ 0` (negative margins are clamped to 0) and gap `g`:
`required = d̂(v) + m`; verdict is `EMERGENCY_BRAKE` iff `g < required`.
Clearance ratio `ρ = clamp(⌊g/required⌋, 0, 1)` ∈ [0, 1]. The boundary `g = required` is **safe** (≥); `g = required − 1 ulp` brakes (tested).
**Maximum safe speed.** Solving `v·T + v²/(2a) = D` with `T = t_r+t_b`, `D = g − m` gives `v* = a(√(T² + 2D/a) − T)`. Floor rounding is applied, then a *verification loop* decreases `v` until `d̂(v) ≤ D`, so the returned cap is sound regardless of rounding (**Theorem 2**: `d̂(v_cap) ≤ D` by the loop postcondition; a failed loop returns 0). The speed ceiling is `min(v*, line_limit, curve_limit)`.
**Verdicts.** `EMERGENCY_BRAKE` (envelope violated) > `SERVICE_BRAKE` (envelope safe but `|v|` exceeds ceiling) > `PERMIT`. `throttle_override` forces throttle to 0 for any verdict other than `PERMIT` and clamps requests to [0, 1].
**Curve limit.** `v_max = ⌊√(a_lat · R)⌋`; non-positive inputs give 0.

## 5. Russell Recursive Refinement (R³)
Input: position estimates (balise, wheel encoder, satellite, …), tolerance `τ`, quorum `q` (default 2), iteration bound 16.
Loop: `m = low_median(C)`; keep `K = {c : |c − m| ≤ τ}`; if `|K| < q` return `(m, False)`; if `K = C` return `(m, True)`; else `C ← K`. Termination: `|C|` strictly decreases each pass, and an iteration cap makes it total. The low median is order-independent (tested). **`converged = False` must be treated by the caller as a loss of position confidence ⇒ brake.**

## 6. Cognitive State Ledger
`ledger/ledger.jsonl` is a hash chain: `h_i = SHA-256(canon({seq, kind, payload, prev}))`, `prev = h_{i−1}` (genesis = 64 zeros), canonical JSON with sorted keys. There are no timestamps (they would break determinism). Appends reject payloads containing floats and refuse to extend a corrupt chain. Verification checks `seq`, `prev` and hash independently (each tested by single-field tampering). Every capsule update is preceded by ledger entries (pre-execution intent, test results). **Limitation:** a hash chain proves internal consistency, not authenticity; real regulatory use requires signatures/anchoring, which are out of scope.

## 7. Mutation testing
`tools/mutants.py` applies 58 single-point source mutations (operator flips, rounding-direction swaps, removed guards, constant changes). Result: **58/58 killed**. Four mutants were analyzed as *equivalent* (unobservable by construction) and are documented in the tool, not counted. Two initial rounds revealed 10 test gaps (e.g. missing saturation boundary, untested `prev`/`seq` tampering, rounding in clearance ratio), which were closed with new tests, not by weakening mutants.

## 8. Reproduce
`python3 tools/verify_capsule.py` runs: ledger verification, 23 unit tests, demo-vs-expected byte comparison, and the mutation suite. `python3 tools/build_capsule.py` rebuilds the ZIP with fixed timestamps and sorted entries (byte-identical across rebuilds).

## 9. Open items
Parameter sourcing (vehicle-specific brake curves, certified adhesion models), lead-train motion models, sensor fault models for R³, formal verification (e.g. Coq/Isabelle) of Theorems 1–2, and certification.
