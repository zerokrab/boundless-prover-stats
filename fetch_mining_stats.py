#!/usr/bin/env python3
"""
Compare market order cycles vs PoVW mining cycles per epoch.

Fetches:
  1. Market order data for a prover address (from /api/provers/)
  2. PoVW mining data for a miner log ID (from /api/miners/)

Then computes what % of mining cycles came from market orders each epoch.

Outputs:
  - output/market_vs_mining.csv — Per-epoch comparison

Usage:
  PROVER_ADDRESS=0xProver MINER_LOG_ID=0xMiner python3 fetch_mining_stats.py

Note: The prover address and miner log ID may differ for the same operator.
"""
import json
import os
import subprocess
import csv
import sys
from collections import Counter

PROVER = os.environ.get("PROVER_ADDRESS")
MINER = os.environ.get("MINER_LOG_ID")

if not PROVER or not MINER:
    print("Error: Both PROVER_ADDRESS and MINER_LOG_ID environment variables are required.")
    print("Usage: PROVER_ADDRESS=0xProver MINER_LOG_ID=0xMiner python3 fetch_mining_stats.py")
    sys.exit(1)

LIMIT = int(os.environ.get("LIMIT", "100000"))
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

EXPLORER = "https://explorer.boundless.network/api"


def api_get(url, timeout=120):
    """Fetch JSON from the Boundless Explorer API."""
    result = subprocess.run(
        ["curl", "-s", "--max-time", str(timeout), url, "-H", "Accept: application/json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def fetch_mining_epochs():
    """Fetch all PoVW mining epoch data for the miner."""
    print(f"Fetching mining data for miner {MINER[:10]}...{MINER[-6:]}...")
    data = api_get(f"{EXPLORER}/miners/{MINER}?limit=1000", timeout=30)
    if not data:
        print("  Error: Failed to fetch mining data.")
        return {}, {}

    entries = data.get("entries", [])
    summary = data.get("summary", {})
    print(f"  Found {len(entries)} epochs, total mining cycles: {summary.get('total_work_submitted_formatted', 'N/A')}")

    # Build epoch -> mining cycles map
    mining_by_epoch = {}
    for e in entries:
        epoch = e["epoch"]
        mining_by_epoch[epoch] = {
            "work_submitted": int(e["work_submitted"]),
            "percentage": e.get("percentage", 0),
            "actual_rewards": e.get("actual_rewards_formatted", ""),
            "uncapped_rewards": e.get("uncapped_rewards_formatted", ""),
            "is_capped": e.get("is_capped", False),
        }

    return mining_by_epoch, summary


def fetch_market_epochs():
    """Fetch market order data and aggregate cycles per epoch."""
    print(f"\nFetching market orders for prover {PROVER[:10]}...{PROVER[-6:]}...")

    # First get epoch aggregates for timestamp mapping
    agg_data = api_get(f"{EXPLORER}/provers/{PROVER}/aggregates/epoch", timeout=30)
    epoch_map = []
    if agg_data and isinstance(agg_data, list):
        for item in agg_data:
            epoch_num = item.get("epoch_number_start")
            ts_iso = item.get("timestamp_iso", "")
            if ts_iso and epoch_num is not None:
                epoch_map.append((epoch_num, ts_iso))
        epoch_map.sort(key=lambda x: x[1])

    # Fetch all orders
    data = api_get(f"{EXPLORER}/provers/{PROVER}/orders?limit={LIMIT}", timeout=180)
    if not data:
        print("  Error: Failed to fetch orders.")
        return {}

    orders = data.get("orders", [])
    has_more = data.get("hasMore", False)
    print(f"  Found {len(orders)} orders (hasMore={has_more})")

    if has_more:
        print(f"  Warning: More orders exist. Increase LIMIT env var (current={LIMIT}).")

    # Aggregate by epoch
    def find_epoch(created_at_iso):
        if not epoch_map:
            return None
        assigned = epoch_map[0][0]
        for epoch_num, start_ts in epoch_map:
            if created_at_iso >= start_ts:
                assigned = epoch_num
            else:
                break
        return assigned

    market_by_epoch = {}
    for o in orders:
        epoch = find_epoch(o.get("created_at_iso", ""))
        if epoch is None:
            continue
        cycles = int(o.get("total_cycles") or 0)
        status = o.get("request_status", "unknown")
        if epoch not in market_by_epoch:
            market_by_epoch[epoch] = {"cycles": 0, "orders": 0, "fulfilled": 0, "expired": 0}
        market_by_epoch[epoch]["cycles"] += cycles
        market_by_epoch[epoch]["orders"] += 1
        if status == "fulfilled":
            market_by_epoch[epoch]["fulfilled"] += 1
        elif status == "expired":
            market_by_epoch[epoch]["expired"] += 1

    return market_by_epoch


def main():
    mining_by_epoch, mining_summary = fetch_mining_epochs()
    market_by_epoch = fetch_market_epochs()

    # Combine all epoch numbers
    all_epochs = sorted(set(list(mining_by_epoch.keys()) + list(market_by_epoch.keys())))

    if not all_epochs:
        print("\nNo data found!")
        sys.exit(1)

    # Write CSV
    csv_path = os.path.join(OUTPUT_DIR, "market_vs_mining.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "epoch",
            "mining_cycles", "mining_cycles_T",
            "market_cycles", "market_cycles_T",
            "market_pct_of_mining",
            "market_orders", "market_fulfilled", "market_expired",
            "network_pct", "rewards",
        ])
        for epoch in all_epochs:
            mining = mining_by_epoch.get(epoch, {})
            market = market_by_epoch.get(epoch, {})

            mining_cycles = mining.get("work_submitted", 0)
            market_cycles = market.get("cycles", 0)

            if mining_cycles > 0:
                pct = (market_cycles / mining_cycles) * 100
            elif market_cycles > 0:
                pct = float("inf")
            else:
                pct = 0

            writer.writerow([
                epoch,
                mining_cycles, f"{mining_cycles / 1e12:.6f}",
                market_cycles, f"{market_cycles / 1e12:.6f}",
                f"{pct:.2f}" if pct != float("inf") else "N/A",
                market.get("orders", 0),
                market.get("fulfilled", 0),
                market.get("expired", 0),
                mining.get("percentage", ""),
                mining.get("actual_rewards", ""),
            ])

    print(f"\nSaved comparison to {csv_path}")

    # Print table
    print(f"\n{'Epoch':>6} | {'Mining Cycles':>18} | {'Market Cycles':>18} | {'Market %':>9} | {'Orders':>7} | {'Network %':>10}")
    print("-" * 90)

    total_mining = 0
    total_market = 0
    for epoch in all_epochs:
        mining = mining_by_epoch.get(epoch, {})
        market = market_by_epoch.get(epoch, {})

        mining_cycles = mining.get("work_submitted", 0)
        market_cycles = market.get("cycles", 0)
        total_mining += mining_cycles
        total_market += market_cycles

        if mining_cycles > 0:
            pct = (market_cycles / mining_cycles) * 100
            pct_str = f"{pct:.1f}%"
        elif market_cycles > 0:
            pct_str = "N/A"
        else:
            pct_str = "—"

        net_pct = mining.get("percentage", "")
        net_str = f"{net_pct}%" if net_pct else ""

        print(
            f"{epoch:>6} | {mining_cycles:>18,} | {market_cycles:>18,} | {pct_str:>9}"
            f" | {market.get('orders', 0):>7} | {net_str:>10}"
        )

    print("-" * 90)
    if total_mining > 0:
        total_pct = (total_market / total_mining) * 100
        print(
            f"{'TOTAL':>6} | {total_mining:>18,} | {total_market:>18,} | {total_pct:.1f}%"
            f" | {'':>7} | {'':>10}"
        )
    print(f"\n  Mining total: {total_mining / 1e12:.2f}T cycles")
    print(f"  Market total: {total_market / 1e12:.2f}T cycles")
    if total_mining > 0:
        print(f"  Market as % of mining: {(total_market / total_mining) * 100:.1f}%")


if __name__ == "__main__":
    main()
