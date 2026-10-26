"""Unit and Integration Tests for SignalTrace V2.

Tests the validation, evidence detection rules, edge cases, and smoke dataset output.
"""

import json
import unittest
from datetime import datetime, timedelta

from data_loader import load_payments, load_shipments, load_complaints, parse_utc_timestamp
from llm_client import validate_extraction
from rules import (
    check_double_charge,
    check_payment_failures,
    check_shipped_unpaid,
    investigate_case
)


class TestSignalTraceValidation(unittest.TestCase):
    """Test data validation and deduplication."""

    def test_timestamp_parsing(self):
        valid_ts = "2026-10-25T09:00:00Z"
        dt = parse_utc_timestamp(valid_ts)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.hour, 9)

        with self.assertRaises(ValueError):
            parse_utc_timestamp("2026-10-25 09:00:00")
        with self.assertRaises(ValueError):
            parse_utc_timestamp("2026-02-30T09:00:00Z")

    def test_extraction_validation_order_ids(self):
        msg1 = "I was charged twice for ORD-101 please refund."
        issue, order_id = validate_extraction({"issue": "DOUBLE_CHARGE", "order_id": "ORD-101"}, msg1)
        self.assertEqual(issue, "DOUBLE_CHARGE")
        self.assertEqual(order_id, "ORD-101")

        msg2 = "Problem with ORD-101 and also ORD-102."
        issue, order_id = validate_extraction({"issue": "DOUBLE_CHARGE", "order_id": "ORD-101"}, msg2)
        self.assertEqual(order_id, None)

        msg3 = "Problem with ORD-101."
        issue, order_id = validate_extraction({"issue": "DOUBLE_CHARGE", "order_id": "ORD-999"}, msg3)
        self.assertEqual(order_id, None)

        issue, order_id = validate_extraction({"issue": "UNKNOWN_BUG", "order_id": "ORD-101"}, msg3)
        self.assertEqual(issue, "OTHER")


class TestDetectionRules(unittest.TestCase):
    """Test the three signal detection rules and edge cases."""

    def test_double_charge_rule(self):
        t1 = datetime(2026, 10, 25, 9, 0, 0)
        t2 = datetime(2026, 10, 25, 9, 1, 0)
        
        payments = [
            {"payment_id": "P1", "status": "SUCCESS", "amount_cents": 5000, "provider_ref": "REF-A", "timestamp": t1},
            {"payment_id": "P2", "status": "SUCCESS", "amount_cents": 5000, "provider_ref": "REF-B", "timestamp": t2},
        ]
        found, evidence = check_double_charge(payments)
        self.assertTrue(found)
        self.assertEqual(evidence, ["P1", "P2"])

        payments_same_ref = [
            {"payment_id": "P1", "status": "SUCCESS", "amount_cents": 5000, "provider_ref": "REF-A", "timestamp": t1},
            {"payment_id": "P2", "status": "SUCCESS", "amount_cents": 5000, "provider_ref": "REF-A", "timestamp": t2},
        ]
        found, evidence = check_double_charge(payments_same_ref)
        self.assertFalse(found)

    def test_payment_failures_10_minute_boundary(self):
        t0 = datetime(2026, 10, 25, 10, 0, 0)
        t1 = datetime(2026, 10, 25, 10, 5, 0)
        t2_exact = datetime(2026, 10, 25, 10, 10, 0)
        t2_over = datetime(2026, 10, 25, 10, 10, 1)

        payments_qualifying = [
            {"payment_id": "F1", "status": "FAILED", "timestamp": t0},
            {"payment_id": "F2", "status": "FAILED", "timestamp": t1},
            {"payment_id": "F3", "status": "FAILED", "timestamp": t2_exact},
        ]
        found, evidence = check_payment_failures(payments_qualifying)
        self.assertTrue(found)
        self.assertEqual(evidence, ["F1", "F2", "F3"])

        payments_over = [
            {"payment_id": "F1", "status": "FAILED", "timestamp": t0},
            {"payment_id": "F2", "status": "FAILED", "timestamp": t1},
            {"payment_id": "F3", "status": "FAILED", "timestamp": t2_over},
        ]
        found, evidence = check_payment_failures(payments_over)
        self.assertFalse(found)

    def test_shipped_unpaid_exact_timestamp(self):
        t = datetime(2026, 10, 25, 12, 0, 0)
        payments = [{"payment_id": "P1", "status": "SUCCESS", "timestamp": t}]
        shipments = [{"event_id": "S1", "event_type": "SHIPMENT_CREATED", "timestamp": t}]

        found, evidence = check_shipped_unpaid(payments, shipments)
        self.assertTrue(found)
        self.assertEqual(evidence, ["S1"])


class TestSmokeDataset(unittest.TestCase):
    """End-to-end test verifying smoke dataset against expected.json."""

    def test_smoke_dataset(self):
        payments, ps = load_payments("data/smoke/payments.csv")
        shipments, ss = load_shipments("data/smoke/shipments.jsonl")
        complaints, cs = load_complaints("data/smoke/complaints.jsonl")

        with open("data/smoke/expected.json", encoding="utf-8") as f:
            expected = json.load(f)

        self.assertEqual(ps, expected["stats"]["payments"])
        self.assertEqual(ss, expected["stats"]["shipments"])
        self.assertEqual(cs, expected["stats"]["complaints"])


if __name__ == "__main__":
    unittest.main()
