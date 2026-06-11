import time
import requests
import json
import hashlib
from datetime import datetime, timedelta


class TaobaoAPI:
    def __init__(self, app_key, app_secret, access_token):
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = access_token
        self.gateway = "https://eco.taobao.com/router/rest"

    def _request(self, method, params):
        params.update({
            "method": method,
            "app_key": self.app_key,
            "session": self.access_token,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "format": "json",
            "v": "2.0",
            "sign_method": "md5"
        })
        # 签名（简化，实际应使用官方SDK）
        params["sign"] = self._gen_sign(params)
        resp = requests.post(self.gateway, data=params)
        return resp.json()

    def _gen_sign(self, params):
        sorted_keys = sorted(params.keys())
        sign_str = self.app_secret + ''.join(f"{k}{params[k]}" for k in sorted_keys) + self.app_secret
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()

    def get_trade_detail(self, tid):
        """获取订单详情"""
        params = {
            "fields": "tid,status,orders.oid,orders.num,orders.sku_id,orders.num_iid",
            "tid": tid
        }
        return self._request("taobao.trade.fullinfo.get", params)

    def update_sku_stock(self, item_id, sku_id, quantity):
        """更新SKU库存（淘宝API需要quantity为增量或绝对值，这里使用绝对值）"""
        params = {
            "num_iid": item_id,
            "sku_id": sku_id,
            "quantity": quantity,
            "type": "full"  # 全量更新库存
        }
        return self._request("taobao.item.sku.update", params)

    def update_item_stock(self, item_id, quantity):
        """无SKU时更新商品库存"""
        params = {
            "num_iid": item_id,
            "quantity": quantity,
            "type": "full"
        }
        return self._request("taobao.item.quantity.update", params)

    @staticmethod
    def refresh_token(app_key, app_secret, refresh_token):
        """刷新access_token（简化版，实际使用refresh_token接口）"""
        url = "https://oauth.taobao.com/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": app_key,
            "client_secret": app_secret
        }
        resp = requests.post(url, data=data)
        return resp.json()
