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

    def get_by_id(self, product_id: int):
        return self.db.query(ProductDB).filter(ProductDB.id == product_id).first()

    def get_all(self, needs_review: bool = None, include_competitors: bool = False):
        query = self.db.query(ProductDB)
        if not include_competitors:
            query = query.filter(ProductDB.is_competitor == False)
        if needs_review is not None:
            query = query.filter(ProductDB.needs_review == needs_review)
        return query.all()