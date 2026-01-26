"""
Tests for FSM Layer
==================
"""

import pytest
import sys
import importlib.util
from pathlib import Path

# Setup path for numbered module imports
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


# Import FSM module
fsm_module = import_numbered_layer("04_fsm")
NegotiationFSM = fsm_module.NegotiationFSM
NegotiationState = fsm_module.NegotiationState
FailureReason = fsm_module.FailureReason


class TestFSMTermination:
    """Test that FSM guarantees termination."""
    
    def test_starts_in_idle(self):
        """FSM should start in IDLE state."""
        fsm = NegotiationFSM(max_turns=10)
        assert fsm.get_state() == NegotiationState.IDLE
    
    def test_can_start(self):
        """Can transition from IDLE to NEGOTIATING."""
        fsm = NegotiationFSM(max_turns=10)
        assert fsm.start() is True
        assert fsm.get_state() == NegotiationState.NEGOTIATING
    
    def test_cannot_start_twice(self):
        """Cannot start an already started negotiation."""
        fsm = NegotiationFSM(max_turns=10)
        fsm.start()
        assert fsm.start() is False
    
    def test_accept_moves_to_agreed(self):
        """Accept should move to AGREED terminal state."""
        fsm = NegotiationFSM(max_turns=10)
        fsm.start()
        fsm.transition_to_agreed(final_price=400.0)
        
        assert fsm.get_state() == NegotiationState.AGREED
        assert fsm.is_terminal() is True
    
    def test_reject_moves_to_failed(self):
        """Reject should move to FAILED terminal state."""
        fsm = NegotiationFSM(max_turns=10)
        fsm.start()
        fsm.transition_to_failed("Too expensive")
        
        assert fsm.get_state() == NegotiationState.FAILED
        assert fsm.is_terminal() is True
    
    def test_max_turns_terminates(self):
        """Exceeding max turns should terminate."""
        fsm = NegotiationFSM(max_turns=3)
        fsm.start()
        
        # Process turns
        fsm.process_turn()  # turn 1
        fsm.process_turn()  # turn 2
        result = fsm.process_turn()  # turn 3 - should fail
        
        assert result is False
        assert fsm.get_state() == NegotiationState.FAILED
        assert fsm.context.failure_reason == FailureReason.MAX_TURNS_EXCEEDED
    
    def test_terminal_states_have_no_transitions(self):
        """Terminal states should have no outgoing transitions."""
        assert len(NegotiationFSM.TRANSITIONS[NegotiationState.AGREED]) == 0
        assert len(NegotiationFSM.TRANSITIONS[NegotiationState.FAILED]) == 0
    
    def test_cannot_act_after_agreed(self):
        """Cannot perform actions after AGREED."""
        fsm = NegotiationFSM(max_turns=10)
        fsm.start()
        fsm.transition_to_agreed(final_price=400.0)
        
        # These should all fail
        assert fsm.process_turn() is False
        assert fsm.transition_to_agreed(final_price=500.0) is False
        assert fsm.transition_to_failed("changed mind") is False


class TestFSMInvariants:
    """Test FSM invariants."""
    
    def test_turn_count_non_negative(self):
        """Turn count should never be negative."""
        fsm = NegotiationFSM(max_turns=10)
        assert fsm.context.turn_count >= 0
        
        fsm.start()
        assert fsm.context.turn_count >= 0
    
    def test_agreed_has_price(self):
        """AGREED state must have agreed_price set."""
        fsm = NegotiationFSM(max_turns=10)
        fsm.start()
        fsm.transition_to_agreed(final_price=400.0)
        
        assert fsm.check_invariants()
        assert fsm.context.agreed_price is not None
    
    def test_failed_has_reason(self):
        """FAILED state must have failure_reason set."""
        fsm = NegotiationFSM(max_turns=10)
        fsm.start()
        fsm.transition_to_failed("test")
        
        assert fsm.check_invariants()
        assert fsm.context.failure_reason is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
