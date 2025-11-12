"""
Unit tests for Prompt Analyzer
"""

import pytest
from tigerhill.analyzer.prompt_analyzer import PromptAnalyzer
from tigerhill.analyzer.diff_engine import DiffEngine
from tigerhill.analyzer.models import (
    PromptComponentType,
    PromptComponent,
    PromptStructure
)


class TestPromptAnalyzer:
    """Test PromptAnalyzer functionality"""

    def test_token_counting(self):
        """Test token counting functionality"""
        analyzer = PromptAnalyzer(model_name="gemini-pro")

        # Simple text
        text = "Hello, world!"
        tokens = analyzer._count_tokens(text)
        assert tokens > 0
        assert isinstance(tokens, int)

        # Empty text
        assert analyzer._count_tokens("") == 0

        # Longer text
        long_text = "This is a longer text to test token counting. " * 10
        long_tokens = analyzer._count_tokens(long_text)
        assert long_tokens > tokens

    def test_extract_new_input(self):
        """Test extraction of new user input"""
        analyzer = PromptAnalyzer()

        contents = [
            {
                "role": "user",
                "parts": [{"text": "Old message"}]
            },
            {
                "role": "model",
                "parts": [{"text": "Old response"}]
            },
            {
                "role": "user",
                "parts": [{"text": "New message"}]
            }
        ]

        turn_data = {}
        new_input = analyzer._extract_new_input(contents, turn_data)

        assert new_input == "New message"

    def test_analyze_turn_basic(self):
        """Test basic turn analysis"""
        analyzer = PromptAnalyzer()

        turn_data = {
            "requests": [
                {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": "Hello, how are you?"}]
                        }
                    ]
                }
            ]
        }

        structure = analyzer.analyze_turn(turn_data, turn_index=1)

        assert isinstance(structure, PromptStructure)
        assert structure.turn_index == 1
        assert structure.total_tokens > 0
        assert len(structure.components) > 0

        # Should have new user input
        new_input_comps = [
            c for c in structure.components
            if c.type == PromptComponentType.NEW_USER_INPUT
        ]
        assert len(new_input_comps) == 1
        assert "Hello" in new_input_comps[0].content

    def test_analyze_turn_with_history(self):
        """Test turn analysis with conversation history"""
        analyzer = PromptAnalyzer()

        turn_data = {
            "requests": [
                {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": "First message"}]
                        },
                        {
                            "role": "model",
                            "parts": [{"text": "First response"}]
                        },
                        {
                            "role": "user",
                            "parts": [{"text": "Second message"}]
                        }
                    ]
                }
            ],
            "conversation_history": [
                {"role": "user", "content": "First message"},
                {"role": "assistant", "content": "First response"}
            ]
        }

        structure = analyzer.analyze_turn(turn_data, turn_index=2)

        # Should have history components
        history_comps = [
            c for c in structure.components
            if c.type == PromptComponentType.HISTORY
        ]
        assert len(history_comps) > 0

    def test_component_repetition_detection(self):
        """Test detection of repeated components"""
        analyzer = PromptAnalyzer()

        # First turn
        turn1_data = {
            "requests": [
                {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": "You are a helpful assistant"}]
                        },
                        {
                            "role": "user",
                            "parts": [{"text": "Hello"}]
                        }
                    ]
                }
            ]
        }

        structure1 = analyzer.analyze_turn(turn1_data, turn_index=1)

        # Second turn with repeated system prompt
        turn2_data = {
            "requests": [
                {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": "You are a helpful assistant"}]
                        },
                        {
                            "role": "user",
                            "parts": [{"text": "Hello"}]
                        },
                        {
                            "role": "user",
                            "parts": [{"text": "World"}]
                        }
                    ]
                }
            ]
        }

        structure2 = analyzer.analyze_turn(
            turn2_data,
            turn_index=2,
            previous_structure=structure1
        )

        # Check stats
        assert structure2.stats["repeated_ratio"] > 0

    def test_analyze_session(self):
        """Test session analysis with multiple turns"""
        analyzer = PromptAnalyzer()

        session_data = {
            "session_id": "test-session",
            "turns": [
                {
                    "requests": [
                        {
                            "contents": [
                                {
                                    "role": "user",
                                    "parts": [{"text": "Turn 1"}]
                                }
                            ]
                        }
                    ]
                },
                {
                    "requests": [
                        {
                            "contents": [
                                {
                                    "role": "user",
                                    "parts": [{"text": "Turn 2"}]
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        structures = analyzer.analyze_session(session_data)

        assert len(structures) == 2
        assert structures[0].turn_index == 1
        assert structures[1].turn_index == 2


class TestDiffEngine:
    """Test DiffEngine functionality"""

    def test_compute_diff_basic(self):
        """Test basic diff computation"""
        engine = DiffEngine()

        # Create two structures
        comp1 = PromptComponent(
            type=PromptComponentType.NEW_USER_INPUT,
            content="Message 1",
            tokens=10
        )

        structure1 = PromptStructure(
            turn_index=1,
            total_tokens=10,
            components=[comp1],
            stats={"unique_tokens": 10, "repeated_ratio": 0}
        )

        comp2 = PromptComponent(
            type=PromptComponentType.HISTORY,
            content="Message 1",
            tokens=10,
            is_repeated=True
        )

        comp3 = PromptComponent(
            type=PromptComponentType.NEW_USER_INPUT,
            content="Message 2",
            tokens=10
        )

        structure2 = PromptStructure(
            turn_index=2,
            total_tokens=20,
            components=[comp2, comp3],
            stats={"unique_tokens": 10, "repeated_ratio": 0.5}
        )

        diff = engine.compute_diff(structure1, structure2)

        assert diff.from_turn == 1
        assert diff.to_turn == 2
        assert diff.total_changes > 0

    def test_compute_all_diffs(self):
        """Test computing all diffs for a session"""
        engine = DiffEngine()

        structures = [
            PromptStructure(
                turn_index=i,
                total_tokens=100 * i,
                components=[
                    PromptComponent(
                        type=PromptComponentType.NEW_USER_INPUT,
                        content=f"Message {i}",
                        tokens=100 * i
                    )
                ],
                stats={"unique_tokens": 100 * i, "repeated_ratio": 0}
            )
            for i in range(1, 4)
        ]

        diffs = engine.compute_all_diffs(structures)

        assert len(diffs) == 2  # 3 structures = 2 diffs
        assert diffs[0].from_turn == 1
        assert diffs[0].to_turn == 2
        assert diffs[1].from_turn == 2
        assert diffs[1].to_turn == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
