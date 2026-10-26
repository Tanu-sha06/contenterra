# Implementation Notes

### Approach
The solution is built cleanly and modularly using Python standard library components across distinct, beginner-friendly files:
- `data_loader.py`: Ingests and validates CSV/JSONL records, strictly checking UTC timestamps, amount boundaries, and non-empty required fields. Deduplication retains the first valid record without allowing invalid entries to reserve IDs.
- `rules.py`: Evaluates the three evidence detection signals (`DOUBLE_CHARGE`, `PAYMENT_FAILURES`, and `SHIPPED_UNPAID`) and determines deterministic verdicts (`SIGNAL_FOUND`, `NOT_VERIFIED`, `INSUFFICIENT_DATA`, `NOT_APPLICABLE`).
- `llm_client.py`: Handles structured extraction via Gemini API in live mode with rate-limit retry, and loads pre-supplied fixtures in offline mode. Strictly validates order IDs against customer messages.
- `main.py`: Coordinates the workflow and CLI flags.

### Tests Performed
- **Unit Tests (`test_investigator.py`)**: Verified timestamp parsing, order ID regex matching, duplicate charge pairing, 10-minute failure interval boundaries, and identical timestamp edge cases.
- **Offline Smoke Test**: Exactly matched `data/smoke/expected.json` (100% equivalence).
- **Challenge Offline Run**: Processed `data/challenge/` into `result_offline.json` (46 cases, 0 LLM errors, all data source balance equations verified).
- **Live LLM Run**: Executed live inference on `data/sample/` using Gemini 2.5 Flash to generate `result_live.json`.

### Known Limitations
Live LLM inference depends on network availability and provider rate limits (e.g., Gemini free-tier per-minute quotas).

### Relevant Technical Risk
Customer messages and support notes are untrusted inputs subject to prompt injection. The design mitigates this by instructing the LLM to ignore embedded commands, while Python independently validates order IDs and controls all final verdicts.
