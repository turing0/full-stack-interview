import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from typing import Optional
from database import get_db
from models import Product, SKU, Cart, CartItem
from schemas import (
    ProductDetailSchema,
    AddCartItemSchema,
    CartResponseSchema,
    CartItemResponseSchema
)


app = FastAPI(title="Variant PDP API", version="1.0.0")


@app.get("/")
async def root():
    return {"status": "OK"}

# GET /api/products 商品列表
@app.get("/api/products", response_model=list[ProductDetailSchema])
def get_products(db: Session = Depends(get_db)):
    return db.query(Product).order_by(Product.id).all()


# GET /api/products/{id}  返回商品、规格及 SKU 数据
@app.get("/api/products/{id}", response_model=ProductDetailSchema)
def get_product_details(id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Product not found", "code": "PRODUCT_NOT_FOUND"}
        )
    return product

# 由于没做身份认证，因此获取first作为返回数据
def get_or_create_default_cart(db: Session) -> Cart:
    cart = db.query(Cart).first()
    if not cart:
        cart = Cart(id=1)
        db.add(cart)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            cart = db.get(Cart, 1)
            if cart is None:
                raise
        db.refresh(cart)
    return cart


# POST /api/cart/items  添加 SKU 到购物车
@app.post("/api/cart/items", response_model=CartItemResponseSchema, status_code=status.HTTP_201_CREATED)
def add_cart_item(
        item_in: AddCartItemSchema,
        idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
        db: Session = Depends(get_db)
):
    cart = get_or_create_default_cart(db)
    cart_id = cart.id
    idempotency_key = idempotency_key or None

    # 幂等性处理
    if idempotency_key:
        existing_item = db.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.idempotency_key == idempotency_key
        ).first()
        if existing_item:
            return existing_item

    # 此处仅校验 SKU，库存由后面的条件 UPDATE 原子校验并扣减。
    sku = db.query(SKU).filter(SKU.id == item_in.sku_id).first()

    # 校验 SKU 是否存在或组合是否可用
    if not sku or not sku.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Selected SKU is invalid, unavailable, or does not exist.", "code": "INVALID_SKU"}
        )

    # 先通过唯一约束占用幂等键，再扣库存；两者在同一事务中提交。
    cart_item = CartItem(
        cart_id=cart_id,
        sku_id=sku.id,
        quantity=item_in.quantity,
        idempotency_key=idempotency_key
    )

    try:
        db.add(cart_item)
        db.flush()
        result = db.execute(
            update(SKU).where(
                SKU.id == item_in.sku_id,
                SKU.is_available.is_(True),
                SKU.available_quantity >= item_in.quantity,
            ).values(available_quantity=SKU.available_quantity - item_in.quantity),
            execution_options={"synchronize_session": False},
        )
        if result.rowcount == 0:
            db.refresh(sku)
            available_quantity = sku.available_quantity
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Insufficient stock for this SKU.",
                        "code": "INSUFFICIENT_STOCK",
                        "available_quantity": available_quantity},
            )
        db.commit()
    except IntegrityError:
        db.rollback()
        if idempotency_key:
            existing_item = db.query(CartItem).filter(
                CartItem.cart_id == cart_id,
                CartItem.idempotency_key == idempotency_key,
            ).first()
            if existing_item is not None:
                return existing_item
        raise
    db.refresh(cart_item)

    return cart_item

# GET /api/cart  返回当前购物车及总商品数量
@app.get("/api/cart", response_model=CartResponseSchema)
def get_cart(db: Session = Depends(get_db)):
    cart = get_or_create_default_cart(db)

    # 计算购物车中所有商品的条目总数
    total_item_count = sum(item.quantity for item in cart.items)

    return {
        "id": cart.id,
        "items": cart.items,
        "total_item_count": total_item_count
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )

