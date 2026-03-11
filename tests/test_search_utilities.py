import pytest
from meals.views import (
    normalize_umlauts,
    _umlaut_search_variants,
    parse_food_search,
    get_food_search_query,
    get_food_ids_by_alias,
)
from meals.models import Food, FoodAlias, ALIAS_CACHE_KEY
from django.core.cache import cache
from django.db.models import Q


def test_normalize_umlauts():
    assert normalize_umlauts("Möhre") == "Mohre"
    assert normalize_umlauts("Gemüse") == "Gemuse"
    assert normalize_umlauts("Äpfel") == "Apfel"
    assert normalize_umlauts("Öl") == "Ol"
    assert normalize_umlauts("Übung") == "Ubung"
    assert normalize_umlauts("NoUmlauts") == "NoUmlauts"


def test_umlaut_search_variants_basic():
    # ä -> a, but also a -> ä
    variants = _umlaut_search_variants("Mohre")
    assert "Möhre" in variants

    variants = _umlaut_search_variants("Möhre")
    assert "Mohre" in variants


def test_umlaut_search_variants_multiple():
    # "Gemuse" -> should find "Gemüse", "Gemuße" is not handled but "u" and "e" are not both umlautable pairs here, only u->ü
    # wait, the code handles a, o, u
    variants = _umlaut_search_variants("Gemuse")
    assert "Gemüse" in variants

    # "Kase" -> "Käse"
    variants = _umlaut_search_variants("Kase")
    assert "Käse" in variants


def test_umlaut_search_variants_permutations():
    # "Apfelmus" -> "Äpfelmus"
    variants = _umlaut_search_variants("Apfelmus")
    assert "Äpfelmus" in variants

    # "Banane" has 'a' which can be 'ä' in German (though incorrect here, the algorithm allows it)
    variants = _umlaut_search_variants("Banane")
    assert "Bänäne" in variants


def test_parse_food_search():
    # Low energy
    intent, high, clean = parse_food_search("low energy apple")
    assert intent is True
    assert high is False
    assert clean == "apple"

    # High kcal
    intent, high, clean = parse_food_search("high kcal steak")
    assert intent is False
    assert high is True
    assert clean == "steak"

    # Multiple keywords - the current regex is not designed for multiple intents
    # and might leave some parts behind. This test verifies current (albeit imperfect) behavior.
    _, _, clean = parse_food_search("high energy low calorie chicken")
    assert "chicken" in clean


@pytest.mark.django_db
def test_get_food_search_query():
    query = get_food_search_query("Apple")
    assert isinstance(query, Q)
    # It should contain Q(name__icontains="Apple") etc.
    # We can't easily check exactly what's inside without inspecting children,
    # but we can verify it works by applying it to a queryset.
    Food.objects.create(
        bls_code="A1", name="Apple", energy_in_kj_per_100g=0, energy_in_kcal_per_100g=0
    )
    assert Food.objects.filter(query).count() == 1


@pytest.mark.django_db
def test_get_food_ids_by_alias():
    f = Food.objects.create(
        bls_code="A2", name="Apple", energy_in_kj_per_100g=0, energy_in_kcal_per_100g=0
    )
    FoodAlias.objects.create(food=f, alias="Forbidden")

    # Invalidate cache to be sure
    cache.delete(ALIAS_CACHE_KEY)

    ids = get_food_ids_by_alias("Forbidden")
    assert f.id in ids

    # Case insensitive
    ids = get_food_ids_by_alias("forbidden")
    assert f.id in ids

    # Umlaut tolerant
    FoodAlias.objects.create(food=f, alias="Äpfelchen")
    cache.delete(ALIAS_CACHE_KEY)
    ids = get_food_ids_by_alias("Apfelchen")  # Normalized search finds Äpfelchen
    assert f.id in ids


@pytest.mark.django_db
def test_alias_cache_invalidation():
    # Ensure starting from a clean cache state
    cache.delete(ALIAS_CACHE_KEY)

    f = Food.objects.create(
        bls_code="A3", name="Banana", energy_in_kj_per_100g=0, energy_in_kcal_per_100g=0
    )

    # Initial state
    assert cache.get(ALIAS_CACHE_KEY) is None

    # Creating an alias should invalidate (though it was already None)
    alias = FoodAlias.objects.create(food=f, alias="Yellow")
    assert cache.get(ALIAS_CACHE_KEY) is None

    # Now trigger index build
    from meals.models import get_alias_index

    index = get_alias_index()
    assert f.id in index
    assert "Yellow" in index[f.id]
    assert cache.get(ALIAS_CACHE_KEY) is not None

    # Deleting alias should invalidate
    alias.delete()
    assert cache.get(ALIAS_CACHE_KEY) is None
