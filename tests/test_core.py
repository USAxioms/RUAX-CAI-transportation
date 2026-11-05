import ast, os, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)
from wad18 import *
import braking as B
import r3
import ledger as L

W = from_int


def scen(**kw):
    s = dict(v=W(20), gap=W(300), a_brake=W(1), mu=W(1), grade=0, t_react=W(1),
             t_build=W(2), margin=W(10), line_limit=W(40), curve_radius=None, a_lat=0)
    s.update(kw)
    return s


class TestWad(unittest.TestCase):
    def test_rounding_directions(self):
        self.assertEqual(mul_down(1, 1), 0)
        self.assertEqual(mul_up(1, 1), 1)
        self.assertEqual(div_down(WAD, 3 * WAD), 333333333333333333)
        self.assertEqual(div_up(WAD, 3 * WAD), 333333333333333334)
        self.assertEqual(mul_down(-1, 1), -1)  # floor
        self.assertEqual(mul_up(-1, 1), 0)

    def test_totality(self):
        self.assertEqual(div_down(5, 0), MAXV)
        self.assertEqual(div_up(-5, 0), MINV)
        self.assertEqual(sqrt_down(-1), 0)
        self.assertEqual(sat(MAXV + 5), MAXV)
        self.assertEqual(sat(MINV - 5), MINV)
        self.assertEqual(mul_down(MAXV, MAXV), MAXV)
        self.assertEqual(sat(MAXV + 1), MAXV)
        self.assertEqual(sat(MINV - 1), MINV)
        self.assertEqual(sat(MAXV), MAXV)

    def test_sqrt(self):
        self.assertEqual(sqrt_down(W(4)), W(2))
        self.assertEqual(sqrt_down(W(2)), 1414213562373095048)
        self.assertEqual(sqrt_down(0), 0)

    def test_decimal(self):
        self.assertEqual(from_decimal("9.80665"), (B.G, True))
        self.assertEqual(from_decimal("-0.5"), (-WAD // 2, True))
        self.assertEqual(from_decimal(".5"), (WAD // 2, True))
        self.assertEqual(from_decimal("1.0000000000000000019"), (WAD + 1, True))
        for bad in ["", "-", "+", ".", "1.2.3", "abc", "1e5", None, 5]:
            self.assertEqual(from_decimal(bad), (0, False))
        self.assertEqual(to_decimal(-WAD // 2), "-0.500000000000000000")
        self.assertEqual(to_decimal(B.G), "9.806650000000000000")

    def test_clamp(self):
        self.assertEqual(clamp(5, 0, 3), 3)
        self.assertEqual(clamp(-5, 0, 3), 0)
        self.assertEqual(clamp(2, 0, 3), 2)

    def test_no_floats_static(self):
        for fn in ["wad18.py", "braking.py", "r3.py", "ledger.py"]:
            with open(os.path.join(SRC, fn)) as fh:
                tree = ast.parse(fh.read())
            for n in ast.walk(tree):
                if isinstance(n, ast.Constant):
                    self.assertNotIsInstance(n.value, float, fn)
                if isinstance(n, ast.BinOp):
                    self.assertNotIsInstance(n.op, ast.Div, fn)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                    self.assertNotEqual(n.func.id, "float", fn)


class TestBraking(unittest.TestCase):
    def test_effective_decel(self):
        self.assertEqual(B.effective_decel(W(1), from_decimal("0.1")[0], 0), 980665000000000000)
        self.assertEqual(B.effective_decel(W(1), W(1), 0), W(1))
        self.assertEqual(B.effective_decel(W(1), W(1), from_decimal("0.01")[0]), W(1) + 98066500000000000)
        self.assertEqual(B.effective_decel(W(1), W(1), from_decimal("-0.01")[0]), W(1) - 98066500000000000)

    def test_stopping_distance_exact(self):
        self.assertEqual(B.stopping_distance(W(20), W(1), 0, 0), W(200))
        self.assertEqual(B.stopping_distance(W(20), W(1), W(1), W(2)), W(260))
        self.assertEqual(B.stopping_distance(-W(20), W(1), W(1), W(2)), W(260))
        self.assertEqual(B.stopping_distance(W(20), 0, 0, 0), MAXV)
        self.assertEqual(B.stopping_distance(W(20), -5, 0, 0), MAXV)

    def test_stopping_distance_conservative(self):
        for v in [3333333333333333333, 7777777777777777777 // 3, 12345678901234567, W(33) + 7]:
            for a in [W(1), 1234567891234567891, from_decimal("0.7")[0]]:
                for t in [0, 333333333333333333]:
                    d = B.stopping_distance(v, a, t, 0)
                    self.assertGreaterEqual((d - mul_up(v, t)) * 2 * a, v * v)
                    self.assertGreaterEqual(d, mul_up(v, t))

    def test_max_safe_speed(self):
        self.assertEqual(B.max_safe_speed(W(200), W(1), 0), W(20))
        self.assertEqual(B.max_safe_speed(0, W(1), 0), 0)
        self.assertEqual(B.max_safe_speed(W(10), 0, 0), 0)
        self.assertEqual(B.max_safe_speed(1, W(3), 777777777777777777), 0)
        self.assertEqual(B.max_safe_speed(W(10), W(1), -1), 0)
        v = B.max_safe_speed(W(270), W(1), W(3))
        self.assertEqual(B.stopping_distance(v, W(1), W(3), 0) <= W(270), True)
        self.assertLess(v, W(21))
        self.assertGreater(v, W(20))
        self.assertGreater(B.stopping_distance(v + 10 ** 12, W(1), W(3), 0), W(270))

    def test_max_safe_speed_soundness_grid(self):
        for D in [W(1), W(37) + 12345, W(500), W(10000) + 1]:
            for a in [W(1), 1234567891234567891, W(3)]:
                for T in [0, W(1), 777777777777777777, W(5)]:
                    v = B.max_safe_speed(D, a, T)
                    self.assertLessEqual(B.stopping_distance(v, a, T, 0), D)
                    self.assertGreater(v, 0)
                    self.assertGreater(B.stopping_distance(v + 10 ** 13, a, T, 0), D - W(1))

    def test_clearance_boundary(self):
        self.assertEqual(B.evaluate(scen(gap=W(270)))["verdict"], "PERMIT")
        self.assertEqual(B.evaluate(scen(gap=W(270) - 1))["verdict"], "EMERGENCY_BRAKE")
        r = B.evaluate(scen(gap=W(270)))
        self.assertEqual(r["required_gap"], W(270))
        self.assertEqual(r["clearance_ratio"], WAD)
        r = B.evaluate(scen(gap=W(270) - 1))
        self.assertEqual(r["clearance_ratio"], WAD - 1)
        self.assertEqual(B.evaluate(scen(gap=W(270)))["decel_setpoint"], 0)
        r = B.evaluate(scen(gap=W(135)))
        self.assertEqual(r["clearance_ratio"], WAD // 2)
        self.assertEqual(r["decel_setpoint"], W(1))

    def test_margin_and_degenerate(self):
        self.assertEqual(B.evaluate(scen(gap=W(260), margin=-W(50)))["verdict"], "PERMIT")
        self.assertEqual(B.evaluate(scen(gap=W(259), margin=-W(50)))["verdict"], "EMERGENCY_BRAKE")
        r = B.evaluate(scen(a_brake=0))
        self.assertEqual(r["verdict"], "EMERGENCY_BRAKE")
        self.assertEqual(r["decel_setpoint"], 0)
        r = B.evaluate(scen(gap=-W(5)))
        self.assertEqual(r["clearance_ratio"], 0)
        r = B.evaluate(scen(v=0, margin=0, gap=0))
        self.assertEqual(r["verdict"], "PERMIT")
        self.assertEqual(r["clearance_ratio"], WAD)

    def test_speed_ceiling_and_service(self):
        r = B.evaluate(scen(gap=W(5000), line_limit=W(15)))
        self.assertEqual((r["verdict"], r["speed_ceiling"]), ("SERVICE_BRAKE", W(15)))
        r = B.evaluate(scen(gap=W(5000), line_limit=W(40), v=-W(15)))
        self.assertEqual(r["verdict"], "PERMIT")
        r = B.evaluate(scen(gap=W(5000), curve_radius=W(400), a_lat=from_decimal("0.5")[0]))
        self.assertEqual(r["speed_ceiling"], 14142135623730950488)
        self.assertEqual(r["verdict"], "SERVICE_BRAKE")
        r = B.evaluate(scen(gap=W(5000), line_limit=W(10), curve_radius=W(400), a_lat=from_decimal("0.5")[0]))
        self.assertEqual(r["speed_ceiling"], W(10))

    def test_margin_in_ceiling(self):
        r = B.evaluate(scen(gap=W(5000), margin=W(10), line_limit=W(1000)))
        self.assertEqual(r["speed_ceiling"], B.max_safe_speed(W(4990), W(1), W(3)))
        self.assertNotEqual(r["speed_ceiling"], B.max_safe_speed(W(5000), W(1), W(3)))
        r = B.evaluate(scen(gap=W(5000), line_limit=W(10), v=-W(15)))
        self.assertEqual(r["verdict"], "SERVICE_BRAKE")

    def test_curve(self):
        self.assertEqual(B.curve_speed_limit(W(400), from_decimal("0.5")[0]), 14142135623730950488)
        self.assertEqual(B.curve_speed_limit(0, W(1)), 0)
        self.assertEqual(B.curve_speed_limit(1, 1), 0)
        self.assertEqual(B.curve_speed_limit(W(1), 0), 0)
        self.assertEqual(B.curve_speed_limit(W(1), -1), 0)

    def test_throttle_override(self):
        self.assertEqual(B.throttle_override(WAD // 2, "PERMIT"), WAD // 2)
        self.assertEqual(B.throttle_override(5 * WAD, "PERMIT"), WAD)
        self.assertEqual(B.throttle_override(-WAD, "PERMIT"), 0)
        self.assertEqual(B.throttle_override(WAD, "SERVICE_BRAKE"), 0)
        self.assertEqual(B.throttle_override(WAD, "EMERGENCY_BRAKE"), 0)

    def test_deterministic(self):
        self.assertEqual(B.evaluate(scen()), B.evaluate(scen()))


class TestR3(unittest.TestCase):
    def test_cases(self):
        self.assertEqual(r3.refine_position([100, 100, 101], 5), (100, True, 0))
        self.assertEqual(r3.refine_position([100, 101, 1000], 5), (100, True, 1))
        self.assertEqual(r3.refine_position([], 5), (0, False, 0))
        self.assertEqual(r3.refine_position([0, 100, 200], 10), (100, False, 0))
        self.assertEqual(r3.refine_position([7], 5, quorum=1), (7, True, 0))
        self.assertEqual(r3.refine_position([7], 5), (7, False, 0))
        self.assertEqual(r3.refine_position([100, 105], 5), (100, True, 0))
        self.assertEqual(r3.refine_position([100, 106], 5), (100, False, 0))
        self.assertEqual(r3.refine_position([1, 2, 3], 5, max_iter=0), (2, False, 0))

    def test_order_independent(self):
        self.assertEqual(r3.refine_position([5, 1, 3, 100], 10), r3.refine_position([100, 3, 5, 1], 10))


class TestLedger(unittest.TestCase):
    def test_chain(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "l.jsonl")
            self.assertTrue(L.verify(p))
            e0 = L.append(p, "A", {"x": "1"})
            e1 = L.append(p, "B", {"y": ["2"]})
            self.assertEqual(e0["prev"], "0" * 64)
            self.assertEqual(e1["prev"], e0["hash"])
            self.assertEqual((e0["seq"], e1["seq"]), (0, 1))
            self.assertTrue(L.verify(p))
            self.assertEqual(len(L.query(p)), 2)
            self.assertEqual(len(L.query(p, "B")), 1)
            self.assertIsNone(L.append(p, "C", {"f": 1.5}))
            self.assertIsNone(L.append(p, "C", {"f": [1.5]}))
            data = open(p).read()
            open(p, "w").write(data.replace('"x":"1"', '"x":"2"'))
            self.assertFalse(L.verify(p))
            self.assertIsNone(L.append(p, "D", {}))
            open(p, "w").write("not json\n")
            self.assertFalse(L.verify(p))
            open(p, "w").write("{}\n")
            self.assertFalse(L.verify(p))

    def test_field_tamper_and_key_order(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "l.jsonl")
            L.append(p, "A", {}); L.append(p, "B", {})
            rows = [json.loads(x) for x in open(p).read().splitlines()]
            for field, val in (("prev", "f" * 64), ("seq", 7)):
                bad = [dict(r) for r in rows]
                bad[1][field] = val
                with open(p, "w") as fh:
                    fh.write("\n".join(json.dumps(r) for r in bad) + "\n")
                self.assertFalse(L.verify(p), field)
            p1, p2 = os.path.join(d, "1"), os.path.join(d, "2")
            e1 = L.append(p1, "K", {"a": "1", "b": "2"})
            e2 = L.append(p2, "K", {"b": "2", "a": "1"})
            self.assertEqual(e1["hash"], e2["hash"])

    def test_reorder_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "l.jsonl")
            L.append(p, "A", {}); L.append(p, "B", {})
            lines = open(p).read().splitlines()
            open(p, "w").write("\n".join(reversed(lines)) + "\n")
            self.assertFalse(L.verify(p))


if __name__ == "__main__":
    unittest.main()
