from sqlalchemy.orm import Session
from app.repositories.models import ProductDB

class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, product_data: dict) -> ProductDB:
        db_product = ProductDB(**product_data)
        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)
        return db_product

    def get_by_id(self, product_id: int) -> ProductDB | None:
        return self.db.query(ProductDB).filter(ProductDB.id == product_id).first()

    def get_all(self, needs_review: bool | None = None) -> list[ProductDB]:
        query = self.db.query(ProductDB)
        if needs_review is not None:
            query = query.filter(ProductDB.needs_review == needs_review)
        return query.all()