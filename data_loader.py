"""Data Loader and Validation Module.

This module handles loading and validating the three input datasets:
1. payments.csv
2. shipments.jsonl
3. complaints.jsonl

It tracks counts for: total, accepted, invalid, and duplicates.
Rule: total = accepted + invalid + duplicates.
"""

import csv
import json
import re
from datetime import datetime

UTC_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def parse_utc_timestamp(timestamp_str: str) -> datetime:
    """Validate and parse a UTC timestamp string.
    
    The string must strictly match 'YYYY-MM-DDTHH:MM:SSZ' and be a real date/time.
    """
    if not isinstance(timestamp_str, str):
        raise ValueError("Timestamp must be a string")
    
    if len(timestamp_str) != 20 or not timestamp_str.endswith("Z"):
        raise ValueError("Timestamp must be in ISO UTC format ending with Z")

    dt = datetime.strptime(timestamp_str, UTC_TIMESTAMP_FORMAT)
    if dt.strftime(UTC_TIMESTAMP_FORMAT) != timestamp_str:
        raise ValueError("Timestamp formatting does not strictly match canonical UTC")
    return dt


def is_non_empty_str(val) -> bool:
    """Check if value is a non-empty string after stripping whitespace."""
    return isinstance(val, str) and bool(val.strip())


def init_stats() -> dict:
    """Initialize count tracking dictionary."""
    return {
        "total": 0,
        "accepted": 0,
        "invalid": 0,
        "duplicates": 0
    }


def load_payments(csv_path: str):
    """Load, validate, and deduplicate payments from payments.csv.
    
    Rules:
    - Required nonempty fields: payment_id, order_id, timestamp, status, amount_cents.
    - Timestamp must exactly match UTC format and be a real date/time.
    - Status must be SUCCESS, FAILED, or PENDING.
    - Amount must be a positive integer in cents (> 0).
    - provider_ref is required for SUCCESS; may be empty for others.
    - Deduplicate by payment_id: keep the first valid row with that ID.
      An invalid row must not reserve an ID.
    - Fully blank rows do not count towards total.
    """
    records = []
    stats = init_stats()
    seen_ids = set()

    with open(csv_path, mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row or not any(is_non_empty_str(v) for v in row.values()):
                continue

            stats["total"] += 1

            try:
                payment_id = row.get("payment_id")
                order_id = row.get("order_id")
                timestamp_str = row.get("timestamp")
                status = row.get("status")
                amount_cents_str = row.get("amount_cents")
                provider_ref = row.get("provider_ref", "") or ""

                if not all(is_non_empty_str(x) for x in [payment_id, order_id, timestamp_str, status, amount_cents_str]):
                    raise ValueError("Missing or empty required field")

                payment_id = payment_id.strip()
                order_id = order_id.strip()
                status = status.strip()
                amount_cents_str = amount_cents_str.strip()
                provider_ref = provider_ref.strip()

                if status not in {"SUCCESS", "FAILED", "PENDING"}:
                    raise ValueError("Invalid status")

                if not re.fullmatch(r"\d+", amount_cents_str):
                    raise ValueError("amount_cents must be digits only")

                amount_cents = int(amount_cents_str)
                if amount_cents <= 0:
                    raise ValueError("amount_cents must be positive (> 0)")

                parsed_time = parse_utc_timestamp(timestamp_str.strip())

                if status == "SUCCESS" and not provider_ref:
                    raise ValueError("provider_ref is required for SUCCESS status")

            except (ValueError, TypeError, KeyError):
                stats["invalid"] += 1
                continue

            if payment_id in seen_ids:
                stats["duplicates"] += 1
                continue

            seen_ids.add(payment_id)
            stats["accepted"] += 1
            records.append({
                "payment_id": payment_id,
                "order_id": order_id,
                "timestamp": parsed_time,
                "status": status,
                "amount_cents": amount_cents,
                "provider_ref": provider_ref
            })

    records.sort(key=lambda x: (x["timestamp"], x["payment_id"]))
    return records, stats


def load_shipments(jsonl_path: str):
    """Load, validate, and deduplicate shipments from shipments.jsonl.
    
    Rules:
    - Each nonblank line must contain one valid JSON object.
    - Required nonempty strings: event_id, order_id, timestamp, event_type.
    - Timestamp must exactly match UTC format.
    - details is optional, untrusted text.
    - Deduplicate by event_id, keeping the first valid record.
    - Blank lines do not count towards total.
    """
    records = []
    stats = init_stats()
    seen_ids = set()

    with open(jsonl_path, mode="r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue

            stats["total"] += 1

            try:
                data = json.loads(stripped)
                if not isinstance(data, dict):
                    raise ValueError("Record is not a JSON object")

                event_id = data.get("event_id")
                order_id = data.get("order_id")
                timestamp_str = data.get("timestamp")
                event_type = data.get("event_type")

                if not all(is_non_empty_str(x) for x in [event_id, order_id, timestamp_str, event_type]):
                    raise ValueError("Missing or empty required field")

                event_id = event_id.strip()
                order_id = order_id.strip()
                event_type = event_type.strip()
                parsed_time = parse_utc_timestamp(timestamp_str.strip())

            except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                stats["invalid"] += 1
                continue

            if event_id in seen_ids:
                stats["duplicates"] += 1
                continue

            seen_ids.add(event_id)
            stats["accepted"] += 1
            records.append({
                "event_id": event_id,
                "order_id": order_id,
                "timestamp": parsed_time,
                "event_type": event_type,
                "details": data.get("details", "")
            })

    records.sort(key=lambda x: (x["timestamp"], x["event_id"]))
    return records, stats


def load_complaints(jsonl_path: str):
    """Load, validate, and deduplicate customer complaints from complaints.jsonl.
    
    Rules:
    - Each nonblank line contains a JSON object with nonempty strings ticket_id and message.
    - Deduplicate by ticket_id, keeping the first valid record.
    - Malformed JSON and missing required fields count as invalid.
    - Blank lines do not count towards total.
    """
    records = []
    stats = init_stats()
    seen_ids = set()

    with open(jsonl_path, mode="r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue

            stats["total"] += 1

            try:
                data = json.loads(stripped)
                if not isinstance(data, dict):
                    raise ValueError("Line is not a JSON object")

                ticket_id = data.get("ticket_id")
                message = data.get("message")

                if not is_non_empty_str(ticket_id) or not is_non_empty_str(message):
                    raise ValueError("ticket_id or message is missing or empty")

                ticket_id = ticket_id.strip()

            except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                stats["invalid"] += 1
                continue

            if ticket_id in seen_ids:
                stats["duplicates"] += 1
                continue

            seen_ids.add(ticket_id)
            stats["accepted"] += 1
            records.append({
                "ticket_id": ticket_id,
                "message": message
            })

    records.sort(key=lambda x: x["ticket_id"])
    return records, stats
