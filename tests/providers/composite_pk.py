# tests/providers/composite_pk.py
import os
from typing import Type, List

from rhosocial.activerecord.model import ActiveRecord

from rhosocial.activerecord.testsuite.feature.composite_pk.fixtures.models import (
    OrderItem as OrderItemBase,
    StoreInventory as StoreInventoryBase,
    Order as OrderBase,
    MappedOrderItem as MappedOrderItemBase,
)
from rhosocial.activerecord.testsuite.feature.composite_pk.fixtures.models import (
    AsyncOrderItem as AsyncOrderItemBase,
    AsyncStoreInventory as AsyncStoreInventoryBase,
    AsyncOrder as AsyncOrderBase,
    AsyncMappedOrderItem as AsyncMappedOrderItemBase,
)

from .scenarios import get_enabled_scenarios, get_scenario


class CompositePKProvider:
    def __init__(self):
        self._active_backends = []
        self._active_async_backends = []

    def get_test_scenarios(self) -> List[str]:
        return list(get_enabled_scenarios().keys())

    def _setup_model(self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str) -> Type[ActiveRecord]:
        backend_class, config = get_scenario(scenario_name)
        model_class.configure(config, backend_class)
        backend_instance = model_class.__backend__
        if backend_instance not in self._active_backends:
            self._active_backends.append(backend_instance)
        try:
            backend_instance.execute("SET FOREIGN_KEY_CHECKS = 0")
            backend_instance.execute(f"DROP TABLE IF EXISTS `{table_name}`")
            backend_instance.execute("SET FOREIGN_KEY_CHECKS = 1")
        except Exception:
            try:
                backend_instance.execute("SET FOREIGN_KEY_CHECKS = 1")
            except Exception:
                pass
        schema_sql = self._load_mysql_schema(f"{table_name}.sql")
        backend_instance.execute(schema_sql)
        return model_class

    async def _setup_async_model(self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str) -> Type[ActiveRecord]:
        from rhosocial.activerecord.backend.impl.mysql import AsyncMySQLBackend
        _, config = get_scenario(scenario_name)
        await model_class.configure(config, AsyncMySQLBackend)
        backend_instance = model_class.__backend__
        if backend_instance not in self._active_async_backends:
            self._active_async_backends.append(backend_instance)
        try:
            await backend_instance.execute("SET FOREIGN_KEY_CHECKS = 0")
            await backend_instance.execute(f"DROP TABLE IF EXISTS `{table_name}`")
            await backend_instance.execute("SET FOREIGN_KEY_CHECKS = 1")
        except Exception:
            try:
                await backend_instance.execute("SET FOREIGN_KEY_CHECKS = 1")
            except Exception:
                pass
        schema_sql = self._load_mysql_schema(f"{table_name}.sql")
        await backend_instance.execute(schema_sql)
        return model_class

    def _load_mysql_schema(self, filename: str) -> str:
        schema_dir = os.path.join(
            os.path.dirname(__file__),
            "..",
            "rhosocial",
            "activerecord_mysql_test",
            "feature",
            "composite_pk",
            "schema",
        )
        schema_path = os.path.join(schema_dir, filename)
        with open(schema_path, "r", encoding="utf-8") as f:
            return f.read()

    def setup_order_item_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup_model(OrderItemBase, scenario_name, "order_items")

    def setup_store_inventory_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup_model(StoreInventoryBase, scenario_name, "store_inventory")

    def setup_order_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup_model(OrderBase, scenario_name, "orders")

    async def setup_async_order_item_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return await self._setup_async_model(AsyncOrderItemBase, scenario_name, "order_items")

    async def setup_async_store_inventory_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return await self._setup_async_model(AsyncStoreInventoryBase, scenario_name, "store_inventory")

    async def setup_async_order_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return await self._setup_async_model(AsyncOrderBase, scenario_name, "orders")

    def setup_mapped_order_item_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup_model(MappedOrderItemBase, scenario_name, "order_items")

    async def setup_async_mapped_order_item_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return await self._setup_async_model(AsyncMappedOrderItemBase, scenario_name, "order_items")

    def _drop_tables(self, backend, tables):
        try:
            backend.execute("SET FOREIGN_KEY_CHECKS = 0")
            for t in tables:
                try:
                    backend.execute(f"DROP TABLE IF EXISTS `{t}`")
                except Exception:
                    pass
            backend.execute("SET FOREIGN_KEY_CHECKS = 1")
        except Exception:
            try:
                backend.execute("SET FOREIGN_KEY_CHECKS = 1")
            except Exception:
                pass

    def cleanup_after_test(self, scenario_name: str):
        tables = ["order_items", "store_inventory", "orders"]
        for backend in self._active_backends:
            self._drop_tables(backend, tables)
            try:
                backend.disconnect()
            except Exception:
                pass
        self._active_backends.clear()

    async def cleanup_after_test_async(self, scenario_name: str):
        tables = ["order_items", "store_inventory", "orders"]
        for backend in self._active_async_backends:
            try:
                await backend.execute("SET FOREIGN_KEY_CHECKS = 0")
                for t in tables:
                    try:
                        await backend.execute(f"DROP TABLE IF EXISTS `{t}`")
                    except Exception:
                        pass
                await backend.execute("SET FOREIGN_KEY_CHECKS = 1")
            except Exception:
                try:
                    await backend.execute("SET FOREIGN_KEY_CHECKS = 1")
                except Exception:
                    pass
            try:
                await backend.disconnect()
            except Exception:
                pass
        self._active_async_backends.clear()
