"""
Test debate script generation and schema validation.
"""
import pytest
import json

from src.agents.debate_orchestrator import DebateLine, DebateScript


def test_debate_line_creation():
    """Test creating a debate line."""
    line = DebateLine(
        speaker="chatgpt",
        text="Hello, this is a test",
        estimated_duration_sec=5.0,
        pause_after_sec=0.5
    )

    assert line.speaker == "chatgpt"
    assert line.text == "Hello, this is a test"
    assert line.estimated_duration_sec == 5.0


def test_debate_script_creation():
    """Test creating a debate script."""
    lines = [
        DebateLine(
            speaker="host",
            text="Welcome",
            estimated_duration_sec=3.0
        ),
        DebateLine(
            speaker="chatgpt",
            text="Hello",
            estimated_duration_sec=2.0
        ),
    ]

    script = DebateScript(
        title="Test Debate",
        topic_summary="A test topic",
        lines=lines,
        total_duration_sec=5.0
    )

    assert script.title == "Test Debate"
    assert len(script.lines) == 2


def test_debate_script_json_serialization():
    """Test that debate script can be serialized to JSON."""
    lines = [
        DebateLine(
            speaker="chatgpt",
            text="Test line",
            estimated_duration_sec=5.0,
            pause_after_sec=0.5
        )
    ]

    script = DebateScript(
        title="Test",
        topic_summary="Summary",
        lines=lines,
        total_duration_sec=5.5
    )

    json_str = script.to_json()

    # Ensure it's valid JSON
    data = json.loads(json_str)

    assert data['title'] == "Test"
    assert data['topic_summary'] == "Summary"
    assert len(data['lines']) == 1
    assert data['lines'][0]['speaker'] == "chatgpt"


def test_debate_script_json_deserialization():
    """Test that debate script can be loaded from JSON."""
    json_str = '''
    {
        "title": "Test Debate",
        "topic_summary": "Test summary",
        "lines": [
            {
                "speaker": "chatgpt",
                "text": "Hello",
                "estimated_duration_sec": 3.0,
                "pause_after_sec": 0.5
            }
        ],
        "total_duration_sec": 3.5
    }
    '''

    script = DebateScript.from_json(json_str)

    assert script.title == "Test Debate"
    assert len(script.lines) == 1
    assert script.lines[0].speaker == "chatgpt"
    assert script.total_duration_sec == 3.5
