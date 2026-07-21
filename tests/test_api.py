import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.dependencies import get_llm_client, get_product_repo
from app.core.security import verify_api_key


class FakeLLMClient:
    def enrich(self, name, description):
        return {
            "material": "mesh",
            "use_case": "running",
            "size_range": None,
            "gender": "unisex",
            "weather_resistance": "water-resistant",
        }


class FakeProductRepository:
    def __init__(self):
        self.products = {}
        self.next_id = 1

    def save(self, product_record):
        product_record["id"] = self.next_id
        self.products[self.next_id] = product_record
        self.next_id += 1
        return product_record

    def get_by_id(self, product_id):
        return self.products.get(product_id)

    def get_all(self, needs_review=None):
        results = list(self.products.values())
        if needs_review is not None:
            results = [p for p in results if p.get("needs_review") == needs_review]
        return results


fake_repo_instance = FakeProductRepository()


def override_get_llm_client():
    return FakeLLMClient()


def override_get_product_repo():
    return fake_repo_instance


def override_verify_api_key():
    return "test-key"


app.dependency_overrides[get_llm_client] = override_get_llm_client
app.dependency_overrides[get_product_repo] = override_get_product_repo
app.dependency_overrides[verify_api_key] = override_verify_api_key

client = TestClient(app)


def test_enrich_product_success():
    response = client.post(
        "/products/enrich",
        json={"name": "Trail Runner Pro", "description": "A lightweight running shoe."},
        headers={"x-api-key": "any-value-works-since-overridden"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["material"] == "mesh"
    assert data["completeness_score"] == 0.8


def test_get_product_not_found():
    response = client.get(
        "/products/9999",
        headers={"x-api-key": "any-value-works-since-overridden"},
    )
    assert response.status_code == 404


def test_get_product_success():
    create_response = client.post(
        "/products/enrich",
        json={"name": "City Walker", "description": "A comfortable walking shoe."},
        headers={"x-api-key": "any-value"},
    )
    product_id = create_response.json()["id"]

    get_response = client.get(
        f"/products/{product_id}",
        headers={"x-api-key": "any-value"},
    )
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "City Walker"


def test_enrich_product_missing_fields_returns_422():
    response = client.post(
        "/products/enrich",
        json={"name": "Incomplete Product"},  # missing "description"
        headers={"x-api-key": "any-value"},
    )
    assert response.status_code == 422