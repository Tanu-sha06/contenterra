"""Evidence Detection Rules Module.

This module determines the evidence-based outcome for customer complaints:
- Signal A: DOUBLE_CHARGE
- Signal B: PAYMENT_FAILURES
- Signal C: SHIPPED_UNPAID
- Verdict logic: NOT_APPLICABLE, INSUFFICIENT_DATA, SIGNAL_FOUND, NOT_VERIFIED
"""

from datetime import timedelta
from typing import List, Dict, Any, Tuple


def check_double_charge(order_payments: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Evaluate Signal A - DOUBLE_CHARGE.
    
    Rule:
    Use accepted SUCCESS payments for the same order, sorted by (timestamp, payment_id).
    Detect two records that have the same amount_cents and different provider_ref values.
    Choose the earliest qualifying second payment, then pair it with the earliest
    preceding qualifying first payment.
    Evidence: both payment IDs in chronological order.
    """
    success_payments = [p for p in order_payments if p["status"] == "SUCCESS"]

    for j in range(len(success_payments)):
        second_payment = success_payments[j]
        for i in range(j):
            first_payment = success_payments[i]
            if (first_payment["amount_cents"] == second_payment["amount_cents"] and
                    first_payment["provider_ref"] != second_payment["provider_ref"]):
                return True, [first_payment["payment_id"], second_payment["payment_id"]]

    return False, []


def check_payment_failures(order_payments: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Evaluate Signal B - PAYMENT_FAILURES.
    
    Rule:
    For a single order, sort only accepted FAILED payments by (timestamp, payment_id).
    Find the earliest three consecutive entries in that failed-payment sequence whose
    first-to-third interval is 10 minutes or less (inclusive, <= 600 seconds).
    Evidence: those three payment IDs in that order.
    """
    failed_payments = [p for p in order_payments if p["status"] == "FAILED"]

    ten_minutes = timedelta(minutes=10)

    for i in range(len(failed_payments) - 2):
        p1 = failed_payments[i]
        p2 = failed_payments[i + 1]
        p3 = failed_payments[i + 2]

        interval = p3["timestamp"] - p1["timestamp"]
        if interval <= ten_minutes:
            return True, [p1["payment_id"], p2["payment_id"], p3["payment_id"]]

    return False, []


def check_shipped_unpaid(order_payments: List[Dict[str, Any]], order_shipments: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Evaluate Signal C - SHIPPED_UNPAID.
    
    Rule:
    For a single order, sort accepted SHIPMENT_CREATED events by (timestamp, event_id).
    Find the earliest shipment event for which there is no SUCCESS payment with a strictly
    earlier timestamp.
    Evidence: that shipment event ID.
    Note: A payment recorded at the exact same timestamp is not earlier.
    """
    success_timestamps = [p["timestamp"] for p in order_payments if p["status"] == "SUCCESS"]

    shipment_created_events = [s for s in order_shipments if s["event_type"] == "SHIPMENT_CREATED"]

    for event in shipment_created_events:
        event_time = event["timestamp"]
        has_earlier_success = any(p_time < event_time for p_time in success_timestamps)
        if not has_earlier_success:
            return True, [event["event_id"]]

    return False, []


def investigate_case(issue: str, order_id: str, payments: List[Dict[str, Any]], shipments: List[Dict[str, Any]], known_orders: set) -> Tuple[str, List[str]]:
    """Determine the evidence-based outcome for a single complaint.
    
    Verdicts:
    - NOT_APPLICABLE: Issue is OTHER (even if no order is mentioned).
    - INSUFFICIENT_DATA: Issue is known but usable order ID is missing (None) or order is unknown.
    - SIGNAL_FOUND: The corresponding rule produces valid evidence for the known order.
    - NOT_VERIFIED: Order is known but that rule is not satisfied by these records.
    
    Only SIGNAL_FOUND may include nonempty evidence_ids.
    """
    if issue == "OTHER":
        return "NOT_APPLICABLE", []

    if order_id is None or order_id not in known_orders:
        return "INSUFFICIENT_DATA", []

    order_payments = [p for p in payments if p["order_id"] == order_id]
    order_shipments = [s for s in shipments if s["order_id"] == order_id]

    if issue == "DOUBLE_CHARGE":
        found, evidence = check_double_charge(order_payments)
        if found:
            return "SIGNAL_FOUND", evidence
        return "NOT_VERIFIED", []

    elif issue == "PAYMENT_FAILURES":
        found, evidence = check_payment_failures(order_payments)
        if found:
            return "SIGNAL_FOUND", evidence
        return "NOT_VERIFIED", []

    elif issue == "SHIPPED_UNPAID":
        found, evidence = check_shipped_unpaid(order_payments, order_shipments)
        if found:
            return "SIGNAL_FOUND", evidence
        return "NOT_VERIFIED", []

    return "NOT_APPLICABLE", []
