"""API fixtures: every test gets a separate on-disk SQLite database."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Allow pytest discovery from either the project root or backend directory.
APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from main import app, get_db
from models import Base, Cart, CartItem, OptionDimension, OptionValue, Product, SKU


@pytest.fixture
def db_factory(tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'api-test.db').as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)

    def override_db():
        with factory() as session:
            yield session

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_db
    try:
        yield factory
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        engine.dispose()


@pytest.fixture
def client(db_factory):
    with TestClient(app) as client:
        yield client


@pytest.fixture
def catalog(db_factory):
    with db_factory() as db:
        product = Product(id=1, title="测试商品", description="API fixture")
        dimension = OptionDimension(id=1, name="颜色", product=product)
        value = OptionValue(id=1, value="红色", dimension=dimension)
        db.add_all([
            product,
            Product(id=2, title="无规格商品"),
            SKU(id=1, product=product, price=19.9, available_quantity=5,
                is_available=True, option_values=[value]),
            SKU(id=2, product=product, price=29.9, available_quantity=0,
                is_available=True),
            SKU(id=3, product=product, price=39.9, available_quantity=5,
                is_available=False),
            SKU(id=4, product=product, price=49.9, available_quantity=1,
                is_available=True),
            Cart(id=1),
        ])
        db.commit()


@pytest.fixture
def snapshot(db_factory):
    """Read persisted state with a fresh session, never the request's identity map."""
    def read():
        with db_factory() as db:
            return {
                "stock": {sku.id: sku.available_quantity for sku in db.query(SKU)},
                "items": [
                    (item.id, item.cart_id, item.sku_id, item.quantity, item.idempotency_key)
                    for item in db.query(CartItem).order_by(CartItem.id)
                ],
            }
    return read
