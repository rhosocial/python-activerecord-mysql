# docs/examples/chapter_12_named_procedure/queries/order_queries.py
"""
MySQL 订单处理相关的命名查询。

这些查询展示如何使用 MySQL 后端实现订单处理工作流中的各个步骤。

``from_`` takes a *row source* over a table, which is two objects rather than
one: :class:`~rhosocial.activerecord.backend.expression.objects.Table` names the
table and :class:`~rhosocial.activerecord.backend.expression.sources.NamedRelationRef`
says the query reads rows from it. The split is what lets a table carry its own
database, so a cross-database query writes ``FROM `other_db`.`orders``` without
any query having to assemble a prefix.
"""
from rhosocial.activerecord.backend.expression import (
    Column,
    Literal,
    QueryExpression,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef


def get_order(dialect, order_id: int):
    """获取订单详情。"""
    return QueryExpression(
        dialect,
        select=[
            Column(dialect, "id"),
            Column(dialect, "status"),
            Column(dialect, "user_id"),
            Column(dialect, "total_amount"),
        ],
        from_=NamedRelationRef(dialect, Table(dialect, "orders")),
        where=Column(dialect, "id") == Literal(dialect, order_id),
    )


def check_inventory(dialect, order_id: int):
    """检查库存可用数量。"""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "available")],
        from_=NamedRelationRef(dialect, Table(dialect, "inventory")),
        where=Column(dialect, "order_id") == Literal(dialect, order_id),
    )


def reserve_inventory(dialect, order_id: int):
    """预留库存。"""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "reserved")],
        from_=NamedRelationRef(dialect, Table(dialect, "inventory")),
        where=Column(dialect, "order_id") == Literal(dialect, order_id),
        dialect_options={"for_update": True},
    )


def send_notification(dialect, user_id: int, type: str):
    """发送通知。"""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "id")],
        from_=NamedRelationRef(dialect, Table(dialect, "notifications")),
        where=Column(dialect, "user_id") == Literal(dialect, user_id),
    )


def process_payment(dialect, order_id: int, amount: float):
    """处理支付。"""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "status"), Column(dialect, "transaction_id")],
        from_=NamedRelationRef(dialect, Table(dialect, "payments")),
        where=Column(dialect, "order_id") == Literal(dialect, order_id),
    )


def release_inventory(dialect, order_id: int):
    """释放库存(回滚)。"""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "id")],
        from_=NamedRelationRef(dialect, Table(dialect, "inventory")),
        where=Column(dialect, "order_id") == Literal(dialect, order_id),
    )


def create_order_record(dialect, order_id: int, user_id: int, amount: float):
    """创建订单记录。"""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "created_at")],
        from_=NamedRelationRef(dialect, Table(dialect, "order_records")),
        where=Column(dialect, "order_id") == Literal(dialect, order_id),
    )


def confirm_inventory(dialect, order_id: int):
    """确认库存(最终确认)。"""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "id")],
        from_=NamedRelationRef(dialect, Table(dialect, "inventory")),
        where=Column(dialect, "order_id") == Literal(dialect, order_id),
    )