# Boundless Prover Stats — Development Guide

Instructions for AI coding assistants working on this repo.

## Project Overview

CLI tools to fetch and analyze Boundless Network prover data from the Explorer API. Pure Python (stdlib only), no database, no framework — just scripts that output CSVs.

## Project Structure

```
boundless-prover-stats/
├── fetch_orders.py          # Pull all market orders for a prover → CSV
├── fetch_mining_stats.py    # Compare market cycles vs PoVW mining cycles per epoch
├── output/                  # Generated files (gitignored)
│   ├── prover_all_proofs.csv
│   ├── prover_epochs_summary.csv
│   ├── prover_all_orders.json
│   └── market_vs_mining.csv
├── AGENTS.md
├── README.md
├── LICENSE
└── .gitignore
```

## Environment Variables

| Variable | Required By | Description |
|----------|------------|-------------|
| `PROVER_ADDRESS` | Both scripts | Prover address on Base Mainnet |
| `MINER_LOG_ID` | `fetch_mining_stats.py` | PoVW miner log ID (may differ from prover address) |
| `LIMIT` | Both scripts | Max orders to fetch (default: 100,000) |
| `EPOCH_START` | Both scripts | Start of epoch range filter (default: 0) |
| `EPOCH_END` | Both scripts | End of epoch range filter (default: 999999) |

## API Endpoints Used

All endpoints are on `https://explorer.boundless.network/api` — no auth required.

| Endpoint | Used By | Returns |
|----------|---------|---------|
| `GET /provers/{addr}/orders?limit=N` | `fetch_orders.py`, `fetch_mining_stats.py` | All market orders with cycles, timestamps, status |
| `GET /provers/{addr}/aggregates/epoch` | Both scripts | Epoch timestamp boundaries for order→epoch mapping |
| `GET /miners/{logId}?limit=N` | `fetch_mining_stats.py` | PoVW mining work per epoch, rewards, network share |

## Key Design Decisions

- **No dependencies** — stdlib only (`json`, `csv`, `subprocess`, `os`). Uses `curl` for HTTP.
- **No database** — outputs are flat CSVs for easy import into notebooks/spreadsheets.
- **Epoch mapping** — orders are assigned to epochs by matching `created_at` timestamps against epoch start boundaries from the aggregates endpoint. This is approximate and may differ slightly from on-chain epoch assignment.
- **Address separation** — prover address (market orders) and miner log ID (PoVW work) are configured independently since they can differ for the same operator.

## Conventions

- Output files go in `output/` (gitignored).
- Never commit real addresses, API keys, or result data to the repo.
- All config is via environment variables, not CLI args or config files.

## Testing

```bash
# Smoke test — fetch a small batch
PROVER_ADDRESS=0xYourAddress LIMIT=10 python3 fetch_orders.py

# Test epoch filtering
PROVER_ADDRESS=0xYourAddress EPOCH_START=50 EPOCH_END=55 python3 fetch_orders.py
```

## Git Workflow

- Always open PRs — do not push directly to `main`.
- Branch naming: `zeroklaw/<branch-name>`.
- Keep this AGENTS.md updated when adding scripts or changing interfaces.
