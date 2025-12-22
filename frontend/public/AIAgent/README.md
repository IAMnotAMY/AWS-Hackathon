# Natural Language to Floorspace JSON Agent

An AI-powered system that converts natural language descriptions of building spaces into valid Floorspace JSON format.

## Features

- Natural language parsing for spatial descriptions
- Interactive clarification for missing details
- Geometric validation and constraint checking
- AWS Bedrock integration for conversation management
- Valid Floorspace JSON generation

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure AWS credentials for Bedrock access

4. Run tests:
```bash
pytest
```

## Usage

```python
from nl_floorspace_agent import FloorspaceAgent

agent = FloorspaceAgent()
result = agent.process_description("Create a 5m x 4m bedroom with 2 windows")
```

## Project Structure

- `src/nl_floorspace_agent/` - Main application code
- `tests/` - Test files
- `docs/` - Documentation
- `.kiro/specs/` - Feature specifications