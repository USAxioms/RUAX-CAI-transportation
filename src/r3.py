"""Russell Recursive Refinement (R3): bounded, deterministic position fusion in WAD18."""


def low_median(vals):
    s = sorted(vals)
    return s[(len(s) - 1) // 2]


def refine_position(estimates, tol, quorum=2, max_iter=16):
    """Returns (position, converged, iterations). Never raises; converged=False => caller must brake."""
    cand = list(estimates)
    if not cand:
        return (0, False, 0)
    for i in range(max_iter):
        m = low_median(cand)
        keep = [c for c in cand if abs(c - m) <= tol]
        if len(keep) < quorum:
            return (m, False, i)
        if len(keep) == len(cand):
            return (m, True, i)
        cand = keep
    return (low_median(cand), False, max_iter)
