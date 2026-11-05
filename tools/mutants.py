"""Mutation suite: apply one textual mutation at a time, require the test suite to fail."""
import os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

M = [
 ("wad18.py", "return sat(-((-a * b) // SCALE))", "return sat((a * b) // SCALE)"),
 ("wad18.py", "return sat((a * b) // SCALE)\n\n\ndef mul_up", "return sat(-((-a * b) // SCALE))\n\n\ndef mul_up"),
 ("wad18.py", "return sat((a * SCALE) // b)", "return sat(-((-a * SCALE) // b))"),
 ("wad18.py", "return sat(-((-a * SCALE) // b))", "return sat((a * SCALE) // b)"),
 ("wad18.py", "return MAXV if a >= 0 else MINV\n    return sat((a", "return MINV if a >= 0 else MAXV\n    return sat((a"),
 ("wad18.py", "return isqrt(x * SCALE)", "return isqrt(x) * 10 ** 9"),
 ("wad18.py", "if x <= 0:\n        return 0\n    return isqrt", "if x < 0:\n        return 0\n    return isqrt(x * SCALE) if x else 1 * 0 + 1\n    return isqrt"),
 ("wad18.py", "if x > MAXV:", "if x >= MAXV + 1 + 1:"),
 ("wad18.py", "if x < lo:", "if x <= lo - 1 and False:"),
 ("wad18.py", "fp = (fp + \"0\" * 18)[:18]", "fp = (fp + \"0\" * 18)[:17]"),
 ("wad18.py", "neg = s[0] == \"-\"", "neg = False"),
 ("wad18.py", "return \"%s%d.%018d\" % (sign, a // SCALE, a % SCALE)", "return \"%s%d.%018d\" % (\"\", a // SCALE, a % SCALE)"),
 ("braking.py", "a = a_brake if a_brake < a_adh else a_adh", "a = a_brake if a_brake > a_adh else a_adh"),
 ("braking.py", "return sat(a + mul_down(G, grade))", "return sat(a - mul_down(G, grade))"),
 ("braking.py", "G = 9806650000000000000", "G = 9810000000000000000"),
 ("braking.py", "total_t = t_react + t_build\n    run_on", "total_t = t_react - t_build\n    run_on"),
 ("braking.py", "brake = div_up(mul_up(speed, speed), 2 * a_eff)", "brake = div_down(mul_up(speed, speed), 2 * a_eff)"),
 ("braking.py", "brake = div_up(mul_up(speed, speed), 2 * a_eff)", "brake = div_up(mul_down(speed, speed), 2 * a_eff)"),
 ("braking.py", "brake = div_up(mul_up(speed, speed), 2 * a_eff)", "brake = div_up(mul_up(speed, speed), a_eff)"),
 ("braking.py", "run_on = mul_up(speed, total_t)", "run_on = mul_down(speed, total_t)"),
 ("braking.py", "speed = v if v >= 0 else -v\n    if a_eff", "speed = v\n    if a_eff"),
 ("braking.py", "if a_eff <= 0:\n        return MAXV", "if a_eff <= 0:\n        return 0"),
 ("braking.py", "v = mul_down(a_eff, sqrt_down(inner) - total_t)", "v = mul_down(a_eff, sqrt_down(inner) + total_t)"),
 ("braking.py", "inner = mul_down(total_t, total_t) + div_down(2 * avail, a_eff)", "inner = mul_down(total_t, total_t) + div_down(avail, a_eff)"),
 ("braking.py", "inner = mul_down(total_t, total_t) + div_down", "inner = div_down"),
 ("braking.py", "if avail <= 0 or a_eff <= 0 or total_t < 0:", "if avail <= 0 or a_eff <= 0:"),
 ("braking.py", "if v < 0:\n        v = 0\n    steps", "steps"),
 ("braking.py", "return sqrt_down(mul_down(a_lat, radius))", "return sqrt_down(mul_up(a_lat, radius))"),
 ("braking.py", "return t if verdict == \"PERMIT\" else 0", "return t if verdict != \"EMERGENCY_BRAKE\" else 0"),
 ("braking.py", "t = clamp(throttle, 0, WAD)", "t = clamp(throttle, 0, 2 * WAD)"),
 ("braking.py", "margin = s[\"margin\"] if s[\"margin\"] > 0 else 0", "margin = s[\"margin\"]"),
 ("braking.py", "safe = gap >= required", "safe = gap > required"),
 ("braking.py", "required = sat(sbd + margin)", "required = sat(sbd)"),
 ("braking.py", "ratio = clamp(div_down(gap, required), 0, WAD) if required > 0 else WAD", "ratio = clamp(div_up(gap, required + 1), 0, WAD) if required > 0 else WAD"),
 ("braking.py", "if required > 0 else WAD", "if required > 0 else 0"),
 ("braking.py", "ceiling = max_safe_speed(sat(gap - margin), a_eff, total_t)", "ceiling = max_safe_speed(sat(gap), a_eff, total_t)"),
 ("braking.py", "if s[\"line_limit\"] < ceiling:", "if s[\"line_limit\"] > ceiling:"),
 ("braking.py", "if c < ceiling:", "if c > ceiling:"),
 ("braking.py", "elif speed > ceiling:", "elif v_never:"),
 ("braking.py", "if s.get(\"curve_radius\") is not None:", "if False:"),
 ("braking.py", "\"decel_setpoint\": a_eff if verdict == \"EMERGENCY_BRAKE\" and a_eff > 0 else 0", "\"decel_setpoint\": a_eff"),
 ("braking.py", "speed = s[\"v\"] if s[\"v\"] >= 0 else -s[\"v\"]", "speed = s[\"v\"]"),
 ("r3.py", "return s[(len(s) - 1) // 2]", "return s[len(s) // 2]"),
 ("r3.py", "if len(keep) < quorum:", "if len(keep) <= quorum:"),
 ("r3.py", "if len(keep) < quorum:", "if False:"),
 ("r3.py", "if abs(c - m) <= tol", "if abs(c - m) < tol"),
 ("r3.py", "if len(keep) == len(cand):\n            return (m, True, i)", "if len(keep) == len(cand):\n            return (m, True, i + 1)"),
 ("r3.py", "if not cand:\n        return (0, False, 0)", "if not cand:\n        return (0, True, 0)"),
 ("r3.py", "return (low_median(cand), False, max_iter)", "return (low_median(cand), True, max_iter)"),
 ("ledger.py", "if e[\"seq\"] != i or e[\"prev\"] != prev:", "if e[\"prev\"] != prev:"),
 ("ledger.py", "if e[\"seq\"] != i or e[\"prev\"] != prev:", "if e[\"seq\"] != i:"),
 ("ledger.py", "if _hash(i, e[\"kind\"], e[\"payload\"], prev) != e[\"hash\"]:", "if False:"),
 ("ledger.py", "if _has_float(payload) or not verify(path):", "if not verify(path):"),
 ("ledger.py", "if _has_float(payload) or not verify(path):", "if _has_float(payload):"),
 ("ledger.py", "prev = entries[-1][\"hash\"] if entries else GENESIS", "prev = GENESIS"),
 ("ledger.py", "if isinstance(o, (list, tuple)):\n        return any(_has_float(v) for v in o)", "if False:\n        return False"),
 ("ledger.py", "if isinstance(o, dict):\n        return any(_has_float(v) for v in o.values())", "if False:\n        return False"),
 ("ledger.py", "sort_keys=True", "sort_keys=False"),
]

