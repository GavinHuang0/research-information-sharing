import unittest

import numpy as np

from factorcast.evaluation import factor_diagnostics, forecast_blocks, mse


class EvaluationTests(unittest.TestCase):
    def test_every_test_date_has_only_past_history(self):
        blocks = list(forecast_blocks(100, 60, 15, 25, 10))
        self.assertEqual([b.test.start for b in blocks], [60, 70, 80])
        self.assertEqual(blocks[-1].test.stop, 85)
        for b in blocks:
            self.assertEqual(b.train.stop, b.validation.start)
            self.assertEqual(b.validation.stop, b.history.stop)
            self.assertEqual(b.history.stop, b.test.start)

    def test_invalid_split_and_loss_rejected(self):
        with self.assertRaises(ValueError):
            list(forecast_blocks(50, 40, 40, 5, 1))
        with self.assertRaises(ValueError):
            mse(np.ones(3), np.ones((3, 1)))

    def test_alignment_handles_rotation_without_using_test_fit(self):
        rng = np.random.default_rng(7)
        f = rng.normal(size=(40, 2))
        rotation = np.array([[0.0, 2.0], [-3.0, 0.0]])
        z = f @ rotation
        self.assertLess(factor_diagnostics(z[:30], f[:30], z[30:], f[30:]), 1e-20)


if __name__ == "__main__":
    unittest.main()
