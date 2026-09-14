# 格式化函数签名规范化改造计划

> 目标：所有 `format_*` 格式化函数统一为 `(self, expr: SomeExpression) -> Tuple[str, tuple]`，消除 isinstance 判断，补齐类型提示。
> 依赖：核心库 `python-activerecord` 先完成 `StorageOptionsExpression` 等新表达式类的创建。

## 一、返回类型不是 Tuple[str, tuple] 的方法

### 1.1 返回 `str` 的方法

| 方法 | 文件 | 当前签名 | 改造方案 |
|------|------|---------|---------|
| `format_storage_options` | `mixins/table.py:179` | `(self, storage_options: Dict[str, Any]) -> str` | 改为接收 expr，返回 `Tuple[str, tuple]` |
| `format_duality_object_select` | `mixins/json_duality_view.py` | `(self, spec) -> str` | 改为接收 expr，返回 `Tuple[str, tuple]` |
| `format_duality_object_body` | `mixins/json_duality_view.py` | `(self, spec) -> str` | 同上 |
| `format_nested_duality` | `mixins/json_duality_view.py` | `(self, nested) -> str` | 同上 |

### 1.2 返回类型大小写

所有 `-> Tuple[str, Tuple]` 统一改为 `-> Tuple[str, tuple]`。

## 二、参数不是 expr 的方法

### 2.1 `format_storage_options`

- **当前**: `(self, storage_options: Dict[str, Any]) -> str`
- **改造**: 接收 `expr: "StorageOptionsExpression"`（依赖核心库创建），从 `expr.options` 取值，返回 `Tuple[str, tuple]`。去掉 isinstance，值统一用 `inline_sql_literal` 渲染

### 2.2 JSON Duality 辅助方法

- `format_duality_object_select(self, spec)` → `(self, expr: "DualityObjectSelectExpression")`
- `format_duality_object_body(self, spec)` → `(self, expr: "DualityObjectBodyExpression")`
- `format_nested_duality(self, nested)` → `(self, expr: "NestedDualityExpression")`

## 三、参数缺少类型提示的方法

### 3.1 `mixins/spatial.py` — 全部 9 个方法

| 方法 | 补齐为 |
|------|--------|
| `format_spatial_literal` | `(self, expr: "SpatialLiteralExpression")` |
| `format_st_geom_from_text` | `(self, expr: "STGeomFromTextExpression")` |
| `format_st_geom_from_wkb` | `(self, expr: "STGeomFromWKBExpression")` |
| `format_st_as_text` | `(self, expr: "STAsTextExpression")` |
| `format_st_as_geojson` | `(self, expr: "STAsGeoJSONExpression")` |
| `format_st_distance` | `(self, expr: "STDistanceExpression")` |
| `format_st_within` | `(self, expr: "STWithinExpression")` |
| `format_st_contains` | `(self, expr: "STContainsExpression")` |
| `format_create_spatial_index` | `(self, expr: "CreateSpatialIndexExpression")` |

### 3.2 `mixins/json.py` — 大部分方法

| 方法 | 补齐为 |
|------|--------|
| `format_json_extract` | `(self, expr: "JSONExtractExpression")` |
| `format_json_unquote` | `(self, expr: "JSONUnquoteExpression")` |
| `format_json_object` | `(self, expr: "JSONObjectExpression")` |
| `format_json_array` | `(self, expr: "JSONArrayExpression")` |
| `format_json_contains` | `(self, expr: "JSONContainsExpression")` |
| `format_json_set` | `(self, expr: "JSONSetExpression")` |
| `format_json_remove` | `(self, expr: "JSONRemoveExpression")` |
| `format_json_type` | `(self, expr: "JSONTypeExpression")` |
| `format_json_valid` | `(self, expr: "JSONValidExpression")` |
| `format_json_search` | `(self, expr: "JSONSearchExpression")` |
| `format_json_table_expression` | `(self, expr: "JSONTableExpression")` |

### 3.3 `mixins/set_type.py` — 全部 3 个方法

| 方法 | 补齐为 |
|------|--------|
| `format_set_literal` | `(self, expr: "SetLiteralExpression")` |
| `format_find_in_set` | `(self, expr: "FindInSetExpression")` |
| `format_set_contains` | `(self, expr: "SetContainsExpression")` |

### 3.4 `mixins/ddl_column.py` — 全部 5 个方法

| 方法 | 补齐为 |
|------|--------|
| `format_column` | `(self, expr: "ColumnDefinition")` |
| `format_add_column_action` | `(self, action: "AddColumn")` |
| `format_drop_column_action` | `(self, action: "DropColumn")` |
| `format_drop_table_constraint_action` | `(self, action: "DropTableConstraint")` |
| `format_alter_column_action` | `(self, action: "AlterColumn")` |

### 3.5 `mixins/vector.py` — 全部 8 个方法

