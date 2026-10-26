"""Real HTTP/ASGI requests, independent sessions, no mocked stock operations."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from main import app
from models import SKU


def simultaneous_adds(db_factory, sku_id, keys):
    # Synchronize after ORM has materialized the stock in both request sessions.
    # This reliably exercises SQLite's lost-update window without timing sleeps.
    # Precreated carts isolate the stock/idempotency races from cart creation.
    barrier = Barrier(2, timeout=10)
    lock = Lock()
    seen_sessions = set()

    def after_load(session, instance):
        if not isinstance(instance, SKU) or instance.id != sku_id:
            return
        with lock:
            if session in seen_sessions:
                return
            seen_sessions.add(session)
        barrier.wait()

    def send(key):
        with TestClient(app, raise_server_exceptions=False) as client:
            return client.post(
                "/api/cart/items",
                json={"sku_id": sku_id, "quantity": 1},
                headers={"Idempotency-Key": key},
            )

    event.listen(db_factory.class_, "loaded_as_persistent", after_load)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(send, key) for key in keys]
            responses = [future.result(timeout=20) for future in futures]
        assert len(seen_sessions) == 2, "Requests must use distinct DB sessions"
        return responses
    finally:
        event.remove(db_factory.class_, "loaded_as_persistent", after_load)


@pytest.mark.concurrency
@pytest.mark.parametrize("attempt", range(3))
def test_stock_race_only_one_buyer_gets_last_unit(db_factory, catalog, snapshot, attempt):
    responses = simultaneous_adds(db_factory, 4, ["buyer-a", "buyer-b"])
    state = snapshot()
    statuses = sorted(response.status_code for response in responses)
    assert statuses == [201, 400], f"statuses={statuses}, persisted={state}"
    loser = next(response for response in responses if response.status_code == 400)
    assert loser.json()["detail"]["code"] == "INSUFFICIENT_STOCK"
    assert loser.json()["detail"]["available_quantity"] == 0
    assert state["stock"][4] == 0
    assert len(state["items"]) == 1
    assert sum(item[3] for item in state["items"]) == 1


@pytest.mark.concurrency
@pytest.mark.parametrize("sku_id,remaining", [(1, 4), (4, 0)])
def test_concurrent_idempotency_key_creates_one_item(db_factory, catalog, snapshot, sku_id, remaining):
    responses = simultaneous_adds(db_factory, sku_id, ["same-key", "same-key"])
    assert [response.status_code for response in responses] == [201, 201]
    state = snapshot()
    ids = [response.json()["id"] for response in responses]
    assert ids[0] == ids[1], f"item IDs={ids}, persisted={state}"
    assert state["stock"][sku_id] == remaining
    assert len(state["items"]) == 1


@pytest.mark.concurrency
def test_concurrent_distinct_requests_preserve_stock_accounting(db_factory, catalog, snapshot):
    responses = simultaneous_adds(db_factory, 1, ["request-a", "request-b"])
    assert [response.status_code for response in responses] == [201, 201]
    state = snapshot()
    purchased = sum(item[3] for item in state["items"])
    assert purchased == 2
    assert state["stock"][1] + purchased == 5, f"Lost stock update: {state}"
