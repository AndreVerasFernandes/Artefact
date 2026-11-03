"""Conversation loop for the Emporio da Musica assistant."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .config import GEMINI_MODEL, GOOGLE_API_KEY
from .prompts import SYSTEM_PROMPT
from .tools import STORE_TOOLS


MAX_TOOL_ROUNDS = 5
_conversation_history: list[HumanMessage | AIMessage | ToolMessage] = []
_tool_map = {store_tool.name: store_tool for store_tool in STORE_TOOLS}
_model: ChatGoogleGenerativeAI | None = None


def _get_model() -> ChatGoogleGenerativeAI:
    global _model
    if _model is None:
        if not GOOGLE_API_KEY:
            raise RuntimeError("A variavel GOOGLE_API_KEY nao esta configurada.")
        _model = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.2,
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
        if isinstance(error, RuntimeError) and "GOOGLE_API_KEY" in str(error):
            return "O atendimento ainda nao esta configurado: informe a chave GOOGLE_API_KEY."
        return "Nao consegui processar sua mensagem neste momento. Tente novamente mais tarde."


def limpar_historico() -> None:
    """Clear the in-memory conversation history for a new session."""
    _conversation_history.clear()