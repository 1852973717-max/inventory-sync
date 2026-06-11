from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Shop(db.Model):
    __tablename__ = 'shops'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    app_key = db.Column(db.String(64), nullable=False)
    app_secret = db.Column(db.String(64), nullable=False)
    access_token = db.Column(db.String(200))
    refresh_token = db.Column(db.String(200))
    token_expire = db.Column(db.DateTime)
    seller_nick = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)


class ProductMapping(db.Model):
    __tablename__ = 'product_mappings'

    id = db.Column(db.Integer, primary_key=True)
    internal_sku = db.Column(db.String(100), nullable=False)  # 内部统一SKU码
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'))
    item_id = db.Column(db.String(50), nullable=False)  # 淘宝商品ID
    sku_id = db.Column(db.String(50))  # SKU ID，可为空
    quantity = db.Column(db.Integer, default=0)  # 本店库存（只做展示）
    last_sync = db.Column(db.DateTime)


class SyncLog(db.Model):
    __tablename__ = 'sync_logs'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50))
    source_shop = db.Column(db.String(50))
    target_shop = db.Column(db.String(50))
    internal_sku = db.Column(db.String(100))
    quantity = db.Column(db.Integer)
    status = db.Column(db.String(20))  # success / fail
    error_msg = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
