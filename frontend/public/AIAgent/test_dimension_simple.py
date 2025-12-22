#!/usr/bin/env python3
"""Simple test script to verify dimension extraction works."""

import sys
sys.path.insert(0, 'src')

from src.nl_floorspace_agent.parser.dimension_extractor import DimensionExtractor
from src.nl_floorspace_agent.models import Units

def test_basic_functionality():
    """Test basic dimension extraction functionality."""
    extractor = DimensionExtractor()
    
    # Test cases
    test_cases = [
        ("5m x 4m room", 5.0, 4.0, Units.SI),
        ("10 feet by 8 feet", 10.0, 8.0, Units.IP),
        ("3.5m by 2.7m", 3.5, 2.7, Units.SI),
        ("12ft x 10ft", 12.0, 10.0, Units.IP),
    ]
    
    print("Testing dimension extraction...")
    
    for text, expected_width, expected_length, expected_units in test_cases:
        print(f"\nTesting: '{text}'")
        result = extractor.extract_dimensions(text)
        
        if result is None:
            print(f"  FAIL: No dimensions extracted")
            continue
            
        print(f"  Extracted: width={result.width}, length={result.length}, units={result.units}")
        print(f"  Expected:  width={expected_width}, length={expected_length}, units={expected_units}")
        
        # Check values
        width_ok = abs(result.width - expected_width) < 0.01
        length_ok = abs(result.length - expected_length) < 0.01
        units_ok = result.units == expected_units
        
        if width_ok and length_ok and units_ok:
            print(f"  PASS")
        else:
            print(f"  FAIL: width_ok={width_ok}, length_ok={length_ok}, units_ok={units_ok}")
    
    # Test validation
    print("\nTesting validation...")
    from src.nl_floorspace_agent.models import Dimensions
    
    # Valid dimensions
    valid_dims = Dimensions(width=5.0, length=4.0, units=Units.SI)
    print(f"Valid dimensions (5x4): {extractor.validate_dimensions(valid_dims)}")
    
    # Invalid dimensions
    invalid_dims = Dimensions(width=-1.0, length=4.0, units=Units.SI)
    print(f"Invalid dimensions (-1x4): {extractor.validate_dimensions(invalid_dims)}")
    
    print("\nBasic functionality test complete!")

if __name__ == "__main__":
    test_basic_functionality()