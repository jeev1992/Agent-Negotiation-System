"""
LangSmith Evaluation Runner
===========================

Runs negotiation scenarios and evaluates them using LangSmith.

Usage:
    python -m 11_evaluation.langsmith.run_evaluation              # Run locally
    python -m 11_evaluation.langsmith.run_evaluation --upload     # Upload to LangSmith
    python -m 11_evaluation.langsmith.run_evaluation --experiment # Run as experiment
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .dataset import NEGOTIATION_SCENARIOS, DATASET_NAME, DATASET_DESCRIPTION
from .evaluators import (
    agreement_evaluator,
    fairness_evaluator,
    efficiency_evaluator,
    protocol_evaluator,
    overall_evaluator,
    ALL_EVALUATORS,
)


# ============================================================================
# Environment Setup
# ============================================================================

def setup_environment():
    """Set up API keys from environment or defaults."""
    # Enable LangSmith tracing
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "negotiation-evaluation"
    
    # Check for required keys
    if not os.getenv("LANGCHAIN_API_KEY"):
        print("Warning: LANGCHAIN_API_KEY not set. Set it for LangSmith features.")
        print("  export LANGCHAIN_API_KEY='lsv2_...'")


# ============================================================================
# Run Negotiation (Target Function)
# ============================================================================

def run_negotiation_for_eval(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a single negotiation with given inputs.
    
    This is the "target function" that LangSmith will evaluate.
    """
    import importlib.util
    
    # Dynamically import the runtime
    def import_layer(layer_name: str):
        folder_path = project_root / layer_name
        init_path = folder_path / "__init__.py"
        spec = importlib.util.spec_from_file_location(layer_name, init_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[layer_name] = module
        spec.loader.exec_module(module)
        return module
    
    # Import required modules
    runtime_module = import_layer("10_runtime")
    
    # Create runtime with quiet mode
    config = runtime_module.RuntimeConfig(
        mode="demo",
        strategy="rule",
        verbose=False,
    )
    
    runtime = runtime_module.NegotiationRuntime(config)
    runtime.initialize()
    
    # Create and run session
    session = runtime.create_session(
        buyer_max_price=inputs.get("buyer_max", 450.0),
        seller_min_price=inputs.get("seller_min", 350.0),
        seller_asking_price=inputs.get("seller_asking", 500.0),
        max_turns=inputs.get("max_turns", 10),
    )
    
    runtime.run_session(session)
    
    # Return results
    return {
        "agreed": session.agreed,
        "final_price": session.final_price,
        "turns": session.turns_taken,
        "messages": session.messages,
        "duration_ms": session.duration_ms(),
    }


# ============================================================================
# Local Evaluation (No LangSmith)
# ============================================================================

def run_local_evaluation():
    """Run evaluation locally without LangSmith."""
    print("=" * 60)
    print("LOCAL EVALUATION")
    print("=" * 60)
    print()
    
    results = []
    
    for scenario in NEGOTIATION_SCENARIOS:
        name = scenario["name"]
        inputs = scenario["inputs"]
        
        print(f"Running: {name}...")
        
        # Run negotiation
        output = run_negotiation_for_eval(inputs)
        
        # Run evaluators
        evals = {
            "agreement": agreement_evaluator(output, scenario),
            "fairness": fairness_evaluator(output, scenario),
            "efficiency": efficiency_evaluator(output, scenario),
            "protocol": protocol_evaluator(output, scenario),
            "overall": overall_evaluator(output, scenario),
        }
        
        # Store result
        results.append({
            "scenario": name,
            "output": output,
            "evaluations": evals,
        })
        
        # Print summary
        overall = evals["overall"]
        status = "✓" if overall.score >= 0.7 else "✗"
        print(f"  {status} {name}: {overall.score:.2f} - {overall.comment}")
    
    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    total_score = sum(r["evaluations"]["overall"].score for r in results)
    avg_score = total_score / len(results)
    
    passed = sum(1 for r in results if r["evaluations"]["overall"].score >= 0.7)
    
    print(f"Scenarios: {len(results)}")
    print(f"Passed (≥0.7): {passed}/{len(results)}")
    print(f"Average Score: {avg_score:.2f}")
    
    return results


# ============================================================================
# LangSmith Dataset Upload
# ============================================================================

def upload_dataset_to_langsmith():
    """Upload evaluation dataset to LangSmith."""
    from langsmith import Client
    
    client = Client()
    
    # Check if dataset exists
    try:
        dataset = client.read_dataset(dataset_name=DATASET_NAME)
        print(f"Dataset '{DATASET_NAME}' already exists (id: {dataset.id})")
        
        # Ask to update
        response = input("Update existing dataset? [y/N]: ")
        if response.lower() != "y":
            return dataset
        
        # Delete and recreate
        client.delete_dataset(dataset_id=dataset.id)
        print("Deleted existing dataset")
        
    except Exception:
        pass  # Dataset doesn't exist
    
    # Create dataset
    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description=DATASET_DESCRIPTION,
    )
    print(f"Created dataset '{DATASET_NAME}' (id: {dataset.id})")
    
    # Add examples
    for scenario in NEGOTIATION_SCENARIOS:
        client.create_example(
            dataset_id=dataset.id,
            inputs=scenario["inputs"],
            outputs=scenario["expected"],
            metadata={
                "name": scenario["name"],
                "tags": scenario.get("tags", []),
            },
        )
    
    print(f"Added {len(NEGOTIATION_SCENARIOS)} examples to dataset")
    
    return dataset


