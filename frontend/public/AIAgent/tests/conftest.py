"""Pytest configuration and shared fixtures."""

import pytest
from typing import Dict, Any
from unittest.mock import Mock

from src.nl_floorspace_agent.models import FloorspaceModel, ConversationState


@pytest.fixture
def sample_floorspace_json() -> Dict[str, Any]:
    """Sample Floorspace JSON structure for testing."""
    return {
        "application": {
            "currentSelections": {
                "tool": "Rectangle",
                "mode": "spaces"
            }
        },
        "project": {
            "config": {
                "units": "ip",
                "language": "EN-US"
            },
            "grid": {
                "visible": True,
                "spacing": 5
            },
            "view": {
                "min_x": 0,
                "min_y": 0,
                "max_x": 100,
                "max_y": 100
            }
        },
        "stories": [],
        "building_units": [],
        "thermal_zones": [],
        "space_types": [],
        "construction_sets": [],
        "window_definitions": [],
        "door_definitions": [],
        "version": "1.4.3"
    }


@pytest.fixture
def mock_bedrock_client():
    """Mock AWS Bedrock client for testing."""
    mock_client = Mock()
    mock_client.invoke_model.return_value = {
        'body': Mock()
    }
    return mock_client


@pytest.fixture
def empty_conversation_state() -> ConversationState:
    """Empty conversation state for testing."""
    from src.nl_floorspace_agent.models import ConversationStep
    
    return ConversationState(
        current_step=ConversationStep.PARSING,
        pending_questions=[],
        collected_specs=[],
        building_model=FloorspaceModel(
            application={},
            project={},
            stories=[],
            window_definitions=[],
            door_definitions=[],
            building_units=[],
            thermal_zones=[],
            space_types=[],
            construction_sets=[],
            version="1.4.3"
        )
    )