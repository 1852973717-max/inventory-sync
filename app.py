from flask import Flask, render_template, request, redirect, url_for, jsonify
from models import db, Shop, ProductMapping, SyncLog
from sync_service import sync_order
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///inventory.db')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
db.init_app(app)

with app.app_context():
    db.create_all()


# ---------- 页面路由 ----------

@app.route('/')
def index():
    shops = Shop.query.all()
    mappings = ProductMapping.query.all()
    return render_template('index.html', shops=shops, mappings=mappings)


@app.route('/shops')
def shops():
    shops = Shop.query.all()
    return render_template('shops.html', shops=shops)


@app.route('/shop/add', methods=['POST'])
def add_shop():
    shop = Shop(
        name=request.form['name'],
        app_key=request.form['app_key'],
        app_secret=request.form['app_secret'],
        access_token=request.form['access_token'],
        refresh_token=request.form['refresh_token'],
        seller_nick=request.form.get('seller_nick')
    )
    db.session.add(shop)
    db.session.commit()
    return redirect(url_for('shops'))


@app.route('/shop/delete/<int:id>')
def delete_shop(id):
    Shop.query.filter_by(id=id).delete()
    db.session.commit()
    return redirect(url_for('shops'))


@app.route('/mappings')
def mappings():
    mapping_list = db.session.query(ProductMapping, Shop.name.label('shop_name')).join(Shop).all()
    shops = Shop.query.all()
    return render_template('mappings.html', mappings=mapping_list, shops=shops)


@app.route('/mapping/add', methods=['POST'])
def add_mapping():
    mapping = ProductMapping(
        internal_sku=request.form['internal_sku'],
        shop_id=int(request.form['shop_id']),
        item_id=request.form['item_id'],
        sku_id=request.form.get('sku_id') or None,
        quantity=int(request.form['quantity'])
    )
    db.session.add(mapping)
    db.session.commit()
    return redirect(url_for('mappings'))


@app.route('/logs')
def logs():
    logs = SyncLog.query.order_by(SyncLog.created_at.desc()).limit(100).all()
    return render_template('logs.html', logs=logs)


# ---------- 淘宝订单推送接收 ----------

@app.route('/taobao/webhook', methods=['POST'])
def order_push():
    """淘宝订单消息推送接收地址"""
    data = request.form.to_dict()  # 淘宝推送为form格式

    # 解析消息类型（需按淘宝消息协议验证签名，为简化只取订单号）
    tid = data.get('tid') or data.get('order_id')
    if not tid:
        return "no tid", 400

    # 根据推送内容确定是哪个店铺触发的，一般推送中会带seller_nick
    seller_nick = data.get('seller_nick')
    shop = Shop.query.filter_by(seller_nick=seller_nick).first()
    if not shop:
        return "shop not found", 400

    # 异步处理同步（避免阻塞淘宝重推）
    from threading import Thread
    Thread(target=sync_order, args=(tid, shop.id)).start()
    return "success", 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
