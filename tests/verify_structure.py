"""
Project Structure Verification
==============================
Run this script to verify all modules import correctly.

Usage:
    python tests/verify_structure.py
"""

import sys
import importlib.util
from pathlib import Path

# Add project root to path (parent of tests/)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def import_numbered_layer(folder_name: str):
    """Import a numbered layer folder dynamically."""
    folder_path = project_root / folder_name
    init_path = folder_path / "__init__.py"
    
    if not init_path.exists():
        raise ImportError(f"No __init__.py in {folder_name}")
    
    spec = importlib.util.spec_from_file_location(folder_name, init_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[folder_name] = module
    spec.loader.exec_module(module)
    return module


def check_imports():
    """Verify all layer imports work."""
    results = []
    
    layers = [
        ("01_baseline", ["run_naive_negotiation"]),
        ("02_architecture", []),  # Documentation only, no exports required
        ("03_protocol", ["NegotiationMessage", "Offer", "Counter", "Accept", "Reject"]),
        ("04_fsm", ["NegotiationFSM", "FSMState"]),
        ("05_agents", ["BuyerStrategy", "SellerStrategy"]),
        ("06_orchestration", ["NegotiationGraph", "NegotiationState"]),
        ("07_coordination", ["CoordinationPolicy", "PolicyViolation"]),
        ("08_transport", ["LocalChannel", "Message", "A2AChannel", "AgentCard"]),
        ("09_context", ["MCPServer", "get_market_context"]),
        ("10_runtime", ["RuntimeConfig", "NegotiationRuntime"]),
        ("11_evaluation", ["JudgeAgent", "NegotiationScore"]),
    ]
    
    for layer_name, expected_exports in layers:
        try:
            module = import_numbered_layer(layer_name)
            
            # Check expected exports exist
            missing = [e for e in expected_exports if not hasattr(module, e)]
            if missing:
                results.append((layer_name, "⚠", f"Missing exports: {missing}"))
            else:
                results.append((layer_name, "✓", ""))
        except Exception as e:
            results.append((layer_name, "✗", str(e)[:60]))
    
    return results


def print_results(results):
    """Pretty print verification results."""
    print("\n" + "=" * 60)
    print("Agent Negotiation System - Structure Verification")
    print("=" * 60 + "\n")
    
    all_passed = True
    for layer, status, error in results:
        print(f"  {status} {layer}")
        if error:
            print(f"      Error: {error}")
            all_passed = False
    
    print("\n" + "-" * 60)
    if all_passed:
        print("✓ All layers imported successfully!")
    else:
        print("✗ Some imports failed. Check the errors above.")
    print("-" * 60 + "\n")
    
    return all_passed


if __name__ == "__main__":
    results = check_imports()
    success = print_results(results)
    sys.exit(0 if success else 1)
