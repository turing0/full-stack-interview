from sqlalchemy.orm import relationship

from database import Base
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Table, Boolean, UniqueConstraint


# SKU 与 规格值（OptionValue）的多对多关联表
sku_option_values = Table(
    'sku_option_values',
    Base.metadata,
    Column('sku_id', Integer, ForeignKey('skus.id'), primary_key=True),
    Column('option_value_id', Integer, ForeignKey('option_values.id'), primary_key=True)
)

class Product(Base):
    '''商品表'''
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    image = Column(String, nullable=True)

    # 关系映射
    dimensions = relationship("OptionDimension", back_populates="product", cascade="all, delete-orphan")
    skus = relationship("SKU", back_populates="product", cascade="all, delete-orphan")


class OptionDimension(Base):
    """规格维度表 (如: 颜色, 尺码)"""
    __tablename__ = 'option_dimensions'

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    name = Column(String, nullable=False)  # 规格维度名称，例如：颜色、尺寸

    product = relationship("Product", back_populates="dimensions")
    values = relationship("OptionValue", back_populates="dimension", cascade="all, delete-orphan")


class OptionValue(Base):
    """规格值表"""
    __tablename__ = 'option_values'

    id = Column(Integer, primary_key=True, index=True)
    dimension_id = Column(Integer, ForeignKey('option_dimensions.id'), nullable=False)
    value = Column(String, nullable=False)  # 规格具体值，例如：红色、白色、S、M

    dimension = relationship("OptionDimension", back_populates="values")

class SKU(Base):
    """库存单位表 (SKU)"""
    __tablename__ = 'skus'

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    price = Column(Float, nullable=False)  # SKU 价格
    available_quantity = Column(Integer, nullable=False, default=0)  # 可用库存
    image = Column(String, nullable=True)  # SKU 专属图片
    is_available = Column(Boolean, default=True)  # 是否可用

    product = relationship("Product", back_populates="skus")
    option_values = relationship("OptionValue", secondary=sku_option_values)
    cart_items = relationship("CartItem", back_populates="sku")

    @property
    def option_value_ids(self):
        return [value.id for value in self.option_values]


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    items = relationship('CartItem', back_populates="cart", cascade="all, delete-orphan")

class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "idempotency_key", name="uq_cart_item_idempotency"),
    )

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey('carts.id'), nullable=False)
    sku_id = Column(Integer, ForeignKey('skus.id'), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    idempotency_key = Column(String, index=True, nullable=True)  # 幂等键，防止重复提交

    cart = relationship("Cart", back_populates="items")
    sku = relationship("SKU", back_populates="cart_items")
