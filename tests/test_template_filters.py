"""
Tests for meals/templatetags/meal_extras.py

Covers:
  - divide_by_100_mult: nutrient-per-amount calculation (value / 100) * arg
  - split_to_dict: parses "key:val,key2:val2" into a list of [key, val] pairs
  - get_item: safe dictionary lookup
"""

import pytest
from meals.templatetags.meal_extras import divide_by_100_mult, split_to_dict, get_item


class TestDivideBy100Mult:
    """Tests for the divide_by_100_mult template filter."""

    def test_basic_calculation(self):
        """100 g of food with 10 kcal/100g → 10 kcal."""
        assert divide_by_100_mult(10, 100) == pytest.approx(10.0)

    def test_partial_amount(self):
        """200 g of food with 100 kcal/100g → 200 kcal."""
        assert divide_by_100_mult(100, 200) == pytest.approx(200.0)

    def test_fractional_amount(self):
        """50 g of food with 80 kcal/100g → 40 kcal."""
        assert divide_by_100_mult(80, 50) == pytest.approx(40.0)

    def test_zero_value(self):
        """Nutrient value of 0 → always 0 regardless of amount."""
        assert divide_by_100_mult(0, 250) == pytest.approx(0.0)

    def test_zero_amount(self):
        """Amount of 0 g → always 0 regardless of nutrient density."""
        assert divide_by_100_mult(50, 0) == pytest.approx(0.0)

    def test_float_inputs(self):
        """Float nutrient values and float amounts are handled correctly."""
        assert divide_by_100_mult(4.5, 150) == pytest.approx(6.75)

    def test_string_numeric_inputs(self):
        """String representations of numbers are coerced correctly."""
        assert divide_by_100_mult("20", "100") == pytest.approx(20.0)

    def test_none_value_returns_zero(self):
        """None as value returns 0 (TypeError caught)."""
        assert divide_by_100_mult(None, 100) == 0

    def test_none_arg_returns_zero(self):
        """None as arg returns 0 (TypeError caught)."""
        assert divide_by_100_mult(50, None) == 0

    def test_non_numeric_value_returns_zero(self):
        """Non-numeric string as value returns 0 (ValueError caught)."""
        assert divide_by_100_mult("abc", 100) == 0

    def test_non_numeric_arg_returns_zero(self):
        """Non-numeric string as arg returns 0 (ValueError caught)."""
        assert divide_by_100_mult(50, "xyz") == 0

    def test_negative_value(self):
        """Negative nutrient density produces a negative result."""
        assert divide_by_100_mult(-10, 100) == pytest.approx(-10.0)

    def test_large_values(self):
        """Large realistic values (e.g. energy in kJ) are computed correctly."""
        # 1700 kJ/100g * 350g = 5950 kJ
        assert divide_by_100_mult(1700, 350) == pytest.approx(5950.0)


class TestSplitToDict:
    """Tests for the split_to_dict template filter."""

    def test_single_pair(self):
        """A single key:value pair is returned as a one-element list."""
        result = split_to_dict("key:val")
        assert result == [["key", "val"]]

    def test_multiple_pairs(self):
        """Multiple comma-separated key:value pairs are parsed correctly."""
        result = split_to_dict("key1:val1,key2:val2,key3:val3")
        assert result == [["key1", "val1"], ["key2", "val2"], ["key3", "val3"]]

    def test_empty_string_returns_list_with_empty(self):
        """An empty string produces a list with one empty item (split on comma gives [''])."""
        result = split_to_dict("")
        # split('') on '' gives [''], then split(':') gives [['']]
        assert isinstance(result, list)

    def test_none_returns_empty_list(self):
        """None input is caught by the except clause and returns []."""
        result = split_to_dict(None)
        assert result == []

    def test_malformed_no_colon_returns_single_item_list(self):
        """Input without ':' still returns a list item (single element sublist)."""
        result = split_to_dict("justkey")
        assert isinstance(result, list)
        assert len(result) == 1

    def test_nutrient_threshold_format(self):
        """Realistic threshold format used in templates parses correctly."""
        result = split_to_dict("energy_in_kcal:2000,protein_in_g:50")
        assert ["energy_in_kcal", "2000"] in result
        assert ["protein_in_g", "50"] in result


class TestGetItem:
    """Tests for the get_item template filter."""

    def test_existing_key(self):
        """Returns the correct value for an existing key."""
        d = {"a": 1, "b": 2}
        assert get_item(d, "a") == 1

    def test_missing_key_returns_none(self):
        """Returns None when the key is absent."""
        d = {"a": 1}
        assert get_item(d, "missing") is None

    def test_none_dict_returns_none(self):
        """Returns None when the dictionary itself is None."""
        assert get_item(None, "key") is None

    def test_empty_dict_returns_none(self):
        """Returns None when the dictionary is empty."""
        assert get_item({}, "key") is None

    def test_falsy_value_is_returned(self):
        """A key mapped to 0 or False is returned, not treated as missing."""
        assert get_item({"x": 0}, "x") == 0
        assert get_item({"y": False}, "y") is False

    def test_nested_value(self):
        """Works with nested dicts as values."""
        d = {"threshold": {"min": 10, "max": 50}}
        assert get_item(d, "threshold") == {"min": 10, "max": 50}

    def test_string_key_lookup(self):
        """String keys are looked up correctly."""
        d = {"energy_in_kcal": 2100.5}
        assert get_item(d, "energy_in_kcal") == pytest.approx(2100.5)
