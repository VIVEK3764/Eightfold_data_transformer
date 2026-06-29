import os
import sys
import pytest

# Add project root to sys.path so we can run this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.normalizers.email import normalize_email
from src.normalizers.phone import normalize_phone
from src.normalizers.dates import normalize_date
from src.normalizers.skills import normalize_skill

# --- Email Tests ---

@pytest.mark.parametrize("input_email, expected", [
    ("JOHN@GMAIL.COM", "john@gmail.com"),
    ("  john@gmail.com  ", "john@gmail.com"),
    ("abc", None),
    ("", None),
    (None, None)
])
def test_normalize_email(input_email, expected):
    assert normalize_email(input_email) == expected

# --- Phone Tests ---

@pytest.mark.parametrize("input_phone, expected", [
    ("(+91)-98765-43210", "+919876543210"),
    ("9876543210", "+919876543210"),
    ("123abc", None),
    ("", None),
    (None, None)
])
def test_normalize_phone(input_phone, expected):
    assert normalize_phone(input_phone) == expected

# --- Date Tests ---

@pytest.mark.parametrize("input_date, expected", [
    ("Jan 2020", "2020-01"),
    ("01/2020", "2020-01"),
    ("2020-01", "2020-01"),
    ("2020", "2020-01"),
    ("abcd", None),
    ("", None),
    (None, None)
])
def test_normalize_date(input_date, expected):
    assert normalize_date(input_date) == expected

# --- Skill Tests ---

@pytest.mark.parametrize("input_skill, expected", [
    ("cpp", "C++"),
    ("C Plus Plus", "C++"),
    ("cplusplus", "C++"),
    ("js", "JavaScript"),
    ("javascript", "JavaScript"),
    ("py", "Python"),
    ("springboot", "Spring Boot"),
    ("spring boot", "Spring Boot"),
    ("Docker", "Docker"),
    ("docker", "Docker"),
    ("", ""),
    (None, "")
])
def test_normalize_skill(input_skill, expected):
    assert normalize_skill(input_skill) == expected

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
