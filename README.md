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

## Requirements

- Python 3.8+
- `curl` (pre-installed on most systems)

No additional Python packages needed — uses only stdlib.

## Usage

```bash
# Set your prover address
export PROVER_ADDRESS=0xYourProverAddressHere

# Fetch all orders (default limit: 100,000)
python3 fetch_orders.py

# Or with a custom limit
PROVER_ADDRESS=0xYourAddress LIMIT=5000 python3 fetch_orders.py
```

Results are written to the `output/` directory.

## API Reference

This tool uses the Boundless Explorer REST API (no auth required):

```
GET https://explorer.boundless.network/api/provers/{address}/orders?limit=N
GET https://explorer.boundless.network/api/provers/{address}/aggregates/epoch
GET https://explorer.boundless.network/api/provers/{address}/cumulatives
```

## Epoch Mapping

Orders are mapped to Boundless epochs using timestamp boundaries from the `/aggregates/epoch` endpoint. Each epoch is approximately 48 hours. The script assigns each order to the epoch that was active at its `created_at` time.

## License

MIT
