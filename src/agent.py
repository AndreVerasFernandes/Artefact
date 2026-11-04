"""Conversation loop for the Emporio da Musica assistant."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from .config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    OPENROUTER_SITE_NAME,
    OPENROUTER_SITE_URL,
)
from .prompts import SYSTEM_PROMPT
from .tools import STORE_TOOLS


MAX_TOOL_ROUNDS = 5
_conversation_history: list[HumanMessage | AIMessage | ToolMessage] = []
_tool_map = {store_tool.name: store_tool for store_tool in STORE_TOOLS}
_model: BaseChatModel | None = None


def _is_quota_error(error: Exception) -> bool:
    """Identify provider quota failures without depending on one SDK exception."""
    error_code = getattr(error, "code", None)
    status_code = getattr(error, "status_code", None)
    error_text = str(error).lower()
    return (
        error_code == 429
        or status_code == 429
        or "resourceexhausted" in error_text
        or "quota exceeded" in error_text
    )


def _get_model() -> BaseChatModel:
    global _model
    if _model is None:
        if not OPENROUTER_API_KEY:
            raise RuntimeError("A variavel OPENROUTER_API_KEY nao esta configurada.")
        headers = {"X-Title": OPENROUTER_SITE_NAME}
        if OPENROUTER_SITE_URL:
            headers["HTTP-Referer"] = OPENROUTER_SITE_URL
        _model = ChatOpenAI(
            model=OPENROUTER_MODEL,
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            temperature=0.2,
            max_retries=0,
            default_headers=headers,
        ).bind_tools(STORE_TOOLS)
    return _model


def _response_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = [block.get("text", "") for block in content if isinstance(block, dict)]
        return "".join(text_parts).strip()
    return str(content)


def executar_agente(mensagem_usuario: str) -> str:
    """Process a user message while preserving the current session history."""
    if not mensagem_usuario or not mensagem_usuario.strip():
        return "Por favor, envie uma mensagem para que eu possa ajudar."

    history_start = len(_conversation_history)
    _conversation_history.append(HumanMessage(content=mensagem_usuario.strip()))

    try:
        model = _get_model()
        for _ in range(MAX_TOOL_ROUNDS):
            response = model.invoke(
                [SystemMessage(content=SYSTEM_PROMPT), *_conversation_history]
            )
            _conversation_history.append(response)

            if not response.tool_calls:
                return _response_text(response.content)

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                store_tool = _tool_map.get(tool_name)
                if store_tool is None:
                    tool_result = f"Ferramenta desconhecida: {tool_name}"
                else:
                    tool_result = store_tool.invoke(tool_call.get("args", {}))
                _conversation_history.append(
                    ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tool_call["id"],
                        name=tool_name,
                    )
                )

        return "Nao consegui concluir a consulta neste momento. Tente reformular sua pergunta."
    except Exception as error:
        del _conversation_history[history_start:]
        if isinstance(error, RuntimeError) and "OPENROUTER_API_KEY" in str(error):
            return "O atendimento ainda nao esta configurado: informe a chave OPENROUTER_API_KEY."
        if _is_quota_error(error):
            return "O atendimento atingiu o limite de uso da API. Tente novamente mais tarde ou fale com a equipe da loja."
        return "Nao consegui processar sua mensagem neste momento. Tente novamente mais tarde."


def limpar_historico() -> None:
    """Clear the in-memory conversation history for a new session."""
    _conversation_history.clear()