# ============================================================================
# LangSmith Experiment
# ============================================================================

def run_langsmith_experiment():
    """Run evaluation as a LangSmith experiment."""
    from langsmith import Client, evaluate
    
    client = Client()
    
    # Ensure dataset exists
    try:
        dataset = client.read_dataset(dataset_name=DATASET_NAME)
    except Exception:
        print(f"Dataset '{DATASET_NAME}' not found. Creating...")
        dataset = upload_dataset_to_langsmith()
    
    print()
    print("=" * 60)
    print("LANGSMITH EXPERIMENT")
    print("=" * 60)
    print(f"Dataset: {DATASET_NAME}")
    print(f"Examples: {len(NEGOTIATION_SCENARIOS)}")
    print()
    
    # Define evaluators for LangSmith
    def ls_agreement(run, example):
        output = run.outputs or {}
        return {
            "key": "agreement",
            "score": 1.0 if output.get("agreed") == example.outputs.get("should_agree") else 0.0,
        }
    
    def ls_fairness(run, example):
        output = run.outputs or {}
        if not output.get("agreed"):
            return {"key": "fairness", "score": 0.5 if not example.outputs.get("should_agree") else 0.0}
        
        price = output.get("final_price", 0)
        min_fair = example.outputs.get("min_fair_price") or 0
        max_fair = example.outputs.get("max_fair_price") or float("inf")
        
        if min_fair and max_fair and min_fair <= price <= max_fair:
            return {"key": "fairness", "score": 1.0}
        return {"key": "fairness", "score": 0.0}
    
    def ls_efficiency(run, example):
        output = run.outputs or {}
        turns = output.get("turns", 10)
        max_acceptable = example.outputs.get("max_acceptable_turns", 10)
        
        if turns <= max_acceptable:
            return {"key": "efficiency", "score": 1.0 - (turns / max_acceptable) * 0.5}
        return {"key": "efficiency", "score": 0.0}
    
    # Run experiment
    experiment_name = f"negotiation-eval-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    print(f"Running experiment: {experiment_name}")
    print("This may take a minute...")
    print()
    
    results = evaluate(
        run_negotiation_for_eval,
        data=DATASET_NAME,
        evaluators=[ls_agreement, ls_fairness, ls_efficiency],
        experiment_prefix=experiment_name,
    )
    
    print()
    print("=" * 60)
    print("EXPERIMENT COMPLETE")
    print("=" * 60)
    print(f"View results at: https://smith.langchain.com")
    print(f"Project: negotiation-evaluation")
    print(f"Experiment: {experiment_name}")
    
    return results


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Run negotiation evaluations with LangSmith",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m 11_evaluation.langsmith.run_evaluation              # Local evaluation
  python -m 11_evaluation.langsmith.run_evaluation --upload     # Upload dataset to LangSmith
  python -m 11_evaluation.langsmith.run_evaluation --experiment # Run LangSmith experiment
  
Environment:
  LANGCHAIN_API_KEY    LangSmith API key (required for --upload and --experiment)
"""
    )
    
    parser.add_argument("--upload", action="store_true",
                        help="Upload dataset to LangSmith")
    parser.add_argument("--experiment", action="store_true",
                        help="Run as LangSmith experiment")
    parser.add_argument("--local", action="store_true",
                        help="Run local evaluation only (default)")
    
    args = parser.parse_args()
    
    # Setup environment
    setup_environment()
    
    if args.upload:
        upload_dataset_to_langsmith()
    elif args.experiment:
        run_langsmith_experiment()
    else:
        run_local_evaluation()


if __name__ == "__main__":
    main()
