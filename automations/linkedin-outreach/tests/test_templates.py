import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import templates
sys.path.insert(0, str(Path(__file__).parent.parent))

import templates

def test_list_templates():
    """Test that list_templates returns all expected template IDs."""
    expected_templates = ["T1", "T2", "T3", "T4", "T5"]
    result = templates.list_templates()

    # Check that all expected templates are in the result
    for t in expected_templates:
        assert t in result

    # Check that the length matches exactly
    assert len(result) == len(expected_templates)

def test_get_template_valid_id():
    """Test get_template with valid IDs returns correct templates."""
    # Test T1
    t1_result = templates.get_template("T1")
    assert t1_result == templates.T1_FOUNDER_DM

    # Test T5
    t5_result = templates.get_template("T5")
    assert t5_result == templates.T5_FOLLOW_UP

def test_get_template_invalid_id():
    """Test get_template with an invalid ID defaults to T2."""
    invalid_result = templates.get_template("INVALID_ID")
    assert invalid_result == templates.T2_HIRING_MANAGER_DM

def test_get_template_empty_string():
    """Test get_template with an empty string defaults to T2."""
    empty_result = templates.get_template("")
    assert empty_result == templates.T2_HIRING_MANAGER_DM
