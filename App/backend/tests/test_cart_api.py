import pytest


def add(client, sku=1, quantity=1, key=None):
    return client.post(
        "/api/cart/items", json={"sku_id": sku, "quantity": quantity},
        headers={"Idempotency-Key": key} if key is not None else {},
    )


def test_empty_cart_is_created_and_reused(client, db_factory):
    from models import Cart

    first = client.get("/api/cart")
    second = client.get("/api/cart")
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["items"] == []
    assert first.json()["total_item_count"] == 0
    with db_factory() as db:
        assert db.query(Cart).count() == 1


def test_success_updates_stock_and_cart_total(client, catalog, snapshot):
    response = add(client, quantity=2, key="purchase-1")
    assert response.status_code == 201
    item = response.json()
    assert item["sku_id"] == 1
    assert item["quantity"] == 2
    assert item["sku"]["available_quantity"] == 3
    assert add(client, sku=4).status_code == 201
    cart = client.get("/api/cart")
    assert cart.status_code == 200
    assert cart.json()["total_item_count"] == 3
    assert len(cart.json()["items"]) == 2
    state = snapshot()
    assert state["stock"][1] == 3
    assert state["stock"][4] == 0
    assert state["items"][0] == (item["id"], 1, 1, 2, "purchase-1")


@pytest.mark.parametrize("sku,quantity,code", [
    (999, 1, "INVALID_SKU"), (0, 1, "INVALID_SKU"),
    (-1, 1, "INVALID_SKU"), (3, 1, "INVALID_SKU"),
    (2, 1, "INSUFFICIENT_STOCK"), (1, 6, "INSUFFICIENT_STOCK"),
    (1, 10**12, "INSUFFICIENT_STOCK"),
])
def test_rejected_purchase_has_no_side_effects(client, catalog, snapshot, sku, quantity, code):
    before = snapshot()
    response = add(client, sku, quantity)
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == code
    if code == "INSUFFICIENT_STOCK":
        assert response.json()["detail"]["available_quantity"] == before["stock"][sku]
    assert snapshot() == before


@pytest.mark.parametrize("body", [
    {}, {"sku_id": 1}, {"quantity": 1},
    {"sku_id": None, "quantity": 1}, {"sku_id": 1, "quantity": None},
    {"sku_id": "invalid", "quantity": 1}, {"sku_id": 1, "quantity": "invalid"},
    {"sku_id": 1.5, "quantity": 1}, {"sku_id": 1, "quantity": 1.5},
    {"sku_id": 1, "quantity": []}, [],
    {"sku_id": 1, "quantity": 0}, {"sku_id": 1, "quantity": -1},
])
def test_invalid_body_returns_422_without_mutation(client, catalog, snapshot, body):
    before = snapshot()
    response = client.post("/api/cart/items", json=body)
    assert response.status_code == 422, response.text
    assert snapshot() == before


@pytest.mark.parametrize("body", ["", "{broken json"])
def test_missing_or_malformed_json(client, catalog, snapshot, body):
    before = snapshot()
    response = client.post("/api/cart/items", content=body,
                           headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert snapshot() == before


def test_exact_stock_then_sold_out(client, catalog, snapshot):
    assert add(client, quantity=5).status_code == 201
    before = snapshot()
    assert before["stock"][1] == 0
    response = add(client)
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INSUFFICIENT_STOCK"
    assert snapshot() == before


def test_sequential_replay_deducts_only_once_even_when_sold_out(client, catalog, snapshot):
    first = add(client, sku=4, key="same-request")
    assert first.status_code == 201
    before = snapshot()
    for _ in range(3):
        retry = add(client, sku=4, key="same-request")
        assert retry.status_code == 201
        assert retry.json() == first.json()
    assert snapshot() == before
    assert len(before["items"]) == 1
    assert before["stock"][4] == 0


@pytest.mark.parametrize("keys", [(None, None), ("", ""), ("request-a", "request-b")])
def test_independent_requests_create_separate_items(client, catalog, snapshot, keys):
    first, second = [add(client, key=key) for key in keys]
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert snapshot()["stock"][1] == 3
    assert len(snapshot()["items"]) == 2


def test_failed_request_does_not_consume_idempotency_key(client, catalog, snapshot):
    assert add(client, quantity=6, key="retry-key").status_code == 400
    assert add(client, quantity=1, key="retry-key").status_code == 201
    assert snapshot()["stock"][1] == 4
    assert len(snapshot()["items"]) == 1
