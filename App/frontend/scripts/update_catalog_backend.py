from pathlib import Path

root = Path(__file__).resolve().parents[2]
main_path = root / 'main.py'
model_path = root / 'models.py'
main = main_path.read_text(encoding='utf-8')
models = model_path.read_text(encoding='utf-8')
anchor = '# GET /api/products/{id}'
endpoint = '''# GET /api/products returns the catalog using the same detail schema.
@app.get("/api/products", response_model=list[ProductDetailSchema])
def get_products(db: Session = Depends(get_db)):
    return db.query(Product).order_by(Product.id).all()


'''
if '@app.get("/api/products",' not in main:
    if anchor not in main:
        raise RuntimeError('Product route anchor changed; refusing to overwrite.')
    main = main.replace(anchor, endpoint + anchor, 1)
anchor = '    cart_items = relationship("CartItem", back_populates="sku")'
if 'def option_value_ids(' not in models:
    if anchor not in models:
        raise RuntimeError('SKU model anchor changed; refusing to overwrite.')
    models = models.replace(anchor, anchor + '''

    @property
    def option_value_ids(self):
        return [value.id for value in self.option_values]
''', 1)
main_path.write_text(main, encoding='utf-8')
model_path.write_text(models, encoding='utf-8')
print('Added catalog endpoint and SKU option ID serialization.')
