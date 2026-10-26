"""
此文件由ai生成
prompt：根据题目描述以及我给出的数据库样式生成符合的初始数据，使用py脚本，重复执行不会重复插入
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session, selectinload

from database import Base, SessionLocal, engine
from models import Cart, OptionDimension, OptionValue, Product, SKU

PRODUCT_TITLE = "Everyday Cotton Tee"
PRODUCT_DESCRIPTION = (
    "A soft, breathable everyday T-shirt with three colours and three sizes. "
    "Select a colour and size to see the exact price, photo and stock."
)
COLORS = ("Black", "White", "Blue")
SIZES = ("S", "M", "L")

# (colour, size, price in CNY, available quantity)
# Blue / L is deliberately missing: an impossible combination.
# Black / M exists, but is out of stock.
# White / S has one item, for the last-unit concurrency test.
SKU_SEEDS = (
    ("Black", "S", 129.0, 12),
    ("Black", "M", 129.0, 0),
    ("Black", "L", 139.0, 5),
    ("White", "S", 129.0, 1),
    ("White", "M", 129.0, 8),
    ("White", "L", 139.0, 3),
    ("Blue",  "S", 135.0, 6),
    ("Blue",  "M", 135.0, 2),
)

BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "static" / "products"
IMAGE_BASE_URL = "/static/products"

COLOUR_HEX = {
    "Black": "#30333B",
    "White": "#F6F5F1",
    "Blue": "#4876A4",
}


def image_name(colour: str, size: str) -> str:
    return f"tee-{colour.lower()}-{size.lower()}.svg"


def image_url(colour: str, size: str) -> str:
    return f"{IMAGE_BASE_URL}/{image_name(colour, size)}"


def create_demo_images(directory: Path = IMAGE_DIR) -> int:
    """Create local demo images once; never overwrite an existing image."""
    directory.mkdir(parents=True, exist_ok=True)
    created = 0
    for colour, size, _price, _stock in SKU_SEEDS:
        path = directory / image_name(colour, size)
        shirt = COLOUR_HEX[colour]
        # All values are fixed seed constants, not user-controlled input.
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 800" role="img" aria-label="{escape(colour)} cotton T-shirt size {escape(size)}">
<rect width="640" height="800" fill="#F0F2F5"/>
<rect x="35" y="35" width="570" height="730" rx="30" fill="#E6EAF0"/>
<path d="M230 156 274 135 Q320 170 366 135 L410 156 505 232 454 322 411 294 411 605 229 605 229 294 186 322 135 232Z" fill="{shirt}" stroke="#9EA7B3" stroke-width="4" stroke-linejoin="round"/>
<path d="M274 136 Q320 208 366 136" fill="none" stroke="#9EA7B3" stroke-width="4"/>
<text x="320" y="686" font-family="sans-serif" font-size="28" font-weight="bold" text-anchor="middle" fill="#263447">EVERYDAY COTTON TEE</text>
<text x="320" y="728" font-family="sans-serif" font-size="24" text-anchor="middle" fill="#526275">{escape(colour)} / {escape(size)}</text>
</svg>'''
        try:
            with path.open("x", encoding="utf-8") as output:
                output.write(svg)
            created += 1
        except FileExistsError:
            pass
    return created


def unique_or_none(rows: list, description: str):
    """Fail safely when existing data is ambiguous instead of picking a random row."""
    if len(rows) > 1:
        raise ValueError(
            f"Found duplicate {description} in database. "
            "Resolve them manually; seeding will not guess which one to use."
        )
    return rows[0] if rows else None


def seed_data(db: Session) -> dict[str, int]:
    """Seed using an existing SQLAlchemy session; caller manages the transaction.

    Lookup keys are the stable product title, dimension names, option values and
    *sets of option-value IDs* for a SKU. These match the provided ORM model,
    which has integer SKU IDs and no standalone SKU code.
    """
    counts = {"products": 0, "dimensions": 0, "values": 0, "skus": 0, "carts": 0}

    product = unique_or_none(
        db.query(Product).filter(Product.title == PRODUCT_TITLE).all(),
        f"product titled {PRODUCT_TITLE!r}",
    )
    if product is None:
        product = Product(
            title=PRODUCT_TITLE,
            description=PRODUCT_DESCRIPTION,
            image=image_url("Black", "S"),
        )
        db.add(product)
        db.flush()
        counts["products"] += 1

    dimension_map: dict[str, OptionDimension] = {}
    option_map: dict[tuple[str, str], OptionValue] = {}

    for dimension_name, values in (("Color", COLORS), ("Size", SIZES)):
        dimension = unique_or_none(
            db.query(OptionDimension).filter(
                OptionDimension.product_id == product.id,
                OptionDimension.name == dimension_name,
            ).all(),
            f"dimension {dimension_name!r} of product {product.id}",
        )
        if dimension is None:
            dimension = OptionDimension(product_id=product.id, name=dimension_name)
            db.add(dimension)
            db.flush()
            counts["dimensions"] += 1
        dimension_map[dimension_name] = dimension

        for value_text in values:
            option = unique_or_none(
                db.query(OptionValue).filter(
                    OptionValue.dimension_id == dimension.id,
                    OptionValue.value == value_text,
                ).all(),
                f"value {value_text!r} of dimension {dimension.id}",
            )
            if option is None:
                option = OptionValue(dimension_id=dimension.id, value=value_text)
                db.add(option)
                db.flush()
                counts["values"] += 1
            option_map[(dimension_name, value_text)] = option

    # Build the key from *both* associated option values, not SKU.id (auto-increment).
    existing: dict[frozenset[int], SKU] = {}
    for sku in (
        db.query(SKU)
        .options(selectinload(SKU.option_values))
        .filter(SKU.product_id == product.id)
        .all()
    ):
        key = frozenset(option.id for option in sku.option_values)
        if key in existing:
            raise ValueError(f"Duplicate SKU option combination for product {product.id}")
        existing[key] = sku

    for colour, size, price, quantity in SKU_SEEDS:
        chosen = [option_map[("Color", colour)], option_map[("Size", size)]]
        key = frozenset(option.id for option in chosen)
        if key in existing:
            # Intentionally never reset an existing SKU's stock, price or image.
            continue
        sku = SKU(
            product_id=product.id,
            price=price,
            available_quantity=quantity,
            image=image_url(colour, size),
            is_available=True,
            option_values=chosen,
        )
        db.add(sku)
        existing[key] = sku
        counts["skus"] += 1

    # This exercise has no authentication: provide an initially empty demo cart.
    # If any cart exists already, preserve it and never create another demo cart.
    if db.query(Cart.id).first() is None:
        db.add(Cart())
        counts["carts"] += 1

    return counts


def main() -> None:
    # create_all creates missing tables only; it never drops or recreates a table.
    Base.metadata.create_all(bind=engine)
    new_images = create_demo_images()

    # One transaction: an exception rolls back all new rows.
    with SessionLocal.begin() as db:
        # Take SQLite's write lock before any SELECT. This also serialises
        # overlapping seed.py processes, despite absent ORM unique constraints.
        if db.bind.dialect.name == "sqlite":
            db.execute(text("BEGIN IMMEDIATE"))
        inserted = seed_data(db)

    db_path = Path(engine.url.database or "data.db").resolve()
    print(f"Database: {db_path}")
    print("New rows: " + ", ".join(f"{key}={value}" for key, value in inserted.items()))
    print(f"New demo images: {new_images}")
    print("Product: Everyday Cotton Tee; 2 dimensions; 8 SKUs")
    print("Unavailable combination: Blue / L; sold out: Black / M; last item: White / S")


if __name__ == "__main__":
    main()
