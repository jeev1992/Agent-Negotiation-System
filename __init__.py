"""
Agent Negotiation System
========================

Root package for the 10-layer architecture.

Since Python modules can't start with numbers, we use importlib
to provide clean access to all layers.
"""

import importlib
import sys
from pathlib import Path

# Ensure project root is in path
_project_root = Path(__file__).parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def _import_layer(folder_name: str):
    """Import a numbered layer folder as a module."""
    import importlib.util
    
    folder_path = _project_root / folder_name
    init_path = folder_path / "__init__.py"
    
    if init_path.exists():
        spec = importlib.util.spec_from_file_location(folder_name, init_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[folder_name] = module
        spec.loader.exec_module(module)
        return module
    return None


# Layer imports available as:
# from agent_negotiation_system import layer_0_system, layer_1_runtime, etc.

try:
    layer_01_baseline = _import_layer("01_baseline")
    layer_02_architecture = _import_layer("02_architecture")
    layer_03_protocol = _import_layer("03_protocol")
    layer_04_fsm = _import_layer("04_fsm")
    layer_05_agents = _import_layer("05_agents")
    layer_06_orchestration = _import_layer("06_orchestration")
    layer_07_coordination = _import_layer("07_coordination")
    layer_08_transport = _import_layer("08_transport")
    layer_09_context = _import_layer("09_context")
    layer_10_runtime = _import_layer("10_runtime")
    layer_11_evaluation = _import_layer("11_evaluation")
except Exception:
    # Layers may not all be set up yet
    pass


__version__ = "0.1.0"
__all__ = [
    "layer_01_baseline",
    "layer_02_architecture",
    "layer_03_protocol",
    "layer_04_fsm",
    "layer_05_agents",
    "layer_06_orchestration",
    "layer_07_coordination",
    "layer_08_transport",
    "layer_09_context",
    "layer_10_runtime",
    "layer_11_evaluation",
]
