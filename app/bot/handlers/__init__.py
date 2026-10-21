from aiogram import Router

from app.bot.handlers import delete_order, edit_order, errors, fallback, menu, my_orders, new_order, owner


def build_router() -> Router:
    root = Router(name="root")
    root.include_routers(
        errors.router,
        menu.router,
        owner.router,
        new_order.router,
        edit_order.router,
        delete_order.router,
        my_orders.router,
        fallback.router,
    )
    return root
