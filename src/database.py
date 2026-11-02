"""SQLite database helpers for the store's structured data."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CSV_TABLES = {
    "categories": "desafio_tecnico_ai_eng - categories.csv",
    "customers": "desafio_tecnico_ai_eng - customers.csv",
    "order_items": "desafio_tecnico_ai_eng - order_items.csv",
    "orders": "desafio_tecnico_ai_eng - orders.csv",
    "products": "desafio_tecnico_ai_eng - products.csv",
    "promotions": "desafio_tecnico_ai_eng - promotions.csv",
}

QueryResult = list[dict[str, Any]] | str


def initialize_database(
    connection: sqlite3.Connection | None = None,
    data_dir: str | Path | None = None,
) -> sqlite3.Connection:
    """Load every store CSV into SQLite and return the ready-to-query connection."""
    database = connection or sqlite3.connect(":memory:")
    database.row_factory = sqlite3.Row
    csv_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR

    try:
        for table_name, filename in CSV_TABLES.items():
            csv_path = csv_dir / filename
            if not csv_path.exists():
                raise FileNotFoundError(f"Arquivo de dados nao encontrado: {csv_path}")

            dataframe = pd.read_csv(csv_path)
            dataframe.to_sql(table_name, database, if_exists="replace", index=False)
        database.commit()
    except (OSError, pd.errors.ParserError, sqlite3.Error, ValueError) as error:
        database.rollback()
        raise RuntimeError(f"Nao foi possivel carregar os dados da loja: {error}") from error

    return database


def _query(database: sqlite3.Connection, sql: str, parameters: tuple[Any, ...]) -> QueryResult:
    """Execute a read-only query and normalize rows for model consumption."""
    try:
        rows = database.execute(sql, parameters).fetchall()
    except sqlite3.Error as error:
        return f"Nao foi possivel consultar os dados da loja: {error}"

    if not rows:
        return "Nenhum registro encontrado para os filtros informados."

    return [dict(row) for row in rows]


def search_products(
    database: sqlite3.Connection,
    name: str | None = None,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    available_only: bool = True,
) -> QueryResult:
    """Search products by name, category, price range, and availability."""
    if min_price is not None and max_price is not None and min_price > max_price:
        return "A faixa de preco informada e invalida: o minimo e maior que o maximo."

    clauses = []
    parameters: list[Any] = []

    if name:
        clauses.append("LOWER(p.name) LIKE LOWER(?)")
        parameters.append(f"%{name}%")
    if category:
        clauses.append("(LOWER(c.name) LIKE LOWER(?) OR CAST(p.category_id AS TEXT) = ?)")
        parameters.extend((f"%{category}%", str(category)))
    if min_price is not None:
        clauses.append("p.price_brl >= ?")
        parameters.append(min_price)
    if max_price is not None:
        clauses.append("p.price_brl <= ?")
        parameters.append(max_price)
    if available_only:
        clauses.append("p.stock_quantity > 0")
        clauses.append("LOWER(p.status) = 'active'")

    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT p.*, c.name AS category_name
        FROM products AS p
        LEFT JOIN categories AS c ON c.category_id = p.category_id
        {where_clause}
        ORDER BY p.price_brl ASC, p.name ASC
    """
    return _query(database, sql, tuple(parameters))


def get_order_status(
    database: sqlite3.Connection,
    order_id: int | str | None = None,
    customer_id: int | str | None = None,
) -> QueryResult:
    """Return order status and delivery details by order or customer ID."""
    if order_id is None and customer_id is None:
        return "Informe o ID do pedido ou o ID do cliente para consultar o status."

    clauses = []
    parameters: list[Any] = []
    if order_id is not None:
        clauses.append("o.order_id = ?")
        parameters.append(order_id)
    if customer_id is not None:
        clauses.append("o.customer_id = ?")
        parameters.append(customer_id)

    sql = f"""
        SELECT o.order_id, o.customer_id, c.name AS customer_name,
               o.order_date, o.status, o.total_brl, o.payment_method,
               o.tracking_code, o.estimated_delivery, o.notes
        FROM orders AS o
        LEFT JOIN customers AS c ON c.customer_id = o.customer_id
        WHERE {' AND '.join(clauses)}
        ORDER BY o.order_date DESC, o.order_id DESC
    """
    return _query(database, sql, tuple(parameters))