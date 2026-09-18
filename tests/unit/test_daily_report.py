import pytest
from daily_report import fmt_lakh

def test_fmt_lakh():
    # Test None
    assert fmt_lakh(None) == "-"

    # Test numbers < 1000
    assert fmt_lakh(0) == "0"
    assert fmt_lakh(500) == "500"
    assert fmt_lakh(999) == "999"

    # Test numbers between 1000 and 99999
    assert fmt_lakh(1000) == "1.0K"
    assert fmt_lakh(1500) == "1.5K"
    assert fmt_lakh(99999) == "100.0K"

    # Test numbers >= 100000
    assert fmt_lakh(100000) == "1.00L"
    assert fmt_lakh(123456) == "1.23L"
    assert fmt_lakh(123900) == "1.24L"

@pytest.mark.parametrize("val, expected", [
    (None, "-"),
    (0, "0"),
    (999, "999"),
    (1000, "1.0K"),
    (1500, "1.5K"),
    (1550, "1.6K"),
    (99900, "99.9K"),
    (99950, "100.0K"),
    (100000, "1.00L"),
    (123456, "1.23L"),
    (123440, "1.23L"),
    (123900, "1.24L")
])
def test_fmt_lakh_parameterized(val, expected):
    assert fmt_lakh(val) == expected
