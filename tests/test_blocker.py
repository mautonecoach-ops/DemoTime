import unittest
from lexo.blocker import Blocker, BlockerConfig, BlockerPolicy


class TestBlockerV02(unittest.TestCase):

    def setUp(self):
        self.pol_base = BlockerPolicy(
            min={
                "trust": 50,
                "cohesion": 30,
                "equity": 50
            },
            weights={
                "trust": 1 / 3,
                "cohesion": 1 / 3,
                "equity": 1 / 3
            },
            require_fail_count=1,
            score_threshold=None,
        )
        self.cfg_base = BlockerConfig(policy=self.pol_base, dry_run=False)

    def test_ok(self):
        b = Blocker(self.cfg_base)
        block, reasons = b.evaluate({
            "trust": 70,
            "cohesion": 40,
            "equity": 75
        })
        self.assertFalse(block)
        self.assertEqual(reasons, [])

    def test_fail_by_cohesion(self):
        b = Blocker(self.cfg_base)
        block, reasons = b.evaluate({
            "trust": 65,
            "cohesion": 20,
            "equity": 60
        })
        self.assertTrue(block)
        self.assertTrue(any("cohesion" in r for r in reasons))

    def test_dry_run(self):
        cfg = BlockerConfig(policy=self.pol_base, dry_run=True)
        b = Blocker(cfg)
        block, reasons = b.evaluate({
            "trust": 40,
            "cohesion": 20,
            "equity": 40
        })
        self.assertFalse(block)
        self.assertTrue(any("dry_run" in r for r in reasons))

    def test_strict_policy_score(self):
        pol = BlockerPolicy(
            min={
                "trust": 50,
                "cohesion": 40,
                "equity": 60
            },
            weights={
                "trust": 0.25,
                "cohesion": 0.5,
                "equity": 0.25
            },
            require_fail_count=2,
            score_threshold=80.0,
        )
        cfg = BlockerConfig(policy=pol, dry_run=False)
        b = Blocker(cfg)
        block, reasons = b.evaluate({
            "trust": 60,
            "cohesion": 30,
            "equity": 55
        })
        self.assertTrue(block)
        self.assertTrue(any("score" in r or "fallas" in r for r in reasons))

    def test_block_by_score_only(self):
        # Sube el umbral de fallas para que NO bloquee por cantidad de fallas
        pol = BlockerPolicy(
            min={"trust": 50, "cohesion": 40, "equity": 60},
            weights={"trust": 0.25, "cohesion": 0.5, "equity": 0.25},
            require_fail_count=3,   # exige 3 fallas para bloquear por cantidad
            score_threshold=80.0,
        )
        cfg = BlockerConfig(policy=pol, dry_run=False)
        b = Blocker(cfg)

        # Solo una métrica por debajo del mínimo: cohesión 30/40 → ratio 0.75
        # Score = 0.25*1 + 0.5*0.75 + 0.25*1 = 0.25 + 0.375 + 0.25 = 0.875 → 87.5
        # Para forzar score < 80, bajamos más cohesión:
        block, reasons = b.evaluate({"trust": 60, "cohesion": 20, "equity": 65})
        # Ahora: ratio cohesión = 20/40 = 0.5 → score = 0.25*1 + 0.5*0.5 + 0.25*1 = 0.25+0.25+0.25=0.75 → 75.0
        self.assertTrue(block)
        self.assertTrue(any("score" in r for r in reasons))


if __name__ == "__main__":
    unittest.main()
