"""Natural Language to Floorspace JSON Agent.

A conversational AI system that transforms natural language descriptions 
of building spaces into valid Floorspace JSON format.
"""

__version__ = "0.1.0"

from .agent import FloorspaceAgent

__all__ = ["FloorspaceAgent"]