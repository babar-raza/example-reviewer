"""
LLM Telemetry Monitoring Script

Analyzes LLM usage across pipeline runs to track:
- Token consumption and estimated costs
- Model performance (latency, success rates)
- Provider distribution (custom endpoint vs Ollama fallback)
- Model tier usage breakdown

Usage:
    # Monitor latest run
    python scripts/ops/monitor_llm_telemetry.py

    # Monitor specific run
    python scripts/ops/monitor_llm_telemetry.py --run-id 41d1b814d248066b

    # Show cost estimates
    python scripts/ops/monitor_llm_telemetry.py --show-costs

    # Compare runs
    python scripts/ops/monitor_llm_telemetry.py --compare run1_id run2_id
"""

import sys
import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')


@dataclass
class LLMUsageStats:
    """LLM usage statistics for a run."""
    run_id: str
    family: str
    timestamp: str

    # Token usage
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int

    # Performance
    total_calls: int
    successful_calls: int
    failed_calls: int
    avg_latency_ms: float

    # Provider breakdown
    remote_calls: int
    ollama_calls: int
    fallback_rate: float

    # Model breakdown
    models_used: Dict[str, int]

    # Tier breakdown
    small_tier_calls: int
    medium_tier_calls: int
    large_tier_calls: int


def get_db_connection(db_path: str = "data/example_reviewer.db") -> sqlite3.Connection:
    """Get database connection."""
    if not Path(db_path).exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_latest_run_id(conn: sqlite3.Connection) -> Optional[str]:
    """Get the most recent run ID."""
    cursor = conn.execute("""
        SELECT run_id FROM telemetry_runs
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    return row['run_id'] if row else None


def get_run_metadata(conn: sqlite3.Connection, run_id: str) -> Optional[Dict]:
    """Get metadata for a specific run."""
    cursor = conn.execute("""
        SELECT run_id, family, timestamp, status, metrics_json
        FROM telemetry_runs
        WHERE run_id = ?
    """, (run_id,))
    row = cursor.fetchone()

    if not row:
        return None

    return {
        'run_id': row['run_id'],
        'family': row['family'],
        'timestamp': row['timestamp'],
        'status': row['status'],
        'metrics': json.loads(row['metrics_json']) if row['metrics_json'] else {}
    }


def analyze_llm_usage(conn: sqlite3.Connection, run_id: str) -> Optional[LLMUsageStats]:
    """Analyze LLM usage for a specific run."""
    metadata = get_run_metadata(conn, run_id)
    if not metadata:
        return None

    # Get LLM telemetry from metrics_json
    metrics = metadata.get('metrics', {})
    llm_stats = metrics.get('llm_stats', {})

    if not llm_stats:
        # Try to get from telemetry_events table (legacy)
        cursor = conn.execute("""
            SELECT event_data_json FROM telemetry_events
            WHERE run_id = ? AND event_type = 'llm_call'
        """, (run_id,))

        events = [json.loads(row['event_data_json']) for row in cursor.fetchall()]

        # Aggregate stats from events
        total_tokens = sum(e.get('total_tokens', 0) for e in events)
        prompt_tokens = sum(e.get('prompt_tokens', 0) for e in events)
        completion_tokens = sum(e.get('completion_tokens', 0) for e in events)

        successful = sum(1 for e in events if e.get('status') == 'success')
        failed = len(events) - successful

        latencies = [e.get('latency_ms', 0) for e in events if e.get('latency_ms')]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        models_used = {}
        for e in events:
            model = e.get('model', 'unknown')
            models_used[model] = models_used.get(model, 0) + 1

        remote_calls = sum(1 for e in events if 'llm.professionalize.com' in e.get('provider', ''))
        ollama_calls = len(events) - remote_calls

    else:
        # Use aggregated stats from metrics_json
        total_tokens = llm_stats.get('total_tokens', 0)
        prompt_tokens = llm_stats.get('prompt_tokens', 0)
        completion_tokens = llm_stats.get('completion_tokens', 0)

        total_calls = llm_stats.get('total_calls', 0)
        successful = llm_stats.get('successful_calls', 0)
        failed = total_calls - successful

        avg_latency = llm_stats.get('avg_latency_ms', 0)

        models_used = llm_stats.get('models_used', {})
        remote_calls = llm_stats.get('remote_calls', 0)
        ollama_calls = llm_stats.get('ollama_calls', 0)

    # Calculate fallback rate
    total_calls = remote_calls + ollama_calls
    fallback_rate = (ollama_calls / total_calls * 100) if total_calls > 0 else 0

    return LLMUsageStats(
        run_id=run_id,
        family=metadata['family'],
        timestamp=metadata['timestamp'],
        total_tokens=total_tokens,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_calls=total_calls,
        successful_calls=successful,
        failed_calls=failed,
        avg_latency_ms=avg_latency,
        remote_calls=remote_calls,
        ollama_calls=ollama_calls,
        fallback_rate=fallback_rate,
        models_used=models_used,
        small_tier_calls=0,  # Would need to parse from events
        medium_tier_calls=0,
        large_tier_calls=0
    )


def estimate_cost(stats: LLMUsageStats, price_per_1k_tokens: float = 0.001) -> Tuple[float, str]:
    """
    Estimate cost based on token usage.

    Default pricing is placeholder - update based on your provider's actual rates.
    """
    cost_usd = (stats.total_tokens / 1000) * price_per_1k_tokens

    # Generate cost breakdown
    breakdown = f"""
Cost Estimate (at ${price_per_1k_tokens:.4f} per 1k tokens):
  Prompt tokens:     {stats.prompt_tokens:,} × ${price_per_1k_tokens:.4f} = ${(stats.prompt_tokens/1000) * price_per_1k_tokens:.4f}
  Completion tokens: {stats.completion_tokens:,} × ${price_per_1k_tokens:.4f} = ${(stats.completion_tokens/1000) * price_per_1k_tokens:.4f}
  ────────────────────────────────────────────────────
  TOTAL:             {stats.total_tokens:,} tokens = ${cost_usd:.4f}
"""

    return cost_usd, breakdown


def print_stats(stats: LLMUsageStats, show_costs: bool = False):
    """Print LLM usage statistics."""
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print(f"║                          LLM Usage Report                                    ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    print(f"Run ID:    {stats.run_id}")
    print(f"Family:    {stats.family}")
    print(f"Timestamp: {stats.timestamp}")
    print()

    # Token usage
    print("Token Usage:")
    print(f"  Total tokens:      {stats.total_tokens:,}")
    print(f"  Prompt tokens:     {stats.prompt_tokens:,}")
    print(f"  Completion tokens: {stats.completion_tokens:,}")
    print()

    # Performance
    print("Performance:")
    print(f"  Total calls:       {stats.total_calls}")
    print(f"  Successful:        {stats.successful_calls} ({stats.successful_calls/stats.total_calls*100:.1f}%)")
    print(f"  Failed:            {stats.failed_calls} ({stats.failed_calls/stats.total_calls*100:.1f}%)")
    print(f"  Avg latency:       {stats.avg_latency_ms:.0f}ms")
    print()

    # Provider distribution
    print("Provider Distribution:")
    print(f"  Remote endpoint:   {stats.remote_calls} calls ({stats.remote_calls/stats.total_calls*100:.1f}%)")
    print(f"  Ollama fallback:   {stats.ollama_calls} calls ({stats.ollama_calls/stats.total_calls*100:.1f}%)")
    print(f"  Fallback rate:     {stats.fallback_rate:.1f}%")
    print()

    # Models used
    if stats.models_used:
        print("Models Used:")
        for model, count in sorted(stats.models_used.items(), key=lambda x: x[1], reverse=True):
            pct = count / stats.total_calls * 100
            print(f"  {model:50s} {count:3d} calls ({pct:.1f}%)")
        print()

    # Cost estimate
    if show_costs:
        cost, breakdown = estimate_cost(stats)
        print(breakdown)
        print(f"Note: This is an ESTIMATE. Update pricing in the script for accuracy.")
        print()


def compare_runs(conn: sqlite3.Connection, run_id1: str, run_id2: str):
    """Compare two runs side by side."""
    stats1 = analyze_llm_usage(conn, run_id1)
    stats2 = analyze_llm_usage(conn, run_id2)

    if not stats1 or not stats2:
        print("Error: Could not load one or both runs")
        return

    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print(f"║                          Run Comparison                                      ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()

    print(f"{'Metric':<30s} {'Run 1':>20s} {'Run 2':>20s} {'Difference':>20s}")
    print("─" * 95)

    print(f"{'Run ID':<30s} {stats1.run_id[:20]:>20s} {stats2.run_id[:20]:>20s} {'-':>20s}")
    print(f"{'Family':<30s} {stats1.family:>20s} {stats2.family:>20s} {'-':>20s}")
    print()

    # Token comparison
    print(f"{'Total tokens':<30s} {stats1.total_tokens:>20,} {stats2.total_tokens:>20,} {stats2.total_tokens - stats1.total_tokens:>+20,}")
    print(f"{'Prompt tokens':<30s} {stats1.prompt_tokens:>20,} {stats2.prompt_tokens:>20,} {stats2.prompt_tokens - stats1.prompt_tokens:>+20,}")
    print(f"{'Completion tokens':<30s} {stats1.completion_tokens:>20,} {stats2.completion_tokens:>20,} {stats2.completion_tokens - stats1.completion_tokens:>+20,}")
    print()

    # Performance comparison
    print(f"{'Total calls':<30s} {stats1.total_calls:>20} {stats2.total_calls:>20} {stats2.total_calls - stats1.total_calls:>+20}")
    print(f"{'Success rate':<30s} {stats1.successful_calls/stats1.total_calls*100:>19.1f}% {stats2.successful_calls/stats2.total_calls*100:>19.1f}% {(stats2.successful_calls/stats2.total_calls - stats1.successful_calls/stats1.total_calls)*100:>+19.1f}%")
    print(f"{'Avg latency (ms)':<30s} {stats1.avg_latency_ms:>20.0f} {stats2.avg_latency_ms:>20.0f} {stats2.avg_latency_ms - stats1.avg_latency_ms:>+20.0f}")
    print()

    # Provider comparison
    print(f"{'Remote calls':<30s} {stats1.remote_calls:>20} {stats2.remote_calls:>20} {stats2.remote_calls - stats1.remote_calls:>+20}")
    print(f"{'Fallback rate':<30s} {stats1.fallback_rate:>19.1f}% {stats2.fallback_rate:>19.1f}% {stats2.fallback_rate - stats1.fallback_rate:>+19.1f}%")
    print()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Monitor LLM usage and costs')
    parser.add_argument('--run-id', help='Specific run ID to analyze')
    parser.add_argument('--show-costs', action='store_true', help='Show cost estimates')
    parser.add_argument('--compare', nargs=2, metavar=('RUN1', 'RUN2'), help='Compare two runs')
    parser.add_argument('--db-path', default='data/example_reviewer.db', help='Path to database')
    parser.add_argument('--list-runs', action='store_true', help='List recent runs')

    args = parser.parse_args()

    conn = get_db_connection(args.db_path)

    # List runs
    if args.list_runs:
        cursor = conn.execute("""
            SELECT run_id, family, timestamp, status
            FROM telemetry_runs
            ORDER BY timestamp DESC
            LIMIT 20
        """)

        print("Recent runs:")
        print(f"{'Run ID':<18s} {'Family':<10s} {'Timestamp':<25s} {'Status':<15s}")
        print("─" * 75)
        for row in cursor:
            print(f"{row['run_id']:<18s} {row['family']:<10s} {row['timestamp']:<25s} {row['status']:<15s}")
        return

    # Compare runs
    if args.compare:
        compare_runs(conn, args.compare[0], args.compare[1])
        return

    # Get run ID
    run_id = args.run_id
    if not run_id:
        run_id = get_latest_run_id(conn)
        if not run_id:
            print("No runs found in database")
            return
        print(f"Using latest run: {run_id}")
        print()

    # Analyze and display stats
    stats = analyze_llm_usage(conn, run_id)
    if not stats:
        print(f"Run {run_id} not found")
        return

    print_stats(stats, show_costs=args.show_costs)

    conn.close()


if __name__ == "__main__":
    main()
