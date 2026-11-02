"""LangChain tools for structured store data and policy retrieval."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from langchain_core.tools import tool

from .database import QueryResult, get_order_status, initialize_database, search_products
from .rag import consultar_politicas


_database: sqlite3.Connection | None = None


def _get_database() -> sqlite3.Connection:
    global _database
    if _database is None:
        _database = initialize_database()
    return _database


def _as_text(result: QueryResult) -> str:
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False, default=str)


@tool
def consultar_catalogo(
    termo_busca: str | None = None,
    preco_maximo: float | None = None,
    categoria: str | None = None,
) -> str:
    """Consulte o catalogo operacional de instrumentos musicais da loja.

    Use esta ferramenta quando o cliente perguntar por produtos, precos,
    categorias ou disponibilidade em estoque. Nao use para regras de troca,
    garantia, frete, devolucao, pagamento ou horario de funcionamento; essas
    orientacoes devem ser consultadas em consultar_regras_e_politicas.

    Args:
        termo_busca: Parte do nome ou modelo do instrumento. Omita quando a
            busca deve listar todos os produtos da categoria.
        preco_maximo: Preco maximo em reais. Use apenas quando o cliente
            informar um limite de orcamento.
        categoria: Nome ou ID da categoria, como "Violões", "Guitarras" ou 5.
    """
    if preco_maximo is not None and preco_maximo < 0:
        return "O preco maximo deve ser maior ou igual a zero."

    try:
        result = search_products(
            _get_database(),
            name=termo_busca,
            category=categoria,
            max_price=preco_maximo,
        )
    except (OSError, RuntimeError, sqlite3.Error, ValueError) as error:
        return f"Nao foi possivel consultar o catalogo: {error}"
    return _as_text(result)


@tool
def consultar_pedido(codigo_pedido: int | str) -> str:
    """Consulte o status e os detalhes operacionais de um pedido.

    Use esta ferramenta somente quando o cliente fornecer ou perguntar pelo
    codigo/ID de um pedido. Ela retorna status, total, pagamento, rastreamento,
    data estimada de entrega e dados basicos do cliente. Nao use para explicar
    as regras gerais de frete, devolucao ou garantia; consulte
    consultar_regras_e_politicas nesses casos.

    Args:
        codigo_pedido: ID numerico do pedido informado pelo cliente.
    """
    if not str(codigo_pedido).strip():
        return "Informe um codigo de pedido valido."

    try:
        result = get_order_status(_get_database(), order_id=codigo_pedido)
    except (OSError, RuntimeError, sqlite3.Error, ValueError) as error:
        return f"Nao foi possivel consultar o pedido: {error}"
    return _as_text(result)


@tool
def consultar_regras_e_politicas(pergunta: str) -> str:
    """Consulte as diretrizes internas da loja por busca semantica no PDF.

    Use esta ferramenta para responder perguntas sobre trocas, devolucoes,
    garantia, formas de pagamento, frete, entrega, horarios, atendimento,
    promocoes ou o escopo de produtos vendidos pela loja. Nao use para buscar
    preco, estoque, nome de produto ou status de um pedido, pois esses dados
    mudam e devem ser consultados nas ferramentas operacionais apropriadas.

    Args:
        pergunta: Pergunta completa do cliente sobre uma regra ou procedimento.
    """
    return consultar_politicas(pergunta)


STORE_TOOLS = [consultar_catalogo, consultar_pedido, consultar_regras_e_politicas]