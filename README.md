<<<<<<< HEAD
# SignalTrace V2 — Evidence-Driven AI Investigator

An evidence-based Python application that investigates e-commerce complaints regarding duplicate charges, repeated payment failures, and shipments created before payment.

## Architecture & Code Structure

The project is structured into clear, beginner-friendly modular files:
- **`data_loader.py`**: Ingests and validates `payments.csv`, `shipments.jsonl`, and `complaints.jsonl`. Tracks counts (`total = accepted + invalid + duplicates`) and handles deduplication.
- **`rules.py`**: Implements domain detection logic for `DOUBLE_CHARGE`, `PAYMENT_FAILURES`, and `SHIPPED_UNPAID`, enforcing deterministic verdicts and evidence tracking.
- **`llm_client.py`**: Interfaces with Google Gemini API (or Groq) in live mode, parses offline fixtures in offline mode, and validates extracted order IDs against complaint text.
- **`main.py`**: Main command-line application that ties together data loading, LLM extraction, incident detection, and output JSON generation.
- **`test_investigator.py`**: Unit tests verifying validation rules, edge cases, and the public smoke dataset.

## Prerequisites

- **Python 3.10+**
- Standard library only — no external dependencies needed.

## Running the Application

### 1. Offline Smoke Test (matches `data/smoke/expected.json`):
```bash
python main.py \
  --payments data/smoke/payments.csv \
  --shipments data/smoke/shipments.jsonl \
  --complaints data/smoke/complaints.jsonl \
  --extractions data/smoke/extractions.json \
  --output smoke_result.json
```

### 2. Required Final Offline Challenge Dataset:
```bash
python main.py \
  --payments data/challenge/payments.csv \
  --shipments data/challenge/shipments.jsonl \
  --complaints data/challenge/complaints.jsonl \
  --extractions data/challenge/extractions.json \
  --output result_offline.json
```

### 3. Live LLM Mode (using Gemini):
Set your API key in the environment and omit `--extractions`:

**PowerShell (Windows):**
```powershell
$env:GEMINI_API_KEY = "your_gemini_api_key_here"
python main.py --payments data/sample/payments.csv --shipments data/sample/shipments.jsonl --complaints data/sample/complaints.jsonl --output result_live.json
```

**Bash / Linux / macOS:**
```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
python main.py --payments data/sample/payments.csv --shipments data/sample/shipments.jsonl --complaints data/sample/complaints.jsonl --output result_live.json
```

### 4. Running Unit Tests:
```bash
python -m unittest test_investigator.py
```
=======
# contenterra
>>>>>>> aa6656b6b2a2b15c54321e17388deca2aab247ff
