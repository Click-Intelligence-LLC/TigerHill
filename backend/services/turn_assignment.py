"""
Turn boundary assignment using state machine algorithm.

This module implements the core algorithm for assigning turn numbers and
sequence numbers to interactions based on their type transitions.

Algorithm:
- State: IN_REQUEST | IN_RESPONSE
- Transition: Request after Response → New turn
- Consecutive requests → Same turn
- Consecutive responses → Same turn
"""

from typing import Dict, List, Any


class TurnAssigner:
    """Assigns turn numbers and sequence numbers to interactions."""

    def __init__(self):
        self.turn_number = 0
        self.sequence = 0
        self.in_response_phase = False

    def assign_turn_numbers(self, interactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Assign turn_number and sequence to each interaction based on type transitions.

        Args:
            interactions: List of interaction dicts with 'type' field ('request' or 'response')
                         Must be sorted chronologically by timestamp

        Returns:
            Same list with 'turn_number' and 'sequence' fields added

        Examples:
            >>> assigner = TurnAssigner()
            >>> interactions = [
            ...     {'type': 'request', 'timestamp': 1000},
            ...     {'type': 'response', 'timestamp': 1100},
            ...     {'type': 'request', 'timestamp': 1200},
            ...     {'type': 'response', 'timestamp': 1300},
            ... ]
            >>> result = assigner.assign_turn_numbers(interactions)
            >>> [(r['turn_number'], r['sequence']) for r in result]
            [(0, 0), (0, 1), (1, 0), (1, 1)]
        """
        result = []

        for interaction in interactions:
            if interaction['type'] == 'request':
                if self.in_response_phase:
                    # Response phase ended, new turn starts
                    self.turn_number += 1
                    self.sequence = 0
                    self.in_response_phase = False
            else:  # type == 'response'
                self.in_response_phase = True

            # Assign current turn and sequence
            interaction['turn_number'] = self.turn_number
            interaction['sequence'] = self.sequence
            result.append(interaction)

            # Increment sequence for next interaction in this turn
            self.sequence += 1

        return result


def assign_turn_numbers(interactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convenience function to assign turn numbers without creating TurnAssigner instance.

    Args:
        interactions: List of interaction dicts sorted by timestamp

    Returns:
        List with turn_number and sequence assigned

    Scenarios covered:
    1. Normal conversation: [R, Resp], [R, Resp] → 2 turns
    2. Function calling: [R, Resp(func)], [R(result), Resp] → 2 turns
    3. Streaming: [R, Resp1, Resp2, Resp3] → 1 turn
    4. Retry: [R, Resp(error)], [R(retry), Resp] → 2 turns
    5. Consecutive requests: [R1, R2, R3, Resp] → 1 turn
    """
    assigner = TurnAssigner()
    return assigner.assign_turn_numbers(interactions)
