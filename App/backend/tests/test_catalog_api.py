import pytest


def test_health(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


def test_empty_catalog(client):
    response = client.get("/api/products")
    assert response.status_code == 200
    assert response.json() == []


def test_catalog_and_detail_include_variants(client, catalog):
    response = client.get("/api/products")
    assert response.status_code == 200
    products = response.json()
    assert [p["id"] for p in products] == [1, 2]
    detail = client.get("/api/products/1")
    assert detail.status_code == 200
    assert detail.json() == products[0]
    assert products[0]["dimensions"] == [
        {"id": 1, "name": "颜色", "values": [{"id": 1, "value": "红色"}]}
    ]
    skus = {sku["id"]: sku for sku in products[0]["skus"]}
    assert skus[1]["option_value_ids"] == [1]
    assert skus[1]["price"] == 19.9
    assert skus[2]["available_quantity"] == 0
    assert skus[3]["is_available"] is False
    assert products[1]["skus"] == products[1]["dimensions"] == []
    assert products[1]["description"] is None


@pytest.mark.parametrize("product_id", [0, -1, 999999])
def test_missing_product(client, catalog, product_id):
    response = client.get(f"/api/products/{product_id}")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PRODUCT_NOT_FOUND"


@pytest.mark.parametrize("product_id", ["abc", "1.5"])
def test_invalid_product_path(client, product_id):
    response = client.get(f"/api/products/{product_id}")
    assert response.status_code == 422
