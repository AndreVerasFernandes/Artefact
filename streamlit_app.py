"""Interface Streamlit do atendente da Emporio da Musica."""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from src.agent import executar_agente, limpar_historico
from src.database import initialize_database
from src.rag import criar_indice_politicas, verificar_base_vetorial
from src.tools import configurar_database


st.set_page_config(
    page_title="Emporio da Musica | Atendimento",
    page_icon="🎵",
    layout="centered",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner=False)
def inicializar_servicos() -> dict[str, object]:
    """Load configuration and prepare the services shared by the chat session."""
    load_dotenv(override=True)
    database = initialize_database()
    configurar_database(database)

    vector_ok, vector_message = verificar_base_vetorial()
    if not vector_ok:
        criar_indice_politicas()
        vector_ok, vector_message = verificar_base_vetorial()

    return {
        "database": database,
        "vector_ok": vector_ok,
        "vector_message": vector_message,
    }

try:
    services = inicializar_servicos()
    startup_error = None
except Exception as error:
    services = None
    startup_error = error


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Grotesk:wght@500;600;700&display=swap');

    :root {
        --ink: #17231f;
        --muted: #64736d;
        --cream: #f7f4ed;
        --paper: #fffdf8;
        --green: #164b3c;
        --lime: #d7ed62;
        --coral: #e87955;
    }

    .stApp {
        background: radial-gradient(circle at 85% 4%, #e8f2bf 0, transparent 26%), var(--cream);
        color: var(--ink);
        font-family: 'DM Sans', sans-serif;
    }
    [data-testid='stSidebar'] { background: var(--green); }
    [data-testid='stSidebar'] * { color: #f5f8ee; }
    h1, h2, h3 { font-family: 'Space Grotesk', sans-serif; letter-spacing: 0; }
    .brand-mark {
        display: inline-block; padding: 6px 11px; border-radius: 999px;
        background: var(--lime); color: var(--green); font-size: .78rem;
        font-weight: 700; letter-spacing: .04em; text-transform: uppercase;
    }
    .hero { padding: 1.8rem 0 .8rem; }
    .hero h1 { margin: .55rem 0 .25rem; font-size: clamp(2rem, 7vw, 3.3rem); color: var(--green); }
    .hero p { color: var(--muted); font-size: 1.05rem; max-width: 39rem; }
    [data-testid='stChatMessage'] { background: var(--paper); border: 1px solid #e6e2d9; }
    [data-testid='stChatInput'] { background: var(--paper); }
    .service-ok { color: #b9dc68; }
    .service-error { color: #ffb09c; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## 🎵 Emporio da Musica")
    st.caption("Atendimento para quem vive a musica em Campo Grande/MS.")
    st.divider()
    st.markdown("### Servicos")
    if services:
        st.markdown("<p class='service-ok'>● Banco de dados pronto</p>", unsafe_allow_html=True)
        if services["vector_ok"]:
            st.markdown(
                f"<p class='service-ok'>● Base de politicas pronta<br><small>{services['vector_message']}</small></p>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown("<p class='service-error'>● Base de politicas indisponivel</p>", unsafe_allow_html=True)
    else:
        st.markdown("<p class='service-error'>● Falha na inicializacao</p>", unsafe_allow_html=True)
        st.caption(str(startup_error))
    st.divider()
    if st.button("Limpar conversa", use_container_width=True, type="secondary"):
        limpar_historico()
        st.session_state.messages = []
        st.rerun()

st.markdown(
    """
    <div class='hero'>
      <span class='brand-mark'>Som que aproxima</span>
      <h1>O que vamos tocar hoje?</h1>
      <p>Bem-vindo à Empório da Música. Encontre seu próximo instrumento, consulte um pedido ou tire dúvidas sobre nossas políticas.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if startup_error:
    st.error(f"Nao foi possivel preparar o atendimento: {startup_error}")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Oi! Eu sou o atendimento da Empório da Música. Posso ajudar com instrumentos, preços, pedidos e políticas da loja. O que você procura?",
        }
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Pergunte sobre instrumentos, pedidos ou políticas..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando a loja..."):
            response = executar_agente(prompt)
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
