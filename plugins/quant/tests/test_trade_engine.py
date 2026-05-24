import os
import tempfile
import unittest

_IMPORT_TMP = tempfile.TemporaryDirectory()
os.environ["TRADE_ENGINE_DB_PATH"] = os.path.join(_IMPORT_TMP.name, "trade_history.db")
os.environ["TRADE_ENGINE_SETTINGS_PATH"] = os.path.join(_IMPORT_TMP.name, "risk_settings.json")

import trade_engine as te


BASE_CFG = {
    "account_balance": 10000.0,
    "risk_per_trade_percent": 1.0,
    "max_position_percent": 25.0,
    "max_leverage": 2.0,
    "atr_multiplier": 1.5,
    "minimum_risk_reward_ratio": 1.5,
}


def market_data(price=100.0, atr=2.0, bull=60.0, side=20.0, bear=20.0):
    return {
        "technical": {"price": price, "atr": atr},
        "regime": {
            "regime_label": "Bullish Trend",
            "bullish_prob": bull,
            "sideways_prob": side,
            "bearish_prob": bear,
            "agent_scores": {"technical": 0.8, "sentiment": 0.2},
        },
        "risk": {"risk_level": "LOW", "vol_expanding": False},
        "markov": {"markov_score": 0.4},
    }


def component_scores(risk=80.0, volatility=70.0):
    return {
        "markov": 70.0,
        "technical": 80.0,
        "sentiment": 60.0,
        "volatility": volatility,
        "risk": risk,
        "breadth": 60.0,
    }


def paper_opp(status="ACTIVE", price=100.0, updated_at="2026-01-01T00:00:00Z"):
    return {
        "ticker": "TEST",
        "direction": "LONG",
        "entry_price": price,
        "updated_at": updated_at,
        "confidence_score": 85.0,
        "expected_horizon": "2-5 DAYS",
        "reason_summary": "Test setup.",
        "status": status,
        "stop_loss": 95.0,
        "target_price": 110.0,
        "risk_per_share": 5.0,
        "reward_per_share": 10.0,
        "shares": 10,
        "capital_required": 1000.0,
        "leverage_used": 0.1,
        "max_loss": 50.0,
        "account_risk_pct": 0.5,
        "rr_ratio": 2.0,
        "expected_value": 4.0,
        "kelly_fraction": 0.4,
        "safe_kelly": 0.1,
    }


class TradeEngineMathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        te.DB_PATH = os.path.join(self.tmp.name, "trade_history.db")
        te.SETTINGS_PATH = os.path.join(self.tmp.name, "risk_settings.json")
        te._init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_atr_stop_calculation_long_and_short(self):
        long_stop = te._atr_stop_prices(100.0, 2.0, "LONG", 1.5, 2.0)
        self.assertEqual(long_stop["risk_per_share"], 3.0)
        self.assertEqual(long_stop["reward_per_share"], 6.0)
        self.assertEqual(long_stop["stop_loss"], 97.0)
        self.assertEqual(long_stop["target_price"], 106.0)

        short_stop = te._atr_stop_prices(100.0, 2.0, "SHORT", 1.5, 2.0)
        self.assertEqual(short_stop["stop_loss"], 103.0)
        self.assertEqual(short_stop["target_price"], 94.0)

    def test_position_sizing_uses_atr_risk_and_actual_leverage(self):
        ps = te._position_sizing(market_data(), "LONG", 85.0, BASE_CFG)

        self.assertEqual(ps["risk_per_share"], 3.0)
        self.assertEqual(ps["reward_per_share"], 4.5)
        self.assertEqual(ps["shares"], 33)
        self.assertEqual(ps["capital_required"], 3300.0)
        self.assertEqual(ps["leverage_used"], 0.33)
        self.assertEqual(ps["max_loss"], 99.0)
        self.assertEqual(ps["account_risk_pct"], 0.99)

    def test_max_leverage_blocks_oversized_trade(self):
        data = market_data(price=1000.0, atr=1.0, bull=80.0, side=10.0, bear=10.0)
        ps = te._position_sizing(data, "LONG", 85.0, BASE_CFG)
        reason = te._no_trade_reason(data, component_scores(), "LONG", "TEST", ps, 85.0, BASE_CFG)

        self.assertGreater(ps["leverage_used"], BASE_CFG["max_leverage"])
        self.assertIn("Leverage", reason)

    def test_expected_value(self):
        self.assertEqual(te._expected_value(0.55, 2.0, 4.0), 1.3)
        self.assertEqual(te._expected_value(0.40, 2.0, 3.0), 0.0)
        self.assertEqual(te._expected_value(0.30, 2.0, 3.0), -0.5)

    def test_kelly_fraction(self):
        self.assertEqual(te._kelly_fraction(0.55, 2.0), 0.325)
        self.assertEqual(te._kelly_fraction(0.30, 1.5), -0.1667)

    def test_no_trade_rules_prefer_weak_scores_and_sideways_regimes(self):
        data = market_data()
        c = component_scores()

        direction = te._direction(data, c, 69.0)
        ps = te._position_sizing(data, direction, 69.0, BASE_CFG)
        reason = te._no_trade_reason(data, c, direction, "TEST", ps, 69.0, BASE_CFG)

        self.assertEqual(direction, "NO TRADE")
        self.assertEqual(ps["shares"], 0)
        self.assertIn("active trade threshold", reason)

        sideways = market_data(bull=30.0, side=45.0, bear=25.0)
        direction = te._direction(sideways, c, 85.0)
        ps = te._position_sizing(sideways, direction, 85.0, BASE_CFG)
        reason = te._no_trade_reason(sideways, c, direction, "TEST", ps, 85.0, BASE_CFG)

        self.assertEqual(direction, "NO TRADE")
        self.assertIn("Sideways regime dominant", reason)

    def test_paper_trade_lifecycle_opens_and_closes_on_target(self):
        te._update_paper(paper_opp(), None)
        stats = te.get_paper_stats()
        self.assertEqual(len(stats["open_trades"]), 1)
        self.assertEqual(stats["total_trades"], 0)

        hit_target = paper_opp(price=111.0, updated_at="2026-01-01T06:00:00Z")
        te._update_paper(hit_target, {"status": "ACTIVE"})

        stats = te.get_paper_stats()
        self.assertEqual(len(stats["open_trades"]), 0)
        self.assertEqual(stats["total_trades"], 1)
        self.assertEqual(stats["exit_types"], {"TARGET_HIT": 1})
        self.assertEqual(stats["avg_return"], 11.0)
        self.assertEqual(stats["avg_hold_h"], 6.0)


if __name__ == "__main__":
    unittest.main()
