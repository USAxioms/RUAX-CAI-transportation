"""Deterministic demo. PLACEHOLDER parameters. Output must be byte-identical everywhere."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from wad18 import from_int, from_decimal, to_decimal, WAD
import braking as B
import r3

D = lambda s: from_decimal(s)[0]
BASE = dict(v=D("27.777777777777777777"), gap=D("1200"), a_brake=D("1.0"), mu=D("0.15"),
            grade=D("-0.01"), t_react=D("1.5"), t_build=D("2.0"), margin=D("50"),
            line_limit=D("33.333333333333333333"), curve_radius=None, a_lat=D("0.8"))
CASES = [
    ("A open line", {}),
    ("B closing gap", {"gap": D("600")}),
    ("C curve R=800", {"curve_radius": D("800")}),
    ("D wet rail mu=0.05", {"mu": D("0.05")}),
    ("E gap violated", {"gap": D("500")}),
]


def main():
    out = []
    for name, ov in CASES:
        s = dict(BASE); s.update(ov)
        r = B.evaluate(s)
        out.append("[%s]" % name)
        for k in ("a_eff", "stopping_distance", "required_gap", "clearance_ratio", "speed_ceiling", "decel_setpoint"):
            out.append("  %s=%s" % (k, to_decimal(r[k])))
        out.append("  verdict=%s" % r["verdict"])
        out.append("  throttle(0.8)=%s" % to_decimal(B.throttle_override(D("0.8"), r["verdict"])))
    pos, ok, it = r3.refine_position([D("1000.000000000000000001"), D("1000.000000000000000002"), D("1250")], D("0.5"))
    out.append("[R3] pos=%s converged=%s iterations=%d" % (to_decimal(pos), ok, it))
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    sys.stdout.write(main())
