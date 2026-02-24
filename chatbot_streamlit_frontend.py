import queue
import uuid
import streamlit as st

from chatbot_backend import chatbot, retrieve_all_threads, submit_async_task
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


# ==========================================================
# Utilities
# ==========================================================

def generate_thread_id():
    return uuid.uuid4()


def generate_title_from_message(text: str, max_words=6):
    words = text.strip().split()
    return " ".join(words[:max_words]).capitalize() or "New conversation"


def add_thread(thread_id):
    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)


def reset_chat():
    st.session_state["message_history"] = []
    if not st.session_state["is_temporary"]:
        new_id = generate_thread_id()
        st.session_state["thread_id"] = new_id
        add_thread(new_id)


def load_conversation(thread_id):
    state = chatbot.get_state(
        config={"configurable": {"thread_id": thread_id}}
    )
    return state.values.get("messages", [])


def delete_thread(thread_id):
    st.session_state["chat_threads"].remove(thread_id)
    st.session_state["thread_titles"].pop(thread_id, None)
    st.session_state["pinned_threads"].discard(thread_id)
    if st.session_state["thread_id"] == thread_id:
        reset_chat()


# ==========================================================
# Session Init
# ==========================================================

if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = retrieve_all_threads()

if "thread_titles" not in st.session_state:
    st.session_state["thread_titles"] = {}

if "pinned_threads" not in st.session_state:
    st.session_state["pinned_threads"] = set()

if "rename_thread_id" not in st.session_state:
    st.session_state["rename_thread_id"] = None

if "is_temporary" not in st.session_state:
    st.session_state["is_temporary"] = False

add_thread(st.session_state["thread_id"])


# ==========================================================
# Sidebar UI (Modern ChatGPT Style)
# ==========================================================

st.sidebar.title("LangGraph Chatbot")

st.sidebar.toggle(
    "🕶 Temporary Chat",
    key="is_temporary",
    help="Temporary chats are not saved in history",
)

if st.sidebar.button("＋ New Chat", use_container_width=True):
    reset_chat()


def render_thread(thread_id):
    title = st.session_state["thread_titles"].get(
        thread_id, "New conversation"
    )

    is_active = thread_id == st.session_state["thread_id"]

    row = st.sidebar.container()
    cols = row.columns([6, 1])

    # Active highlight
    button_type = "primary" if is_active else "secondary"

    if cols[0].button(
        title,
        key=f"open_{thread_id}",
        use_container_width=True,
        type=button_type
    ):
        st.session_state["thread_id"] = thread_id
        messages = load_conversation(thread_id)
        st.session_state["message_history"] = [
            {
                "role": "user" if isinstance(m, HumanMessage) else "assistant",
                "content": m.content
            }
            for m in messages
        ]

    # 3-dot popover menu
    with cols[1]:
        with st.popover("⋯", use_container_width=True):
            if st.button("✏ Rename", key=f"rename_{thread_id}"):
                st.session_state["rename_thread_id"] = thread_id
                st.rerun()

            if st.button(
                "📌 Pin" if thread_id not in st.session_state["pinned_threads"]
                else "📍 Unpin",
                key=f"pin_{thread_id}"
            ):
                if thread_id in st.session_state["pinned_threads"]:
                    st.session_state["pinned_threads"].remove(thread_id)
                else:
                    st.session_state["pinned_threads"].add(thread_id)
                st.rerun()

            if st.button("🗑 Delete", key=f"delete_{thread_id}"):
                delete_thread(thread_id)
                st.rerun()


if not st.session_state["is_temporary"]:

    pinned = [t for t in st.session_state["chat_threads"]
              if t in st.session_state["pinned_threads"]]

    unpinned = [t for t in st.session_state["chat_threads"]
                if t not in st.session_state["pinned_threads"]]

    if pinned:
        st.sidebar.markdown("### 📌 Pinned")
        for t in pinned[::-1]:
            render_thread(t)

    st.sidebar.markdown("### 💬 Chats")
    for t in unpinned[::-1]:
        render_thread(t)


# ==========================================================
# Main Chat UI
# ==========================================================

for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_input = st.chat_input(
    "Temporary chat (not saved)"
    if st.session_state["is_temporary"]
    else "Type a message..."
)

if user_input:
    st.session_state["message_history"].append(
        {"role": "user", "content": user_input}
    )

    if (
        not st.session_state["is_temporary"]
        and st.session_state["thread_id"] not in st.session_state["thread_titles"]
    ):
        st.session_state["thread_titles"][st.session_state["thread_id"]] = \
            generate_title_from_message(user_input)

    with st.chat_message("user"):
        st.markdown(user_input)

    CONFIG = (
        {"run_name": "temp_chat"}
        if st.session_state["is_temporary"]
        else {
            "configurable": {"thread_id": st.session_state["thread_id"]},
            "metadata": {"thread_id": st.session_state["thread_id"]},
            "run_name": "chat_turn",
        }
    )

    with st.chat_message("assistant"):
        status_holder = {"box": None}

        def ai_stream():
            event_queue = queue.Queue()

            async def run_stream():
                async for msg, _ in chatbot.astream(
                    {"messages": [HumanMessage(content=user_input)]},
                    config=CONFIG,
                    stream_mode="messages",
                ):
                    event_queue.put(msg)
                event_queue.put(None)

            submit_async_task(run_stream())

            while True:
                m = event_queue.get()
                if m is None:
                    break
                if isinstance(m, ToolMessage):
                    if status_holder["box"] is None:
                        status_holder["box"] = st.status(
                            f"🔧 Using `{m.name}`...",
                            expanded=True
                        )
                if isinstance(m, AIMessage):
                    yield m.content

        ai_message = st.write_stream(ai_stream())

        if status_holder["box"]:
            status_holder["box"].update(
                label="✅ Tool finished",
                state="complete",
                expanded=False,
            )

    st.session_state["message_history"].append(
        {"role": "assistant", "content": ai_message}
    )