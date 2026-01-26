"""
Evaluation Dataset
==================

Test scenarios for evaluating the negotiation system.
These will be uploaded to LangSmith as a dataset.
"""

from typing import List, Dict, Any

# Dataset name in LangSmith
DATASET_NAME = "negotiation-scenarios"
DATASET_DESCRIPTION = "Test scenarios for agent negotiation system evaluation"


# Each scenario defines inputs and expected outputs
NEGOTIATION_SCENARIOS: List[Dict[str, Any]] = [
    # Easy cases - should always agree
    {
        "name": "easy_wide_margin",
        "inputs": {
            "buyer_max": 500.0,
            "seller_min": 300.0,
            "seller_asking": 450.0,
            "max_turns": 10,
        },
        "expected": {
            "should_agree": True,
            "min_fair_price": 350.0,  # 30% from seller min
            "max_fair_price": 450.0,  # 70% from seller min
            "max_acceptable_turns": 6,
        },
        "tags": ["easy", "wide_margin"],
    },
    {
        "name": "easy_medium_margin",
        "inputs": {
            "buyer_max": 450.0,
            "seller_min": 350.0,
            "seller_asking": 500.0,
            "max_turns": 10,
        },
        "expected": {
            "should_agree": True,
            "min_fair_price": 365.0,
            "max_fair_price": 435.0,
            "max_acceptable_turns": 7,
        },
        "tags": ["easy", "medium_margin"],
    },
    
    # Tight margins - should agree but might take more turns
    {
        "name": "tight_margin_small",
        "inputs": {
            "buyer_max": 360.0,
            "seller_min": 350.0,
            "seller_asking": 400.0,
            "max_turns": 10,
        },
        "expected": {
            "should_agree": True,
            "min_fair_price": 350.0,
            "max_fair_price": 360.0,
            "max_acceptable_turns": 8,
        },
        "tags": ["tight", "small_margin"],
    },
    {
        "name": "tight_margin_exact",
        "inputs": {
            "buyer_max": 350.0,
            "seller_min": 350.0,
            "seller_asking": 400.0,
            "max_turns": 10,
        },
        "expected": {
            "should_agree": True,
            "min_fair_price": 350.0,
            "max_fair_price": 350.0,
            "max_acceptable_turns": 10,
        },
        "tags": ["tight", "exact_match"],
    },
    
    # No overlap - should NOT agree
    {
        "name": "no_overlap_clear",
        "inputs": {
            "buyer_max": 200.0,
            "seller_min": 400.0,
            "seller_asking": 500.0,
            "max_turns": 10,
        },
        "expected": {
            "should_agree": False,
            "min_fair_price": None,
            "max_fair_price": None,
            "max_acceptable_turns": 10,  # Should exhaust turns
        },
        "tags": ["impossible", "no_overlap"],
    },
    {
        "name": "no_overlap_close",
        "inputs": {
            "buyer_max": 340.0,
            "seller_min": 350.0,
            "seller_asking": 400.0,
            "max_turns": 10,
        },
        "expected": {
            "should_agree": False,
            "min_fair_price": None,
            "max_fair_price": None,
            "max_acceptable_turns": 10,
        },
        "tags": ["impossible", "close_but_no"],
    },
    
    # Stress tests
    {
        "name": "stress_many_turns",
        "inputs": {
            "buyer_max": 400.0,
            "seller_min": 350.0,
            "seller_asking": 600.0,  # High starting price
            "max_turns": 15,
        },
        "expected": {
            "should_agree": True,
            "min_fair_price": 357.5,
            "max_fair_price": 392.5,
            "max_acceptable_turns": 10,
        },
        "tags": ["stress", "high_asking"],
    },
    {
        "name": "stress_few_turns",
        "inputs": {
            "buyer_max": 450.0,
            "seller_min": 350.0,
            "seller_asking": 500.0,
            "max_turns": 3,  # Very few turns
        },
        "expected": {
            "should_agree": True,  # Should still agree with good strategy
            "min_fair_price": 350.0,
            "max_fair_price": 450.0,
            "max_acceptable_turns": 3,
        },
        "tags": ["stress", "few_turns"],
    },
    
    # Edge cases
    {
        "name": "edge_zero_min",
        "inputs": {
            "buyer_max": 100.0,
            "seller_min": 0.0,
            "seller_asking": 150.0,
            "max_turns": 10,
        },
        "expected": {
            "should_agree": True,
            "min_fair_price": 30.0,
            "max_fair_price": 70.0,
            "max_acceptable_turns": 6,
        },
        "tags": ["edge", "zero_min"],
    },
    {
        "name": "edge_high_values",
        "inputs": {
            "buyer_max": 50000.0,
            "seller_min": 35000.0,
            "seller_asking": 60000.0,
            "max_turns": 10,
        },
        "expected": {
            "should_agree": True,
            "min_fair_price": 39500.0,
            "max_fair_price": 45500.0,
            "max_acceptable_turns": 7,
        },
        "tags": ["edge", "high_values"],
    },
]


def get_scenarios_by_tag(tag: str) -> List[Dict[str, Any]]:
    """Get all scenarios with a specific tag."""
    return [s for s in NEGOTIATION_SCENARIOS if tag in s.get("tags", [])]


def get_all_inputs() -> List[Dict[str, Any]]:
    """Get just the inputs for all scenarios."""
    return [s["inputs"] for s in NEGOTIATION_SCENARIOS]


def get_scenario_by_name(name: str) -> Dict[str, Any]:
    """Get a scenario by name."""
    for s in NEGOTIATION_SCENARIOS:
        if s["name"] == name:
            return s
    raise ValueError(f"Scenario '{name}' not found")