| 方法 | 补齐为 |
|------|--------|
| `format_vector_literal` | `(self, expr: "VectorLiteralExpression")` |
| `format_string_to_vector` | `(self, expr: "StringToVectorExpression")` |
| `format_vector_to_string` | `(self, expr: "VectorToStringExpression")` |
| `format_vector_dim` | `(self, expr: "VectorDimExpression")` |
| `format_distance_euclidean` | `(self, expr: "DistanceEuclideanExpression")` |
| `format_distance_cosine` | `(self, expr: "DistanceCosineExpression")` |
| `format_distance_dot` | `(self, expr: "DistanceDotExpression")` |
| `format_create_vector_index` | `(self, expr: "CreateVectorIndexExpression")` |

### 3.6 `mixins/datetime.py` — 5 个方法使用 `Any`

| 方法 | 补齐为 |
|------|--------|
| `format_date_trunc_expression` | `(self, expr: "DateTruncExpression")` |
| `format_interval_expression` | `(self, expr: "IntervalExpression")` |
| `format_datetime_add_expression` | `(self, expr: "DatetimeAddExpression")` |
| `format_datetime_subtract_expression` | `(self, expr: "DatetimeSubtractExpression")` |
| `format_datetime_diff_expression` | `(self, expr: "DatetimeDiffExpression")` |

## 四、消除 isinstance 判断

### 4.1 `format_insert_statement` — 数据源分发

- **保留**。`DefaultValuesSource`/`ValuesSource`/`SelectSource` 是不同的表达式类型，多态分发合理

### 4.2 `format_create_table_like` — like_table 类型

- **isinstance**: `isinstance(like_table, tuple)` 判断 schema.table
- **改造**: `CreateTableExpression.like_table` 应统一为表达式对象（`TableExpression`），构造时将 tuple 包装为带 schema 的 `TableExpression`

### 4.3 `format_storage_options` — 值类型判断

- **isinstance**: `isinstance(value, str)`
- **改造**: 接收 expr 后，值统一用 `inline_sql_literal` 渲染，无需 isinstance

### 4.4 `format_json_function_expression` — 列引用

- **isinstance**: `isinstance(expr.column, bases.BaseExpression)`
- **改造**: `JSONExpression.column` 应统一为表达式对象，构造时将字符串包装为 `IdentifierExpression`

## 五、需要新建的表达式类

以下表达式类需在核心库 `python-activerecord` 中新建（MySQL 特有的在本项目中新建）：

| 表达式类 | 用途 | 创建位置 |
|---------|------|---------|
| `StorageOptionsExpression` | 存储选项 | 核心库 |
| `SpatialLiteralExpression` | 空间字面量 | MySQL 项目 |
| `STGeomFromTextExpression` | ST_GeomFromText | MySQL 项目 |
| `STGeomFromWKBExpression` | ST_GeomFromWKB | MySQL 项目 |
| `STAsTextExpression` | ST_AsText | MySQL 项目 |
| `STAsGeoJSONExpression` | ST_AsGeoJSON | MySQL 项目 |
| `STDistanceExpression` | ST_Distance | MySQL 项目 |
| `STWithinExpression` | ST_Within | MySQL 项目 |
| `STContainsExpression` | ST_Contains | MySQL 项目 |
| `CreateSpatialIndexExpression` | 创建空间索引 | MySQL 项目 |
| `SetLiteralExpression` | SET 字面量 | MySQL 项目 |
| `FindInSetExpression` | FIND_IN_SET | MySQL 项目 |
| `SetContainsExpression` | SET 包含 | MySQL 项目 |
| `VectorLiteralExpression` | 向量字面量 | MySQL 项目 |
| `StringToVectorExpression` | STRING_TO_VECTOR | MySQL 项目 |
| `VectorToStringExpression` | VECTOR_TO_STRING | MySQL 项目 |
| `VectorDimExpression` | VECTOR_DIM | MySQL 项目 |
| `DistanceEuclideanExpression` | 欧几里得距离 | MySQL 项目 |
| `DistanceCosineExpression` | 余弦距离 | MySQL 项目 |
| `DistanceDotExpression` | 点积距离 | MySQL 项目 |
| `CreateVectorIndexExpression` | 创建向量索引 | MySQL 项目 |

## 六、优先级排序

### P0 — 返回类型修复
1. `format_storage_options` → 接收 expr + `Tuple[str, tuple]`
2. `format_duality_object_select/body/nested` → 接收 expr + `Tuple[str, tuple]`

### P1 — 类型提示补齐（按文件）
3. `mixins/spatial.py` 9 个方法
4. `mixins/json.py` 11 个方法
5. `mixins/set_type.py` 3 个方法
6. `mixins/vector.py` 8 个方法
7. `mixins/datetime.py` 5 个方法
8. `mixins/ddl_column.py` 5 个方法

### P2 — isinstance 消除
9. `format_create_table_like` — like_table 统一为表达式
10. `format_storage_options` — 值用 inline_sql_literal
11. `format_json_function_expression` — 列统一为表达式

### P3 — 返回类型大小写统一
12. 全局 `Tuple[str, Tuple]` → `Tuple[str, tuple]`
