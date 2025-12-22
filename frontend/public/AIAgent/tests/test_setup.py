"""Test basic project setup and imports."""

import pytest
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_package_imports():
    """Test that all main package components can be imported."""
    # Test main package import
    import nl_floorspace_agent
    assert nl_floorspace_agent.__version__ == "0.1.0"
    
    # Test main agent import
    from nl_floorspace_agent import FloorspaceAgent
    assert FloorspaceAgent is not None
    
    # Test model imports
    from nl_floorspace_agent.models import (
        Dimensions, ElementSpec, BuildingElement, SpaceRequirement
    )
    assert all([Dimensions, ElementSpec, BuildingElement, SpaceRequirement])


def test_config_import():
    """Test configuration module import."""
    from nl_floorspace_agent.config import get_aws_config, get_app_config
    
    aws_config = get_aws_config()
    app_config = get_app_config()
    
    assert aws_config.region == "us-east-1"
    assert app_config.log_level == "INFO"


def test_agent_initialization():
    """Test that FloorspaceAgent can be initialized."""
    from nl_floorspace_agent import FloorspaceAgent
    
    # This should not raise an exception
    agent = FloorspaceAgent()
    assert agent is not None
    assert hasattr(agent, 'parser')
    assert hasattr(agent, 'conversation_manager')
    assert hasattr(agent, 'geometry_generator')


def test_directory_structure():
    """Test that all expected directories exist."""
    src_path = Path(__file__).parent.parent / "src" / "nl_floorspace_agent"
    
    expected_dirs = [
        "models",
        "parser", 
        "conversation",
        "geometry",
        "storage",
        "export"
    ]
    
    for dir_name in expected_dirs:
        dir_path = src_path / dir_name
        assert dir_path.exists(), f"Directory {dir_name} should exist"
        assert (dir_path / "__init__.py").exists(), f"__init__.py should exist in {dir_name}"