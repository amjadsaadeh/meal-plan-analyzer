import pytest
from django.core.cache import cache
from rest_framework import status
from meals.models import Food, FoodAlias, ALIAS_CACHE_KEY
from meals.models import get_alias_index

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_food(**kwargs):
    """Create a minimal Food instance for testing."""
    defaults = dict(
        bls_code="TEST001",
        name="Testfood",
        energy_in_kj_per_100g=100.0,
        energy_in_kcal_per_100g=24.0,
        protein_in_g_per_100g=1.0,
        fat_in_g_per_100g=0.5,
        carbohydrate_in_g_per_100g=4.0,
        fibre_in_g_per_100g=0.5,
        iron_in_mg_per_100g=0.1,
        sugar_in_g_per_100g=2.0,
        omega3_in_g_per_100g=0.01,
        vitc_in_mg_per_100g=1.0,
        magnesium_in_mg_per_100g=5.0,
        zinc_in_mg_per_100g=0.1,
        vitb12_in_mug_per_100g=0.0,
        vita_in_mug_per_100g=0.0,
        calcium_in_mg_per_100g=10.0,
        vitd_in_mug_per_100g=0.0,
    )
    defaults.update(kwargs)
    return Food.objects.create(**defaults)


# ---------------------------------------------------------------------------
# Existing tests (unchanged behaviour)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFoodAPI:
    def test_list_foods_unauthenticated(self, api_client):
        """Test getting all foods without authentication."""
        response = api_client.get("/api/foods/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_foods_authenticated(self, authenticated_client):
        """Test getting all foods with authentication (paginated)."""
        response = authenticated_client.get("/api/foods/")
        assert response.status_code == status.HTTP_200_OK
        # Without a search query the endpoint returns paginated results
        assert "results" in response.data
        assert isinstance(response.data["results"], list)
        assert response.data["count"] == 100

    def test_get_single_food_unauthenticated(self, api_client):
        """Test getting a single food item without authentication."""
        food = Food.objects.first()
        response = api_client.get(f"/api/foods/{food.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_single_food_authenticated(self, authenticated_client):
        """Test getting a single food item with authentication."""
        food = Food.objects.first()
        response = authenticated_client.get(f"/api/foods/{food.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == food.name
        assert response.data["bls_code"] == food.bls_code

    def test_create_food_unauthenticated(self, api_client):
        """Test creating a new food item without authentication."""
        payload = {"bls_code": "NEWFOOD123", "name": "Test Apple"}
        response = api_client.post("/api/foods/", payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_food_authenticated(self, authenticated_client):
        """Test creating a new custom food item with authentication."""
        payload = {"name": "My Custom Apple"}
        response = authenticated_client.post("/api/foods/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.data
        assert data["name"] == "My Custom Apple"
        assert data["data_source"] == "custom"
        assert data["bls_code"].startswith("custom_")
        assert Food.objects.filter(bls_code=data["bls_code"]).exists()

    def test_search_foods_name_unauthenticated(self, api_client):
        """Test searching for foods without authentication."""
        response = api_client.get("/api/foods/?search=Apfel")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_search_foods_name_authenticated(self, authenticated_client):
        """Test searching for foods by name with authentication."""
        food = Food.objects.get(pk=1)
        search_term = food.name[:10]
        response = authenticated_client.get(f"/api/foods/?search={search_term}")
        assert response.status_code == status.HTTP_200_OK
        assert any(item["name"] == food.name for item in response.data)

    def test_search_foods_semantic_low_energy_authenticated(self, authenticated_client):
        """Test the 'low energy' semantic search intent with authentication."""
        response = authenticated_client.get("/api/foods/?search=low energy")
        assert response.status_code == status.HTTP_200_OK
        energies = [item["energy_in_kcal_per_100g"] for item in response.data]
        assert energies == sorted(energies)

    # ------------------------------------------------------------------
    # matched_alias field is always present
    # ------------------------------------------------------------------

    def test_food_list_has_matched_alias_field(self, authenticated_client):
        """Every food in the list response exposes matched_alias."""
        response = authenticated_client.get("/api/foods/")
        assert response.status_code == status.HTTP_200_OK
        items = response.data.get("results", response.data)
        for item in items:
            assert "matched_alias" in item

    def test_food_detail_has_matched_alias_field(self, authenticated_client):
        """Single food detail endpoint exposes matched_alias."""
        food = Food.objects.first()
        response = authenticated_client.get(f"/api/foods/{food.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert "matched_alias" in response.data

    def test_name_search_matched_alias_is_null(self, authenticated_client):
        """Foods found by name/bls_code match should have matched_alias=null."""
        food = Food.objects.get(pk=1)
        response = authenticated_client.get(f"/api/foods/?search={food.name[:6]}")
        assert response.status_code == status.HTTP_200_OK
        for item in response.data:
            if item["id"] == food.id:
                assert item["matched_alias"] is None
                break


# ---------------------------------------------------------------------------
# Alias search tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFoodAliasSearch:
    """Tests for alias-based food search."""

    def setup_method(self):
        # Ensure the alias cache is clear before every test
        cache.delete(ALIAS_CACHE_KEY)

    def teardown_method(self):
        cache.delete(ALIAS_CACHE_KEY)

    # ------------------------------------------------------------------
    # Model / cache tests
    # ------------------------------------------------------------------

    def test_alias_index_is_empty_when_no_aliases_exist(self):
        """get_alias_index returns an empty dict when no FoodAlias rows exist."""
        assert FoodAlias.objects.count() == 0
        index = get_alias_index()
        assert index == {}

    def test_alias_index_populated_after_creation(self):
        """get_alias_index reflects newly created aliases."""
        food = _make_food(bls_code="ALIAS001", name="Hühnerbrust")
        FoodAlias.objects.create(food=food, alias="Chicken breast")
        index = get_alias_index()
        assert food.id in index
        assert "Chicken breast" in index[food.id]

    def test_alias_index_cached_after_first_call(self):
        """Second call to get_alias_index returns the cached value."""
        food = _make_food(bls_code="ALIAS002", name="Lachs")
        FoodAlias.objects.create(food=food, alias="Salmon")
        # First call builds and caches
        get_alias_index()
        assert cache.get(ALIAS_CACHE_KEY) is not None
        # Second call hits the cache (we verify the key is still there)
        index2 = get_alias_index()
        assert food.id in index2

    def test_cache_invalidated_on_alias_create(self):
        """Creating a FoodAlias clears the alias cache."""
        food = _make_food(bls_code="ALIAS003", name="Rind")
        get_alias_index()  # populate cache
        FoodAlias.objects.create(food=food, alias="Beef")
        assert cache.get(ALIAS_CACHE_KEY) is None

    def test_cache_invalidated_on_alias_delete(self):
        """Deleting a FoodAlias clears the alias cache."""
        food = _make_food(bls_code="ALIAS004", name="Schwein")
        fa = FoodAlias.objects.create(food=food, alias="Pork")
        get_alias_index()  # populate cache
        fa.delete()
        assert cache.get(ALIAS_CACHE_KEY) is None

    def test_multiple_aliases_per_food(self):
        """A food can have multiple aliases all stored in the index."""
        food = _make_food(bls_code="ALIAS005", name="Kartoffel")
        FoodAlias.objects.create(food=food, alias="Potato")
        FoodAlias.objects.create(food=food, alias="Spud")
        index = get_alias_index()
        assert set(index[food.id]) == {"Potato", "Spud"}

    # ------------------------------------------------------------------
    # API endpoint tests
    # ------------------------------------------------------------------

    def test_search_by_alias_returns_food(self, authenticated_client):
        """Searching for an alias term returns the associated food."""
        food = _make_food(bls_code="ALIAS010", name="Apfel")
        FoodAlias.objects.create(food=food, alias="Malum")
        cache.delete(ALIAS_CACHE_KEY)

        response = authenticated_client.get("/api/foods/?search=Malum")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data]
        assert food.id in ids

    def test_alias_match_has_matched_alias_set(self, authenticated_client):
        """Foods returned via alias match carry the alias string in matched_alias."""
        food = _make_food(bls_code="ALIAS011", name="Birne")
        FoodAlias.objects.create(food=food, alias="Pear")
        cache.delete(ALIAS_CACHE_KEY)

        response = authenticated_client.get("/api/foods/?search=Pear")
        assert response.status_code == status.HTTP_200_OK
        matched = next((item for item in response.data if item["id"] == food.id), None)
        assert matched is not None
        assert matched["matched_alias"] == "Pear"

    def test_alias_search_is_case_insensitive(self, authenticated_client):
        """Alias matching ignores letter case."""
        food = _make_food(bls_code="ALIAS012", name="Tomate")
        FoodAlias.objects.create(food=food, alias="Tomato")
        cache.delete(ALIAS_CACHE_KEY)

        response = authenticated_client.get("/api/foods/?search=tomato")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data]
        assert food.id in ids

        response_upper = authenticated_client.get("/api/foods/?search=TOMATO")
        assert food.id in [item["id"] for item in response_upper.data]

    def test_alias_partial_match(self, authenticated_client):
        """A partial term contained in an alias still returns the food."""
        food = _make_food(bls_code="ALIAS013", name="Erdbeere")
        FoodAlias.objects.create(food=food, alias="Strawberry")
        cache.delete(ALIAS_CACHE_KEY)

        # "strawb" is a substring of "Strawberry"
        response = authenticated_client.get("/api/foods/?search=strawb")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data]
        assert food.id in ids

    def test_name_match_does_not_get_alias_badge(self, authenticated_client):
        """Foods found by their actual name do not get a matched_alias even if they also have aliases."""
        food = _make_food(bls_code="ALIAS014", name="Mango")
        FoodAlias.objects.create(food=food, alias="AnotherName")
        cache.delete(ALIAS_CACHE_KEY)

        # Search by actual name
        response = authenticated_client.get("/api/foods/?search=Mango")
        assert response.status_code == status.HTTP_200_OK
        matched = next((item for item in response.data if item["id"] == food.id), None)
        assert matched is not None
        assert matched["matched_alias"] is None

    def test_alias_only_result_appears_after_name_results(self, authenticated_client):
        """Foods matched by alias come after name-matched results in the response."""
        food_name = _make_food(bls_code="ALIAS015", name="Zitrone")
        food_alias = _make_food(bls_code="ALIAS016", name="Unrelated XYZ")
        FoodAlias.objects.create(food=food_alias, alias="Zitrone alias")
        cache.delete(ALIAS_CACHE_KEY)

        response = authenticated_client.get("/api/foods/?search=Zitrone")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data]
        assert food_name.id in ids
        assert food_alias.id in ids
        # Name match comes first
        assert ids.index(food_name.id) < ids.index(food_alias.id)

    def test_no_duplicate_when_both_name_and_alias_match(self, authenticated_client):
        """A food matching by both name and alias appears only once."""
        food = _make_food(bls_code="ALIAS017", name="Banane")
        FoodAlias.objects.create(food=food, alias="Banane gelb")
        cache.delete(ALIAS_CACHE_KEY)

        response = authenticated_client.get("/api/foods/?search=Banane")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data]
        assert ids.count(food.id) == 1

    def test_short_query_below_threshold_returns_nothing(self, authenticated_client):
        """Queries shorter than 2 chars return an empty list."""
        food = _make_food(bls_code="ALIAS018", name="Ei")
        FoodAlias.objects.create(food=food, alias="E")
        cache.delete(ALIAS_CACHE_KEY)

        response = authenticated_client.get("/api/foods/?search=E")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []


# ---------------------------------------------------------------------------
# Real-world German dialect alias scenarios
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRealWorldAliases:
    """Tests with realistic German regional/dialect synonyms.

    Setup
    -----
    - Kartoffeln  → aliases: Erdäpfel, Krumbirnen
    - Tomate      → alias:   Paradeisa
    - Gemüsebrühe → alias:   Suppe
    - Knochenbrühe → alias:  Suppe          (same alias shared by two foods)
    """

    @pytest.fixture(autouse=True)
    def setup_foods(self, db):
        cache.delete(ALIAS_CACHE_KEY)

        self.kartoffeln = _make_food(bls_code="RW001", name="Kartoffeln")
        FoodAlias.objects.create(food=self.kartoffeln, alias="Erdäpfel")
        FoodAlias.objects.create(food=self.kartoffeln, alias="Krumbirnen")

        self.tomate = _make_food(bls_code="RW002", name="Tomate")
        FoodAlias.objects.create(food=self.tomate, alias="Paradeisa")

        self.gemuesebruehe = _make_food(bls_code="RW003", name="Gemüsebrühe")
        FoodAlias.objects.create(food=self.gemuesebruehe, alias="Suppe")

        self.knochenbruehe = _make_food(bls_code="RW004", name="Knochenbrühe")
        FoodAlias.objects.create(food=self.knochenbruehe, alias="Suppe")

        # Ensure fresh cache after creating all aliases
        cache.delete(ALIAS_CACHE_KEY)
        yield
        cache.delete(ALIAS_CACHE_KEY)

    # ------------------------------------------------------------------
    # Kartoffeln / Erdäpfel / Krumbirnen
    # ------------------------------------------------------------------

    def test_kartoffeln_found_by_erdaepfel(self, authenticated_client):
        """Searching 'Erdäpfel' (Austrian dialect) returns Kartoffeln."""
        response = authenticated_client.get("/api/foods/?search=Erdäpfel")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data]
        assert self.kartoffeln.id in ids

    def test_kartoffeln_erdaepfel_sets_matched_alias(self, authenticated_client):
        """matched_alias is set to 'Erdäpfel' when found via that alias."""
        response = authenticated_client.get("/api/foods/?search=Erdäpfel")
        item = next(i for i in response.data if i["id"] == self.kartoffeln.id)
        assert item["matched_alias"] == "Erdäpfel"

    def test_kartoffeln_found_by_krumbirnen(self, authenticated_client):
        """Searching 'Krumbirnen' (regional dialect) returns Kartoffeln."""
        response = authenticated_client.get("/api/foods/?search=Krumbirnen")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data]
        assert self.kartoffeln.id in ids

    def test_kartoffeln_krumbirnen_sets_matched_alias(self, authenticated_client):
        """matched_alias is set to 'Krumbirnen' when found via that alias."""
        response = authenticated_client.get("/api/foods/?search=Krumbirnen")
        item = next(i for i in response.data if i["id"] == self.kartoffeln.id)
        assert item["matched_alias"] == "Krumbirnen"

    def test_kartoffeln_partial_erdaepf(self, authenticated_client):
        """Partial term 'Erdäpf' is enough to match the alias 'Erdäpfel'."""
        response = authenticated_client.get("/api/foods/?search=Erdäpf")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data]
        assert self.kartoffeln.id in ids

    def test_kartoffeln_index_has_both_aliases(self):
        """The alias index contains both 'Erdäpfel' and 'Krumbirnen' for Kartoffeln."""
        index = get_alias_index()
        assert self.kartoffeln.id in index
        assert set(index[self.kartoffeln.id]) == {"Erdäpfel", "Krumbirnen"}

    def test_kartoffeln_by_name_has_no_alias_badge(self, authenticated_client):
        """Searching the real name 'Kartoffeln' does not set matched_alias."""
        response = authenticated_client.get("/api/foods/?search=Kartoffeln")
        item = next((i for i in response.data if i["id"] == self.kartoffeln.id), None)
        assert item is not None
        assert item["matched_alias"] is None

    # ------------------------------------------------------------------
    # Tomate / Paradeisa
    # ------------------------------------------------------------------

    def test_tomate_found_by_paradeisa(self, authenticated_client):
        """Searching 'Paradeisa' (Bavarian/Austrian word for tomato) returns Tomate."""
        response = authenticated_client.get("/api/foods/?search=Paradeisa")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data]
        assert self.tomate.id in ids

    def test_tomate_paradeisa_sets_matched_alias(self, authenticated_client):
        """matched_alias is 'Paradeisa' when Tomate is found via that alias."""
        response = authenticated_client.get("/api/foods/?search=Paradeisa")
        item = next(i for i in response.data if i["id"] == self.tomate.id)
        assert item["matched_alias"] == "Paradeisa"

    def test_tomate_partial_paradeis(self, authenticated_client):
        """Partial term 'Paradeis' matches the alias 'Paradeisa'."""
        response = authenticated_client.get("/api/foods/?search=Paradeis")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data]
        assert self.tomate.id in ids

    def test_tomate_paradeisa_case_insensitive(self, authenticated_client):
        """Alias search for 'paradeisa' (lowercase) still finds Tomate."""
        response = authenticated_client.get("/api/foods/?search=paradeisa")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data]
        assert self.tomate.id in ids

    # ------------------------------------------------------------------
    # Shared alias "Suppe" → Gemüsebrühe AND Knochenbrühe
    # ------------------------------------------------------------------

    def test_suppe_returns_both_bruehe_foods(self, authenticated_client):
        """Searching 'Suppe' returns both Gemüsebrühe and Knochenbrühe."""
        response = authenticated_client.get("/api/foods/?search=Suppe")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data]
        assert self.gemuesebruehe.id in ids
        assert self.knochenbruehe.id in ids

    def test_suppe_both_foods_have_matched_alias_suppe(self, authenticated_client):
        """Both foods found via 'Suppe' carry matched_alias='Suppe'."""
        response = authenticated_client.get("/api/foods/?search=Suppe")
        by_id = {item["id"]: item for item in response.data}
        assert by_id[self.gemuesebruehe.id]["matched_alias"] == "Suppe"
        assert by_id[self.knochenbruehe.id]["matched_alias"] == "Suppe"

    def test_suppe_each_food_appears_exactly_once(self, authenticated_client):
        """No duplicates: each brühe food appears exactly once in the results."""
        response = authenticated_client.get("/api/foods/?search=Suppe")
        ids = [item["id"] for item in response.data]
        assert ids.count(self.gemuesebruehe.id) == 1
        assert ids.count(self.knochenbruehe.id) == 1

    def test_suppe_partial_supp(self, authenticated_client):
        """Partial term 'Supp' is enough to match both brühe foods via alias."""
        response = authenticated_client.get("/api/foods/?search=Supp")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data]
        assert self.gemuesebruehe.id in ids
        assert self.knochenbruehe.id in ids

    def test_suppe_alias_index_has_both_food_ids(self):
        """The alias index maps both brühe food IDs to an alias list containing 'Suppe'."""
        index = get_alias_index()
        assert "Suppe" in index.get(self.gemuesebruehe.id, [])
        assert "Suppe" in index.get(self.knochenbruehe.id, [])

    def test_gemuesebruehe_by_name_has_no_alias_badge(self, authenticated_client):
        """Searching 'Gemüsebrühe' by name gives matched_alias=None."""
        response = authenticated_client.get("/api/foods/?search=Gemüsebrühe")
        item = next(
            (i for i in response.data if i["id"] == self.gemuesebruehe.id), None
        )
        assert item is not None
        assert item["matched_alias"] is None

    def test_knochenbruehe_by_name_has_no_alias_badge(self, authenticated_client):
        """Searching 'Knochenbrühe' by name gives matched_alias=None."""
        response = authenticated_client.get("/api/foods/?search=Knochenbrühe")
        item = next(
            (i for i in response.data if i["id"] == self.knochenbruehe.id), None
        )
        assert item is not None
        assert item["matched_alias"] is None

    # ------------------------------------------------------------------
    # Umlaut tolerance: typing without umlaut still finds the right food
    # ------------------------------------------------------------------

    def test_kartoffeln_found_by_erdapfel_without_umlaut(self, authenticated_client):
        """'Erdapfel' (no ä) matches alias 'Erdäpfel' via umlaut normalisation."""
        response = authenticated_client.get("/api/foods/?search=Erdapfel")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data]
        assert self.kartoffeln.id in ids

    def test_kartoffeln_erdapfel_matched_alias_is_original_form(
        self, authenticated_client
    ):
        """matched_alias contains the original alias string ('Erdäpfel'), not the normalised form."""
        response = authenticated_client.get("/api/foods/?search=Erdapfel")
        item = next(i for i in response.data if i["id"] == self.kartoffeln.id)
        assert item["matched_alias"] == "Erdäpfel"

    def test_knochenbruehe_found_by_name_without_umlaut(self, authenticated_client):
        """'Knochenbruhe' (no ü) finds 'Knochenbrühe' by name via DB umlaut expansion."""
        response = authenticated_client.get("/api/foods/?search=Knochenbruhe")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data]
        assert self.knochenbruehe.id in ids

    def test_gemuesebruehe_found_by_name_with_missing_second_umlaut(
        self, authenticated_client
    ):
        """'Gemüsebruhe' (ü in first syllable, plain u in second) still finds 'Gemüsebrühe'."""
        response = authenticated_client.get("/api/foods/?search=Gemüsebruhe")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data]
        assert self.gemuesebruehe.id in ids

    def test_gemuesebruehe_found_when_both_umlauts_omitted(self, authenticated_client):
        """'Gemusebruhe' (both ü → u) still finds 'Gemüsebrühe' via combinatorial expansion."""
        response = authenticated_client.get("/api/foods/?search=Gemusebruhe")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data]
        assert self.gemuesebruehe.id in ids

    def test_knochenbruehe_found_when_umlaut_omitted(self, authenticated_client):
        """'Knochenbruhe' (ü → u) finds 'Knochenbrühe' via umlaut expansion."""
        response = authenticated_client.get("/api/foods/?search=Knochenbruhe")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data]
        assert self.knochenbruehe.id in ids


