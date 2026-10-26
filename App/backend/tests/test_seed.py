"""AI-generated regression test for seed data and fresh database constraints."""
import pytest
from sqlalchemy.exc import IntegrityError

from models import Cart, CartItem, SKU
from seed import seed_data


def test_seed_is_repeatable_and_creates_idempotency_constraint(db_factory):
    with db_factory.begin() as db:
        seed_data(db)
    with db_factory.begin() as db:
        counts = seed_data(db)
        assert all(count == 0 for count in counts.values())
        assert db.query(Cart).count() == 1
        assert db.query(SKU).count() == 8
        cart_id = db.query(Cart).one().id
        sku_id = db.query(SKU).first().id
        db.add(CartItem(cart_id=cart_id, sku_id=sku_id, quantity=1, idempotency_key="seed-check"))
    with pytest.raises(IntegrityError):
        with db_factory.begin() as db:
            db.add(CartItem(cart_id=cart_id, sku_id=sku_id, quantity=1, idempotency_key="seed-check"))
