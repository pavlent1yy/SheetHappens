from html import escape
from typing import Any

from app import config, texts


def summary(data: dict[str, Any]) -> str:
    return texts.SUMMARY.format(
        type=escape(data.get("type", "")),
        subtype=escape(data.get("subtype", "")),
        weight=escape(data.get("weight", "")),
        price=escape(data.get("price", "")),
        src=escape(data.get("src", "")),
        dst=escape(data.get("dst", "")),
        comment=escape(data.get("comment") or texts.EMPTY),
        photo=texts.PHOTO_YES if data.get("photo") else texts.EMPTY,
    )


def order_summary(order: dict[str, str]) -> str:
    return summary({
        "type": order.get(config.COL_TYPE, ""),
        "subtype": order.get(config.COL_SUBTYPE, ""),
        "weight": order.get(config.COL_WEIGHT, ""),
        "price": order.get(config.COL_PRICE, ""),
        "src": order.get(config.COL_FROM, ""),
        "dst": order.get(config.COL_TO, ""),
        "comment": order.get(config.COL_COMMENT, ""),
        "photo": order.get(config.COL_PHOTO, ""),
    })
