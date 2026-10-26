import argparse
import json
import os
import sys

from data_loader import load_payments, load_shipments, load_complaints
from llm_client import load_offline_extractions, extract_complaint_info
from rules import investigate_case


def parse_arguments():
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(
        description="SignalTrace V2: Evidence-driven investigation of e-commerce customer complaints."
    )
    parser.add_argument(
        "--payments",
        required=True,
        help="Path to payments.csv"
    )
    parser.add_argument(
        "--shipments",
        required=True,
        help="Path to shipments.jsonl"
    )
    parser.add_argument(
        "--complaints",
        required=True,
        help="Path to complaints.jsonl"
    )
    parser.add_argument(
        "--extractions",
        help="Path to offline extractions.json. If omitted, runs in live LLM mode."
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to output JSON file"
    )
    parser.add_argument(
        "--provider",
        choices=["gemini", "groq"],
        help="LLM inference provider for live mode (gemini or groq)"
    )
    parser.add_argument(
        "--model",
        help="Model name to use for the selected inference provider"
    )
    return parser.parse_args()


def determine_provider(args):
    """Determine which LLM provider to use in live inference mode."""
    if args.extractions:
        return None

    if args.provider:
        return args.provider

    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    elif os.environ.get("GROQ_API_KEY"):
        return "groq"
    else:
        print(
            "Error: Live mode requires either GEMINI_API_KEY or GROQ_API_KEY environment variable, "
            "or use --extractions for offline mode.",
            file=sys.stderr
        )
        sys.exit(1)


def main():
    args = parse_arguments()

    print(f"Loading payments from {args.payments}...")
    payments, payment_stats = load_payments(args.payments)

    print(f"Loading shipments from {args.shipments}...")
    shipments, shipment_stats = load_shipments(args.shipments)

    print(f"Loading complaints from {args.complaints}...")
    complaints, complaint_stats = load_complaints(args.complaints)

    known_orders = {p["order_id"] for p in payments} | {s["order_id"] for s in shipments}

    fixture_lookup = None
    provider = None
    if args.extractions:
        print(f"Running in offline mode using fixture: {args.extractions}")
        fixture_lookup = load_offline_extractions(args.extractions)
    else:
        provider = determine_provider(args)
        model_name = args.model or ("gemini-2.5-flash" if provider == "gemini" else "llama-3.3-70b-versatile")
        print(f"Running in live LLM mode using provider: {provider} (model: {model_name})")

    cases = []
    llm_errors = 0

    for complaint in complaints:
        ticket_id = complaint["ticket_id"]

        issue, order_id, is_error = extract_complaint_info(
            complaint=complaint,
            fixture_lookup=fixture_lookup,
            provider=provider,
            model=args.model
        )

        if is_error:
            llm_errors += 1

        verdict, evidence_ids = investigate_case(
            issue=issue,
            order_id=order_id,
            payments=payments,
            shipments=shipments,
            known_orders=known_orders
        )

        cases.append({
            "ticket_id": ticket_id,
            "order_id": order_id,
            "issue": issue,
            "verdict": verdict,
            "evidence_ids": evidence_ids
        })

    cases.sort(key=lambda c: c["ticket_id"])

    result = {
        "stats": {
            "payments": payment_stats,
            "shipments": shipment_stats,
            "complaints": complaint_stats,
            "llm_errors": llm_errors
        },
        "cases": cases
    }

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.output, mode="w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Successfully generated output: {args.output}")
    print(f"Stats summary: Payments accepted={payment_stats['accepted']}, "
          f"Shipments accepted={shipment_stats['accepted']}, "
          f"Complaints processed={complaint_stats['accepted']}, "
          f"LLM errors={llm_errors}")


if __name__ == "__main__":
    main()
