from models import db, Shop, ProductMapping, SyncLog
from taobao_api import TaobaoAPI
from datetime import datetime
import traceback


def sync_order(order_tid, shop_id):
    """当店铺shop_id产生订单时，将库存同步到其他所有店铺"""
    source_shop = Shop.query.get(shop_id)
    if not source_shop:
        return

    # 1. 获取订单详情
    api = TaobaoAPI(source_shop.app_key, source_shop.app_secret, source_shop.access_token)
    trade_info = api.get_trade_detail(order_tid)

    if trade_info.get("error_response"):
        _log_error(order_tid, source_shop.name, None, None, 0,
                    f"获取订单失败: {trade_info['error_response']['msg']}")
        return

    orders = trade_info.get("trade", {}).get("orders", [])

    # 2. 对订单中每个商品，根据sku_id或item_id找到内部SKU
    for order_item in orders:
        item_id = str(order_item["num_iid"])
        sku_id = str(order_item.get("sku_id", ""))
        quantity = int(order_item["num"])

        # 查找映射记录（同店铺内匹配）
        mapping = ProductMapping.query.filter_by(
            shop_id=shop_id, item_id=item_id, sku_id=sku_id
        ).first()
        if not mapping:
            continue

        internal_sku = mapping.internal_sku

        # 3. 找出其他所有店铺中相同internal_sku的映射
        other_mappings = ProductMapping.query.filter(
            ProductMapping.internal_sku == internal_sku,
            ProductMapping.shop_id != shop_id
        ).all()

        for target_map in other_mappings:
            target_shop = Shop.query.get(target_map.shop_id)
            if not target_shop.is_active:
                continue
            try:
                target_api = TaobaoAPI(target_shop.app_key, target_shop.app_secret,
                                       target_shop.access_token)
                # 计算新库存（当前库存 - quantity）
                current_stock = target_map.quantity
                new_stock = max(0, current_stock - quantity)

                if target_map.sku_id:
                    resp = target_api.update_sku_stock(target_map.item_id, target_map.sku_id, new_stock)
                else:
                    resp = target_api.update_item_stock(target_map.item_id, new_stock)

                if resp.get("error_response"):
                    _log_error(order_tid, source_shop.name, target_shop.name, internal_sku,
                               quantity, resp['error_response']['msg'])
                else:
                    # 更新本地库存记录
                    target_map.quantity = new_stock
                    target_map.last_sync = datetime.utcnow()
                    db.session.commit()
                    _log_success(order_tid, source_shop.name, target_shop.name, internal_sku, quantity)
            except Exception as e:
                _log_error(order_tid, source_shop.name, target_shop.name, internal_sku,
                           quantity, traceback.format_exc())


def _log_success(order_id, src_shop, tgt_shop, sku, qty):
    log = SyncLog(order_id=order_id, source_shop=src_shop, target_shop=tgt_shop,
                  internal_sku=sku, quantity=qty, status="success")
    db.session.add(log)
    db.session.commit()


def _log_error(order_id, src_shop, tgt_shop, sku, qty, err):
    log = SyncLog(order_id=order_id, source_shop=src_shop, target_shop=tgt_shop,
                  internal_sku=sku, quantity=qty, status="fail", error_msg=err[:500])
    db.session.add(log)
    db.session.commit()
