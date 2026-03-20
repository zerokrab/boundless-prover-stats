#!/usr/bin/env python3
"""
Fetch all orders for a Boundless Network prover from the Explorer API.

Outputs:
  - output/prover_all_proofs.csv   — Every individual proof with epoch assignment
  - output/prover_epochs_summary.csv — Aggregated cycles per epoch
  - output/prover_all_orders.json  — Raw JSON backup

Usage:
  PROVER_ADDRESS=0xYourAddress python3 fetch_orders.py
  PROVER_ADDRESS=0xYourAddress LIMIT=5000 python3 fetch_orders.py
  PROVER_ADDRESS=0xYourAddress EPOCH_START=30 EPOCH_END=50 python3 fetch_orders.py
"""
import json
import os
import subprocess
import csv
import sys
from collections import Counter

PROVER = os.environ.get("PROVER_ADDRESS")
if not PROVER:
    print("Error: PROVER_ADDRESS environment variable is required.")
    print("Usage: PROVER_ADDRESS=0xYourAddress python3 fetch_orders.py")
    sys.exit(1)

LIMIT = int(os.environ.get("LIMIT", "100000"))
EPOCH_START = int(os.environ.get("EPOCH_START", "0"))
EPOCH_END = int(os.environ.get("EPOCH_END", "999999"))
BASE_URL = f"https://explorer.boundless.network/api/provers/{PROVER}"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def api_get(path, params="", timeout=120):
    """Fetch JSON from the Boundless Explorer API with download progress."""
    url = f"{BASE_URL}/{path}" if path else BASE_URL
    if params:
        url += f"?{params}"
    proc = subprocess.Popen(
        ["curl", "-s", "--max-time", str(timeout), url, "-H", "Accept: application/json"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    chunks = []
    total = 0
    while True:
        chunk = proc.stdout.read(65536)
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        mb = total / (1024 * 1024)
        sys.stdout.write(f"\r  Downloading... {mb:.1f} MB")
        sys.stdout.flush()
    if total > 0:
        sys.stdout.write(f"\r  Downloaded {total / (1024 * 1024):.1f} MB     \n")
        sys.stdout.flush()
    proc.wait()
    if proc.returncode != 0:
        stderr = proc.stderr.read().decode()
        print(f"  curl error (exit {proc.returncode}): {stderr[:200]}")
        return None
    raw = b"".join(chunks).decode()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  JSON error: {e}")
        print(f"  Response: {raw[:200]}")
        return None


def fetch_epoch_map():
    """Fetch epoch aggregates to build epoch timestamp boundaries."""
    print("Fetching epoch aggregates...")
    data = api_get("aggregates/epoch", timeout=30)
    if not data or not isinstance(data, list):
        print("  Warning: Could not fetch epoch aggregates. Epoch mapping will be empty.")
        return []

    print(f"  Found {len(data)} epoch records")
    epoch_map = []
    for item in data:
        epoch_num = item.get("epoch_number_start")
        ts_iso = item.get("timestamp_iso", "")
        if ts_iso and epoch_num is not None:
            epoch_map.append((epoch_num, ts_iso))
    epoch_map.sort(key=lambda x: x[1])
    return epoch_map


def find_epoch(created_at_iso, epoch_map):
    """Map an order's creation time to an epoch number."""
    if not epoch_map:
        return None
    assigned = epoch_map[0][0]
    for epoch_num, start_ts in epoch_map:
        if created_at_iso >= start_ts:
            assigned = epoch_num
        else:
            break
    return assigned


def main():
    # Step 1: Fetch all orders
    print(f"[1/4] Fetching orders for prover {PROVER[:10]}...{PROVER[-6:]} (limit={LIMIT})...")
    data = api_get("orders", f"limit={LIMIT}", timeout=180)
    if not data:
        print("Error: Failed to fetch orders.")
        sys.exit(1)

    orders = data.get("orders", [])
    has_more = data.get("hasMore", False)
    print(f"  ✓ {len(orders)} orders (hasMore={has_more})")

    if not orders:
        print("No orders found for this prover.")
        sys.exit(0)

    if has_more:
        print(f"  Warning: There are more orders than the limit ({LIMIT}). Increase LIMIT env var.")

    # Step 2: Fetch epoch boundaries
    print(f"\n[2/4] Fetching epoch boundaries...")
    epoch_map = fetch_epoch_map()

    # Step 3: Sort, filter by epoch range, and analyze
    print(f"\n[3/4] Processing orders...")
    orders.sort(key=lambda o: o.get("created_at_iso", ""))

    # Apply epoch range filter
    if EPOCH_START > 0 or EPOCH_END < 999999:
        pre_filter = len(orders)
        orders = [
            o for o in orders
            if EPOCH_START <= (find_epoch(o.get("created_at_iso", ""), epoch_map) or 0) <= EPOCH_END
        ]
        print(f"  Filtered to epochs {EPOCH_START}–{EPOCH_END}: {pre_filter} → {len(orders)} orders")

    dates = [o.get("created_at_iso", "") for o in orders]
    statuses = Counter(o.get("request_status", "unknown") for o in orders)
    total_cycles = sum(int(o.get("total_cycles") or 0) for o in orders)

    print(f"\n=== Summary ===")
    print(f"  Date range: {dates[0]} to {dates[-1]}")
    print(f"  Statuses: {dict(statuses)}")
    print(f"  Total cycles: {total_cycles:,} ({total_cycles / 1e12:.2f}T)")

    # Step 4: Write output files
    print(f"\n[4/4] Writing output files...")
    proofs_csv = os.path.join(OUTPUT_DIR, "prover_all_proofs.csv")
    with open(proofs_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "epoch", "created_at", "fulfilled_at", "locked_at",
            "request_id", "request_status", "total_cycles",
            "effective_prove_mhz", "prover_effective_prove_mhz",
            "client_address", "chain_id", "slashed_at",
        ])
        for o in orders:
            epoch = find_epoch(o.get("created_at_iso", ""), epoch_map)
            writer.writerow([
                epoch,
                o.get("created_at_iso", ""),
                o.get("fulfilled_at_iso", ""),
                o.get("locked_at_iso", ""),
                o.get("request_id", ""),
                o.get("request_status", ""),
                o.get("total_cycles") or "0",
                o.get("effective_prove_mhz", ""),
                o.get("prover_effective_prove_mhz", ""),
                o.get("client_address", ""),
                o.get("chain_id", ""),
                o.get("slashed_at", ""),
            ])
    print(f"\n  Saved {len(orders)} proofs to {proofs_csv}")

    # Step 5: Write epoch summary CSV
    epoch_cycles = {}
    epoch_counts = {}
    epoch_statuses = {}
    for o in orders:
        epoch = find_epoch(o.get("created_at_iso", ""), epoch_map)
        if epoch is None:
            continue
        cycles = int(o.get("total_cycles") or 0)
        status = o.get("request_status", "unknown")
        epoch_cycles[epoch] = epoch_cycles.get(epoch, 0) + cycles
        epoch_counts[epoch] = epoch_counts.get(epoch, 0) + 1
        if epoch not in epoch_statuses:
            epoch_statuses[epoch] = Counter()
        epoch_statuses[epoch][status] += 1

    summary_csv = os.path.join(OUTPUT_DIR, "prover_epochs_summary.csv")
    with open(summary_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "epoch", "total_cycles", "total_cycles_T",
            "num_orders", "fulfilled", "expired", "other",
        ])
        for epoch in sorted(epoch_cycles.keys()):
            cycles = epoch_cycles[epoch]
            count = epoch_counts[epoch]
            st = epoch_statuses.get(epoch, Counter())
            fulfilled = st.get("fulfilled", 0)
            expired = st.get("expired", 0)
            other = count - fulfilled - expired
            writer.writerow([
                epoch, cycles, f"{cycles / 1e12:.6f}",
                count, fulfilled, expired, other,
            ])

    print(f"  Saved epoch summary to {summary_csv}")

    # Step 6: Write raw JSON
    json_path = os.path.join(OUTPUT_DIR, "prover_all_orders.json")
    with open(json_path, "w") as f:
        json.dump(orders, f)
    print(f"  Saved raw JSON to {json_path}")

    # Step 7: Print epoch table
    print(f"\n=== Cycles per Epoch ===")
    for epoch in sorted(epoch_cycles.keys()):
        cycles = epoch_cycles[epoch]
        count = epoch_counts[epoch]
        st = epoch_statuses.get(epoch, Counter())
        print(
            f"  Epoch {epoch:>3}: {cycles:>20,} ({cycles / 1e12:.3f}T)"
            f" | {count:>5} orders"
            f" | ✅{st.get('fulfilled', 0)} ❌{st.get('expired', 0)}"
        )

    print(f"\nDone! Results in {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
