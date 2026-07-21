from app.services.enrichment import compute_completeness_score, flag_needs_review, _to_string


def test_completeness_score_all_fields_filled():
    data = {
        "material": "mesh",
        "use_case": "running",
        "size_range": "M-XL",
        "gender": "unisex",
        "weather_resistance": "water-resistant",
    }
    assert compute_completeness_score(data) == 1.0


def test_completeness_score_partial_fields():
    data = {
        "material": "mesh",
        "use_case": "running",
        "size_range": None,
        "gender": None,
        "weather_resistance": None,
    }
    assert compute_completeness_score(data) == 0.4


def test_completeness_score_no_fields():
    data = {"material": None, "use_case": None, "size_range": None, "gender": None, "weather_resistance": None}
    assert compute_completeness_score(data) == 0.0


def test_needs_review_flags_vague_values():
    data = {
        "material": "various",
        "use_case": "running",
        "size_range": None,
        "gender": None,
        "weather_resistance": None,
    }
    assert flag_needs_review(data) is True


def test_needs_review_false_for_clean_data():
    data = {
        "material": "mesh",
        "use_case": "running",
        "size_range": None,
        "gender": None,
        "weather_resistance": None,
    }
    assert flag_needs_review(data) is False


def test_to_string_converts_list():
    assert _to_string(["leather", "suede"]) == "leather, suede"


def test_to_string_leaves_string_unchanged():
    assert _to_string("mesh") == "mesh"


def test_to_string_leaves_none_unchanged():
    assert _to_string(None) is None


from app.services.enrichment import enrich_and_save


class FakeLLMClient:
    """A stand-in for LLMClient that returns canned responses instead of calling Gemini."""
    def __init__(self, fake_response):
        self.fake_response = fake_response

    def enrich(self, name, description):
        return self.fake_response


class FakeProductRepository:
    """A stand-in for ProductRepository that stores data in memory instead of a real database."""
    def __init__(self):
        self.saved_products = []

    def save(self, product_record):
        product_record["id"] = len(self.saved_products) + 1
        self.saved_products.append(product_record)
        return product_record


def test_enrich_and_save_with_good_data():
    fake_llm = FakeLLMClient({
        "material": "mesh",
        "use_case": "running",
        "size_range": None,
        "gender": "unisex",
        "weather_resistance": "water-resistant",
    })
    fake_repo = FakeProductRepository()

    result = enrich_and_save("Trail Runner Pro", "A lightweight running shoe.", fake_llm, fake_repo)

    assert result["status"] == "completed"
    assert result["material"] == "mesh"
    assert result["completeness_score"] == 0.8
    assert len(fake_repo.saved_products) == 1


def test_enrich_and_save_with_list_values():
    fake_llm = FakeLLMClient({
        "material": ["leather", "suede", "rubber"],
        "use_case": ["lifestyle", "casual"],
        "size_range": None,
        "gender": None,
        "weather_resistance": None,
    })
    fake_repo = FakeProductRepository()

    result = enrich_and_save("Some Shoe", "A shoe with multiple materials.", fake_llm, fake_repo)

    assert result["material"] == "leather, suede, rubber"
    assert result["use_case"] == "lifestyle, casual"
    assert isinstance(result["material"], str)


def test_enrich_and_save_with_parse_failure():
    fake_llm = FakeLLMClient({"_parse_failed": True, "_raw_response": "garbage text"})
    fake_repo = FakeProductRepository()

    result = enrich_and_save("Broken Product", "Some description.", fake_llm, fake_repo)

    assert result["status"] == "enrichment_failed"
    assert result["needs_review"] is True
    assert result["completeness_score"] == 0.0