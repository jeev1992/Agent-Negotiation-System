"""
00_BASELINE - The Problem We're Solving
=======================================

This module contains the INTENTIONALLY BROKEN naive implementation.

Run to see the failures:
    python -m 00_baseline.naive_negotiation

The baseline demonstrates:
1. Ambiguous message parsing (regex on free-form text)
2. No termination guarantee (while True loops)
3. Silent failures (errors that don't crash)
4. Hardcoded values (no grounded context)
5. No observability (can't see what happened)

The 10-layer architecture (layers 0-9) fixes ALL of these problems.
"""

from .naive_negotiation import (
    NaiveBuyer,
    NaiveSeller,
    run_naive_negotiation,
    demonstrate_failure_modes,
)
