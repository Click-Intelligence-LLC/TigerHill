"""
Turn assignment based on request_id (V3 - Simplified).

Key insight: Every request and response has a unique request_id.
We can simply group all interactions by request_id to form turns.

This eliminates the need for complex merge/split logic and handles
streaming responses automatically.
"""

from typing import Dict, List, Any


def assign_turn_numbers_by_request_id(interactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Assign turn numbers based on request_id grouping.

    Strategy:
    1. Group all interactions by request_id
    2. Sort groups by the timestamp of their request
    3. Assign sequential turn numbers
    4. Assign sequence numbers within each turn

    Args:
        interactions: List of interaction dicts with 'type', 'data', 'timestamp'

    Returns:
        List with turn_number and sequence assigned
    """
    if not interactions:
        return []

    # Group interactions by request_id
    request_groups = {}

    for interaction in interactions:
        data = interaction['data']
        req_id = data.get('request_id')

        if not req_id:
            print(f"⚠ Warning: interaction without request_id, skipping")
            continue

        if req_id not in request_groups:
            request_groups[req_id] = []

        request_groups[req_id].append(interaction)

    # Sort each group by timestamp
    for req_id, group in request_groups.items():
        group.sort(key=lambda x: x['timestamp'])

    # Find the request in each group to determine turn order
    turn_order = []
    for req_id, group in request_groups.items():
        # Find the request (should be first after sorting, but let's be safe)
        request = next((i for i in group if i['type'] == 'request'), None)
        if request:
            turn_order.append((req_id, request['timestamp']))
        else:
            # No request? Use first interaction's timestamp
            turn_order.append((req_id, group[0]['timestamp']))

    # Sort by timestamp to get turn sequence
    turn_order.sort(key=lambda x: x[1])

    # Assign turn numbers
    result = []
    for turn_number, (req_id, _) in enumerate(turn_order):
        group = request_groups[req_id]

        # Assign turn_number and sequence to each interaction
        for sequence, interaction in enumerate(group):
            interaction['turn_number'] = turn_number
            interaction['sequence'] = sequence
            result.append(interaction)

        # Debug info
        req_count = sum(1 for i in group if i['type'] == 'request')
        resp_count = sum(1 for i in group if i['type'] == 'response')
        print(f"Turn {turn_number}: {req_count} request(s), {resp_count} response(s) [request_id: {req_id[:20]}...]")

    print(f"\n✅ Total: {len(turn_order)} turns from {len(request_groups)} unique request_ids")

    return result
