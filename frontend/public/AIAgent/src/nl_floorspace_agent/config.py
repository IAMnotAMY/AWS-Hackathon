"""Configuration settings for the Natural Language to Floorspace JSON Agent."""

import os
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class AWSConfig:
    """AWS configuration settings."""
    region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    max_tokens: int = 4000
    temperature: float = 0.1


@dataclass
class AppConfig:
    """Application configuration settings."""
    log_level: str = "INFO"
    session_timeout: int = 3600  # 1 hour in seconds
    max_conversation_turns: int = 50
    default_units: str = "si"  # metric by default


def get_aws_config() -> AWSConfig:
    """Get AWS configuration from environment variables or defaults."""
    return AWSConfig(
        region=os.getenv("AWS_REGION", "us-east-1"),
        bedrock_model_id=os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"),
        max_tokens=int(os.getenv("BEDROCK_MAX_TOKENS", "4000")),
        temperature=float(os.getenv("BEDROCK_TEMPERATURE", "0.1"))
    )


def get_app_config() -> AppConfig:
    """Get application configuration from environment variables or defaults."""
    return AppConfig(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        session_timeout=int(os.getenv("SESSION_TIMEOUT", "3600")),
        max_conversation_turns=int(os.getenv("MAX_CONVERSATION_TURNS", "50")),
        default_units=os.getenv("DEFAULT_UNITS", "si")
    )


# Default Floorspace JSON template
DEFAULT_FLOORSPACE_TEMPLATE: Dict[str, Any] = {
    "application": {
        "currentSelections": {
            "tool": "Rectangle",
            "mode": "spaces"
        }
    },
    "project": {
        "config": {
            "units": "si",
            "language": "EN-US",
            "north_axis": 0
        },
        "grid": {
            "visible": True,
            "spacing": 1.0
        },
        "view": {
            "min_x": -10,
            "min_y": -10,
            "max_x": 10,
            "max_y": 10
        },
        "map": {
            "visible": False,
            "latitude": 39.7392,
            "longitude": -104.9903,
            "zoom": 4,
            "rotation": 0
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