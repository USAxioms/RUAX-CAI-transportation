"""Braking envelope, moving-block clearance and curve limits in WAD18.
Rounding is always conservative: distances round UP, decelerations and speed caps round DOWN.
PLACEHOLDER MODEL: constant-deceleration, brick-wall lead train, small-angle grade."""
from wad18 import WAD, MAXV, sat, clamp, mul_down, mul_up, div_down, div_up, sqrt_down

G = 9806650000000000000  # 9.80665 m/s^2


def effective_decel(a_brake, mu, grade):
    a_adh = mul_down(mu, G)
    a = a_brake if a_brake < a_adh else a_adh
    return sat(a + mul_down(G, grade))


def stopping_distance(v, a_eff, t_react, t_build):
    speed = v if v >= 0 else -v
    if a_eff <= 0:
        return MAXV
    total_t = t_react + t_build
    run_on = mul_up(speed, total_t)
    brake = div_up(mul_up(speed, speed), 2 * a_eff)
    return sat(run_on + brake)


def max_safe_speed(avail, a_eff, total_t):
    if avail <= 0 or a_eff <= 0 or total_t < 0:
        return 0
    inner = mul_down(total_t, total_t) + div_down(2 * avail, a_eff)
    v = mul_down(a_eff, sqrt_down(inner) - total_t)
    if v < 0:
        v = 0
    steps = 0
    while v > 0 and stopping_distance(v, a_eff, total_t, 0) > avail and steps < 1000:
        v = v - 1000000000 if v > 1000000000 else 0
        steps += 1
    if v > 0 and stopping_distance(v, a_eff, total_t, 0) > avail:
        return 0
    return v


def curve_speed_limit(radius, a_lat):
    if radius <= 0 or a_lat <= 0:
        return 0
    return sqrt_down(mul_down(a_lat, radius))


def throttle_override(throttle, verdict):
    t = clamp(throttle, 0, WAD)
    return t if verdict == "PERMIT" else 0


def evaluate(s):
    margin = s["margin"] if s["margin"] > 0 else 0
    a_eff = effective_decel(s["a_brake"], s["mu"], s["grade"])
    total_t = s["t_react"] + s["t_build"]
    speed = s["v"] if s["v"] >= 0 else -s["v"]
    sbd = stopping_distance(speed, a_eff, s["t_react"], s["t_build"])
    required = sat(sbd + margin)
    gap = s["gap"]
    safe = gap >= required
    ratio = clamp(div_down(gap, required), 0, WAD) if required > 0 else WAD
    ceiling = max_safe_speed(sat(gap - margin), a_eff, total_t)
    if s["line_limit"] < ceiling:
        ceiling = s["line_limit"]
    if s.get("curve_radius") is not None:
        c = curve_speed_limit(s["curve_radius"], s["a_lat"])
        if c < ceiling:
            ceiling = c
    if not safe:
        verdict = "EMERGENCY_BRAKE"
    elif speed > ceiling:
        verdict = "SERVICE_BRAKE"
    else:
        verdict = "PERMIT"
    return {
        "a_eff": a_eff, "stopping_distance": sbd, "required_gap": required,
        "clearance_ratio": ratio, "speed_ceiling": ceiling, "verdict": verdict,
        "decel_setpoint": a_eff if verdict == "EMERGENCY_BRAKE" and a_eff > 0 else 0,
    }
