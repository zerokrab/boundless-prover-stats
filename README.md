# Boundless Prover Stats

Fetch and analyze order history for any [Boundless Network](https://boundless.network) prover. Pulls data from the Boundless Explorer API and generates CSVs with per-proof details and per-epoch cycle totals.

## Output

| File | Description |
|------|-------------|
| `output/prover_all_proofs.csv` | Every individual proof — epoch, timestamps, cycles, status, prove speed |
| `output/prover_epochs_summary.csv` | Aggregated totals per epoch — cycles, order counts, fulfilled/expired |
| `output/prover_all_orders.json` | Raw JSON backup of all order data |

### Proof CSV columns

| Column | Description |
|--------|-------------|
| `epoch` | Boundless epoch number the order was created in |
| `created_at` | When the order was submitted |
| `fulfilled_at` | When the proof was delivered |
| `locked_at` | When the prover locked the order |
| `request_id` | Unique order identifier |
| `request_status` | `fulfilled` or `expired` |
| `total_cycles` | RISC-V execution cycles for this proof |
| `effective_prove_mhz` | Overall proving speed (MHz) |
| `prover_effective_prove_mhz` | Prover-specific proving speed (MHz) |
| `client_address` | Requestor address |
| `chain_id` | Chain ID (8453 = Base Mainnet) |
| `slashed_at` | Timestamp if prover was slashed, else empty |

## Scripts

### `fetch_orders.py` — Pull all prover orders

Fetches every order for a prover and generates per-proof and per-epoch CSVs.

```bash
export PROVER_ADDRESS=0xYourProverAddressHere

python3 fetch_orders.py

# With a custom limit
PROVER_ADDRESS=0xYourAddress LIMIT=5000 python3 fetch_orders.py

# Filter to a specific epoch range
PROVER_ADDRESS=0xYourAddress EPOCH_START=30 EPOCH_END=50 python3 fetch_orders.py
```

### `fetch_mining_stats.py` — Market vs Mining comparison

Compares market order cycles against PoVW mining cycles per epoch. The prover address (market orders) and miner log ID (PoVW work) may differ for the same operator.

```bash
export PROVER_ADDRESS=0xYourProverAddress
export MINER_LOG_ID=0xYourMinerLogID

python3 fetch_mining_stats.py

# Filter to a specific epoch range
PROVER_ADDRESS=0xProver MINER_LOG_ID=0xMiner EPOCH_START=30 EPOCH_END=50 python3 fetch_mining_stats.py
```

Outputs `output/market_vs_mining.csv` with columns:

| Column | Description |
|--------|-------------|
| `epoch` | Boundless epoch number |
| `mining_cycles` | Total PoVW cycles submitted for this epoch |
| `market_cycles` | Total market order cycles fulfilled this epoch |
| `market_pct_of_mining` | What % of mining work came from market orders |
| `market_orders` | Number of market orders in this epoch |
| `network_pct` | Miner's share of total network work |
| `rewards` | ZKC rewards earned this epoch |

## Requirements

- Python 3.8+
- `curl` (pre-installed on most systems)

No additional Python packages needed — uses only stdlib.

## API Reference

This tool uses the Boundless Explorer REST API (no auth required):

```
GET /api/provers/{address}/orders?limit=N
GET /api/provers/{address}/aggregates/epoch
GET /api/provers/{address}/cumulatives
GET /api/miners/{logId}?limit=N
```

Base URL: `https://explorer.boundless.network`

## Epoch Mapping

Orders are mapped to Boundless epochs using timestamp boundaries from the `/aggregates/epoch` endpoint. Each epoch is approximately 48 hours. The script assigns each order to the epoch that was active at its `created_at` time.

## License

MIT
