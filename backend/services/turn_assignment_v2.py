"""
Turn assignment with merge and split logic.

Merge Rules:
- Consecutive incomplete turns (only requests OR only responses) are merged
- Keep the first turn number, skip subsequent numbers
- Example: Turn 1 (reqs only) + Turn 2 (resps only) → Turn 1, skip 2

Split Rules:
- A turn with multiple request-response pairs gets split
- Use fractional numbers: Turn 6 → Turn 6.1, Turn 6.2, ...
- Next turn number is unaffected (still Turn 7)
"""

from typing import Dict, List, Any, Union


def merge_and_split_turns(interactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process turns: merge incomplete ones, split multi-pair ones.

    Args:
        interactions: List sorted by timestamp with initial turn_number assigned

    Returns:
        List with final turn_number (int or float like 6.1, 6.2)
    """
    if not interactions:
        return []

    # Group by initial turn_number
    turns_dict = {}
    for interaction in interactions:
        turn_num = interaction['turn_number']
        if turn_num not in turns_dict:
            turns_dict[turn_num] = []
        turns_dict[turn_num].append(interaction)

    turn_numbers = sorted(turns_dict.keys())
    result = []
    i = 0

    print(f"\n📊 Processing {len(turn_numbers)} turns...")

    while i < len(turn_numbers):
        turn_num = turn_numbers[i]
        turn_interactions = turns_dict[turn_num]

        # Check if incomplete
        if is_incomplete_turn(turn_interactions):
            # Start collecting consecutive incomplete turns
            merge_group = [turn_num]
            merged_interactions = list(turn_interactions)
            j = i + 1

            # Continue collecting incomplete turns
            while j < len(turn_numbers):
                next_num = turn_numbers[j]
                next_interactions = turns_dict[next_num]

                if is_incomplete_turn(next_interactions):
                    merge_group.append(next_num)
                    merged_interactions.extend(next_interactions)
                    j += 1
                else:
                    break  # Hit a complete turn, stop

            # Merge complete, assign first turn number to all
            for interaction in merged_interactions:
                interaction['turn_number'] = merge_group[0]

            result.extend(merged_interactions)

            if len(merge_group) > 1:
                print(f"🔗 Merged Turns {merge_group} → Turn {merge_group[0]}")
                print(f"   Skipped: {merge_group[1:]}")

            i = j

        else:
            # Complete turn - check if needs splitting
            pairs = identify_request_response_pairs(turn_interactions)

            if len(pairs) > 1:
                # Split into fractional turns
                # Use 0.01 increments to avoid float("13.10") == float("13.1") issue
                for idx, pair in enumerate(pairs):
                    sub_turn_num = turn_num + (idx + 1) * 0.01
                    for interaction in pair:
                        interaction['turn_number'] = sub_turn_num
                    result.extend(pair)

                fractional_nums = [f"{turn_num + (i+1) * 0.01:.2f}" for i in range(len(pairs))]
                print(f"✂️  Split Turn {int(turn_num)} → {fractional_nums}")
            else:
                # Normal complete turn, keep as-is
                result.extend(turn_interactions)

            i += 1

    # Re-assign sequence numbers within each final turn
    result = reassign_sequences(result)

    print(f"✅ Final: {len(set(i['turn_number'] for i in result))} turns, {len(result)} interactions\n")

    return result


def is_incomplete_turn(interactions: List[Dict[str, Any]]) -> bool:
    """Check if turn is incomplete (only requests OR only responses)."""
    has_request = any(i['type'] == 'request' for i in interactions)
    has_response = any(i['type'] == 'response' for i in interactions)
    return has_request != has_response  # XOR: exactly one type


def identify_request_response_pairs(interactions: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Identify request-response pairs in a turn by timestamp order.

    Returns:
        List of pairs, each pair is [interaction1, interaction2, ...]
    """
    sorted_interactions = sorted(interactions, key=lambda x: x['timestamp'])
    pairs = []
    current_pair = []

    for interaction in sorted_interactions:
        if interaction['type'] == 'request':
            if current_pair:
                # Previous pair ends, start new one
                pairs.append(current_pair)
                current_pair = []
            current_pair.append(interaction)
        else:  # response
            current_pair.append(interaction)

    # Add final pair
    if current_pair:
        pairs.append(current_pair)

    return pairs


def reassign_sequences(interactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Reassign sequence numbers within each turn."""
    # Group by final turn_number
    turn_groups = {}
    for interaction in interactions:
        turn_num = interaction['turn_number']
        if turn_num not in turn_groups:
            turn_groups[turn_num] = []
        turn_groups[turn_num].append(interaction)

    # Reassign sequences
    result = []
    for turn_num in sorted(turn_groups.keys()):
        turn_interactions = sorted(turn_groups[turn_num], key=lambda x: x['timestamp'])
        for seq, interaction in enumerate(turn_interactions):
            interaction['sequence'] = seq
            result.append(interaction)

    return result


# Legacy compatibility - original simple algorithm
def assign_turn_numbers_simple(interactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Original simple turn assignment (for backward compatibility).
    Uses state machine: Request after Response → New turn.
    """
    turn_number = 0
    sequence = 0
    in_response_phase = False
    result = []

    for interaction in interactions:
        if interaction['type'] == 'request':
            if in_response_phase:
                turn_number += 1
                sequence = 0
                in_response_phase = False
        else:  # response
            in_response_phase = True

        interaction['turn_number'] = turn_number
        interaction['sequence'] = sequence
        result.append(interaction)
        sequence += 1

    return result


# Main entry point
def assign_turn_numbers(interactions: List[Dict[str, Any]], use_smart_merge: bool = True) -> List[Dict[str, Any]]:
    """
    Assign turn numbers with optional smart merge/split.

    Args:
        interactions: List of interaction dicts sorted by timestamp
                     Should have 'turn_number' already set (from JSON or simple algorithm)
        use_smart_merge: If True, use merge/split logic; if False, keep as-is

    Returns:
        List with turn_number and sequence assigned
    """
    if not interactions:
        return []

    # Check if turn_number is already set
    has_turn_numbers = all('turn_number' in i for i in interactions)

    if not has_turn_numbers:
        # No turn numbers yet, use simple algorithm
        interactions = assign_turn_numbers_simple(interactions)

    # Apply merge/split if enabled
    if use_smart_merge:
        interactions = merge_and_split_turns(interactions)

    return interactions