# Equivalent mutants (cannot change observable behavior), excluded from the kill score:
EQUIVALENT = [
 "max_safe_speed: dropping 'a_eff <= 0' guard -> v is forced to 0 by the post-loop stopping_distance check (defense in depth)",
 "max_safe_speed: dropping final post-loop check -> only reachable after 1000 correction steps (1e12 ulps), unreachable by construction",
 "curve_speed_limit: dropping 'a_lat <= 0' -> sqrt_down returns 0 for non-positive arguments anyway",
 "evaluate: 'speed > ceiling' vs 'speed >= ceiling + 1' -> identical on integers",
]


def run(tmp):
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
                       cwd=tmp, capture_output=True, text=True, timeout=120)
    return r.returncode


def main():
    killed, survived, invalid = [], [], []
    for idx, (fn, old, new) in enumerate(M):
        with tempfile.TemporaryDirectory() as tmp:
            for d in ("src", "tests"):
                shutil.copytree(os.path.join(ROOT, d), os.path.join(tmp, d),
                                ignore=shutil.ignore_patterns("__pycache__"))
            p = os.path.join(tmp, "src", fn)
            with open(p) as f:
                code = f.read()
            if code.count(old) != 1:
                invalid.append(idx)
                continue
            with open(p, "w") as f:
                f.write(code.replace(old, new))
            (killed if run(tmp) != 0 else survived).append(idx)
    print("equivalent (documented, excluded): %d" % len(EQUIVALENT))
    print("mutants=%d killed=%d survived=%s invalid=%s" % (len(M), len(killed), survived, invalid))
    return 0 if not survived and not invalid else 1


if __name__ == "__main__":
    sys.exit(main())