# ---------------------------------------------------------------------------
# Systematic umlaut normalisation tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUmlautNormalization:
    """Verify ä↔a, ö↔o, ü↔u equivalence in both alias search and DB name search.

    Two matching directions are tested for each umlaut:

    * **Case A** – alias HAS the umlaut, user types WITHOUT it
      (e.g. alias "Bösel", search "Bosel")
    * **Case B** – alias is plain ASCII, user types WITH the umlaut
      (e.g. alias "Mohre", search "Möhre")
    * **Case C** – food *name* has the umlaut, user types without
      (e.g. food "Möhre", search "Mohre") – tests the DB-side expansion
    """

    @pytest.fixture(autouse=True)
    def setup_foods(self, db):
        cache.delete(ALIAS_CACHE_KEY)

        # --- Case A: alias HAS umlaut, user omits it ---
        # ö
        self.rind = _make_food(bls_code="UM001", name="Rindfleisch")
        FoodAlias.objects.create(food=self.rind, alias="Bösel")
        # ä
        self.haehnchen = _make_food(bls_code="UM002", name="Brathähnchen")
        FoodAlias.objects.create(food=self.haehnchen, alias="Hähnchen")
        # ü
        self.karotte = _make_food(bls_code="UM003", name="Karotte")
        FoodAlias.objects.create(food=self.karotte, alias="Rübli")

        # --- Case B: alias is plain, user types WITH the umlaut ---
        # ö: alias "Mohre", search "Möhre"
        self.rettich = _make_food(bls_code="UM004", name="Rettich")
        FoodAlias.objects.create(food=self.rettich, alias="Mohre")
        # ä: alias "Hahnchen", search "Hähnchen"  (food name is unrelated)
        self.gefluegel = _make_food(bls_code="UM005", name="Geflügel")
        FoodAlias.objects.create(food=self.gefluegel, alias="Hahnchen")
        # ü: alias "Rubli", search "Rübli"
        self.rotkohl = _make_food(bls_code="UM006", name="Rotkohl")
        FoodAlias.objects.create(food=self.rotkohl, alias="Rubli")

        # --- Case C: food NAME contains umlaut, user types without ---
        self.moehre = _make_food(bls_code="UM007", name="Möhre")  # ö
        self.gruenkohl = _make_food(bls_code="UM008", name="Grünkohl")  # ü
        self.hasenbraten = _make_food(
            bls_code="UM009", name="Häsenbraten"
        )  # ä (fictional)

        # --- Case D: food NAME has NO umlaut, user types WITH wrong umlaut ---
        # (e.g. "Tomate" in DB, user accidentally types "Tomäte")
        self.tomate_plain = _make_food(bls_code="UM010", name="Tomate")

        # --- Case E: multi-umlaut food name, user removes ALL umlauts ---
        self.huhnerbruehe = _make_food(bls_code="UM011", name="Hühnerbrühe")  # two ü

        cache.delete(ALIAS_CACHE_KEY)
        yield
        cache.delete(ALIAS_CACHE_KEY)

    # ------------------------------------------------------------------
    # Case A – alias HAS umlaut, user types WITHOUT
    # ------------------------------------------------------------------

    def test_oe_alias_found_without_umlaut(self, authenticated_client):
        """'Bosel' (no ö) matches alias 'Bösel' → returns Rindfleisch."""
        response = authenticated_client.get("/api/foods/?search=Bosel")
        assert response.status_code == status.HTTP_200_OK
        assert self.rind.id in [i["id"] for i in response.data]

    def test_oe_alias_matched_alias_is_original(self, authenticated_client):
        """matched_alias is 'Bösel' (original with ö), not the normalised 'Bosel'."""
        response = authenticated_client.get("/api/foods/?search=Bosel")
        item = next(i for i in response.data if i["id"] == self.rind.id)
        assert item["matched_alias"] == "Bösel"

    def test_ae_alias_found_without_umlaut(self, authenticated_client):
        """'Hahnchen' (no ä) matches alias 'Hähnchen' → returns Brathähnchen."""
        response = authenticated_client.get("/api/foods/?search=Hahnchen")
        assert response.status_code == status.HTTP_200_OK
        assert self.haehnchen.id in [i["id"] for i in response.data]

    def test_ae_alias_matched_alias_is_original(self, authenticated_client):
        """matched_alias is 'Hähnchen' (with ä), not 'Hahnchen'."""
        response = authenticated_client.get("/api/foods/?search=Hahnchen")
        # self.haehnchen may appear as a NAME match (name contains "Hähnchen");
        # it should still have matched_alias=None in that case.
        item = next(i for i in response.data if i["id"] == self.haehnchen.id)
        # Name match takes priority → matched_alias is None
        assert item["matched_alias"] is None

    def test_ue_alias_found_without_umlaut(self, authenticated_client):
        """'Rubli' (no ü) matches alias 'Rübli' → returns Karotte."""
        response = authenticated_client.get("/api/foods/?search=Rubli")
        assert response.status_code == status.HTTP_200_OK
        assert self.karotte.id in [i["id"] for i in response.data]

    def test_ue_alias_matched_alias_is_original(self, authenticated_client):
        """matched_alias is 'Rübli' (with ü), not 'Rubli'."""
        response = authenticated_client.get("/api/foods/?search=Rubli")
        item = next(i for i in response.data if i["id"] == self.karotte.id)
        assert item["matched_alias"] == "Rübli"

    def test_case_a_partial_without_umlaut(self, authenticated_client):
        """Partial term 'Bos' (no ö) still matches alias 'Bösel'."""
        response = authenticated_client.get("/api/foods/?search=Bos")
        assert response.status_code == status.HTTP_200_OK
        assert self.rind.id in [i["id"] for i in response.data]

    def test_case_a_uppercase_without_umlaut(self, authenticated_client):
        """Uppercase 'BOSEL' (no ö) still matches alias 'Bösel'."""
        response = authenticated_client.get("/api/foods/?search=BOSEL")
        assert response.status_code == status.HTTP_200_OK
        assert self.rind.id in [i["id"] for i in response.data]

    # ------------------------------------------------------------------
    # Case B – alias is plain ASCII, user types WITH the umlaut
    # ------------------------------------------------------------------

    def test_oe_search_matches_plain_alias(self, authenticated_client):
        """'Möhre' (with ö) matches plain alias 'Mohre' → returns Rettich."""
        response = authenticated_client.get("/api/foods/?search=Möhre")
        assert response.status_code == status.HTTP_200_OK
        assert self.rettich.id in [i["id"] for i in response.data]

    def test_oe_search_plain_alias_matched_alias_set(self, authenticated_client):
        """matched_alias is 'Mohre' (plain) when found via 'Möhre' search."""
        response = authenticated_client.get("/api/foods/?search=Möhre")
        item = next(i for i in response.data if i["id"] == self.rettich.id)
        assert item["matched_alias"] == "Mohre"

    def test_ae_search_matches_plain_alias(self, authenticated_client):
        """'Hähnchen' (with ä) matches plain alias 'Hahnchen' → returns Geflügel."""
        response = authenticated_client.get("/api/foods/?search=Hähnchen")
        assert response.status_code == status.HTTP_200_OK
        assert self.gefluegel.id in [i["id"] for i in response.data]

    def test_ue_search_matches_plain_alias(self, authenticated_client):
        """'Rübli' (with ü) matches plain alias 'Rubli' → returns Rotkohl."""
        response = authenticated_client.get("/api/foods/?search=Rübli")
        assert response.status_code == status.HTTP_200_OK
        assert self.rotkohl.id in [i["id"] for i in response.data]

    def test_ue_search_plain_alias_matched_alias_set(self, authenticated_client):
        """matched_alias is 'Rubli' (plain) when found via 'Rübli' search."""
        response = authenticated_client.get("/api/foods/?search=Rübli")
        item = next(i for i in response.data if i["id"] == self.rotkohl.id)
        assert item["matched_alias"] == "Rubli"

    # ------------------------------------------------------------------
    # Case C – food NAME has umlaut, user searches without (DB expansion)
    # ------------------------------------------------------------------

    def test_food_name_oe_found_without_umlaut(self, authenticated_client):
        """'Mohre' (no ö) finds food named 'Möhre' via DB umlaut expansion."""
        response = authenticated_client.get("/api/foods/?search=Mohre")
        assert response.status_code == status.HTTP_200_OK
        assert self.moehre.id in [i["id"] for i in response.data]

    def test_food_name_oe_found_with_umlaut(self, authenticated_client):
        """'Möhre' (with ö) finds food named 'Möhre' directly."""
        response = authenticated_client.get("/api/foods/?search=Möhre")
        assert response.status_code == status.HTTP_200_OK
        assert self.moehre.id in [i["id"] for i in response.data]

    def test_food_name_oe_name_match_has_no_alias_badge(self, authenticated_client):
        """Name-matched 'Möhre' (with or without umlaut in query) has matched_alias=None."""
        for query in ("Mohre", "Möhre"):
            response = authenticated_client.get(f"/api/foods/?search={query}")
            item = next((i for i in response.data if i["id"] == self.moehre.id), None)
            assert item is not None, f"'Möhre' not found for query '{query}'"
            assert item["matched_alias"] is None, f"Expected None for query '{query}'"

    def test_food_name_ue_found_without_umlaut(self, authenticated_client):
        """'Grunkohl' (no ü) finds food named 'Grünkohl' via DB umlaut expansion."""
        response = authenticated_client.get("/api/foods/?search=Grunkohl")
        assert response.status_code == status.HTTP_200_OK
        assert self.gruenkohl.id in [i["id"] for i in response.data]

    def test_food_name_ae_found_without_umlaut(self, authenticated_client):
        """'Hasenbraten' (no ä) finds food named 'Häsenbraten' via DB umlaut expansion."""
        response = authenticated_client.get("/api/foods/?search=Hasenbraten")
        assert response.status_code == status.HTTP_200_OK
        assert self.hasenbraten.id in [i["id"] for i in response.data]

    # ------------------------------------------------------------------
    # Case D – food NAME has NO umlaut, user types WITH umlaut (wrong key)
    # The normalised form of the query is used to search, so "Tomäte" → "Tomate"
    # ------------------------------------------------------------------

    def test_plain_name_found_by_search_with_wrong_ae(self, authenticated_client):
        """'Tomäte' (spurious ä) finds food named 'Tomate' (no umlaut in DB)."""
        response = authenticated_client.get("/api/foods/?search=Tomäte")
        assert response.status_code == status.HTTP_200_OK
        assert self.tomate_plain.id in [i["id"] for i in response.data]

    def test_plain_name_found_by_search_with_wrong_oe(self, authenticated_client):
        """'Tömäte' (spurious ö and ä) also finds 'Tomate' via normalisation."""
        response = authenticated_client.get("/api/foods/?search=Tömäte")
        assert response.status_code == status.HTTP_200_OK
        assert self.tomate_plain.id in [i["id"] for i in response.data]

    def test_plain_name_matched_alias_is_none(self, authenticated_client):
        """Finding 'Tomate' by a umlauted query still gives matched_alias=None (name match)."""
        response = authenticated_client.get("/api/foods/?search=Tomäte")
        item = next((i for i in response.data if i["id"] == self.tomate_plain.id), None)
        assert item is not None
        assert item["matched_alias"] is None

    # ------------------------------------------------------------------
    # Case E – multi-umlaut food name, user removes ALL umlauts
    # Requires combinatorial expansion (single-substitution is not enough)
    # ------------------------------------------------------------------

    def test_multi_umlaut_name_found_when_all_omitted(self, authenticated_client):
        """'Huhnerbruhe' (both ü → u) finds 'Hühnerbrühe' via combinatorial expansion."""
        response = authenticated_client.get("/api/foods/?search=Huhnerbruhe")
        assert response.status_code == status.HTTP_200_OK
        assert self.huhnerbruehe.id in [i["id"] for i in response.data]

    def test_multi_umlaut_name_found_when_first_omitted(self, authenticated_client):
        """'Hühnerbruhe' (second ü → u) finds 'Hühnerbrühe' via expansion."""
        response = authenticated_client.get("/api/foods/?search=Hühnerbruhe")
        assert response.status_code == status.HTTP_200_OK
        assert self.huhnerbruehe.id in [i["id"] for i in response.data]

    def test_multi_umlaut_name_found_when_second_omitted(self, authenticated_client):
        """'Huhnerbrühe' (first ü → u) finds 'Hühnerbrühe' via expansion."""
        response = authenticated_client.get("/api/foods/?search=Huhnerbrühe")
        assert response.status_code == status.HTTP_200_OK
        assert self.huhnerbruehe.id in [i["id"] for i in response.data]

    def test_multi_umlaut_name_match_has_no_alias_badge(self, authenticated_client):
        """Name-matched 'Hühnerbrühe' (any umlaut variant) has matched_alias=None."""
        for query in ("Huhnerbruhe", "Hühnerbrühe", "Hühnerbruhe"):
            response = authenticated_client.get(f"/api/foods/?search={query}")
            item = next(
                (i for i in response.data if i["id"] == self.huhnerbruehe.id), None
            )
            assert item is not None, f"'Hühnerbrühe' not found for query '{query}'"
            assert item["matched_alias"] is None, f"Expected None for query '{query}'"
