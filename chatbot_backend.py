import asyncio
import threading
import requests
import aiosqlite
from typing import TypedDict, Annotated

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun

load_dotenv()

# ==========================================================
# 🔁 Dedicated async backend loop (REQUIRED for Streamlit)
# ==========================================================

_BACKEND_LOOP = asyncio.new_event_loop()
_BACKEND_THREAD = threading.Thread(
    target=_BACKEND_LOOP.run_forever,
    daemon=True
)
_BACKEND_THREAD.start()


def submit_async_task(coro):
    """Run coroutine safely on backend event loop."""
    return asyncio.run_coroutine_threadsafe(coro, _BACKEND_LOOP)


def run_async(coro):
    """Blocking helper for async backend calls."""
    return submit_async_task(coro).result()


# ==========================================================
# 🤖 LLM
# ==========================================================

llm = ChatOpenAI(
    temperature=0,
)

# ==========================================================
# 🧰 TOOLS
# ==========================================================

# 1️⃣ Web search
search_tool = DuckDuckGoSearchRun(region="us-en")


# 2️⃣ Stock price tool
@tool
def get_stock_price(symbol: str) -> dict:
    """
    Get latest stock price for a symbol like AAPL or TSLA.
    """
    url = (
        "https://www.alphavantage.co/query"
        f"?function=GLOBAL_QUOTE&symbol={symbol}"
        "&apikey=C9PE94QUEW9VWGFM"
    )
    try:
        return requests.get(url, timeout=10).json()
    except Exception as e:
        return {"error": str(e)}


# 3️⃣ Calculator tool
@tool
def calculate(expression: str) -> str:
    """
    Evaluate a math expression.
    Example: 2 + 3 * 4
    """
    try:
        result = eval(expression, {"__builtins__": {}})
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"


tools = [
    search_tool,
    get_stock_price,
    calculate,
]

llm_with_tools = llm.bind_tools(tools)

# ==========================================================
# 📦 STATE
# ==========================================================

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# ==========================================================
# 🧠 NODES
# ==========================================================

async def chat_node(state: ChatState):
    """
    Main LLM node.
    Either responds directly or requests a tool.
    """
    response = await llm_with_tools.ainvoke(state["messages"])
    return {"messages": [response]}


tool_node = ToolNode(tools)

# ==========================================================
# 💾 SQLITE CHECKPOINTER
# ==========================================================

async def _init_checkpointer():
    conn = await aiosqlite.connect("chatbot.db")
    return AsyncSqliteSaver(conn)


checkpointer = run_async(_init_checkpointer())

# ==========================================================
# 🧩 GRAPH (CORRECT & FINAL)
# ==========================================================

graph = StateGraph(ChatState)

graph.add_node("chat", chat_node)
graph.add_node("tools", tool_node)

# Start → Chat
graph.add_edge(START, "chat")

# ✅ CRITICAL FIX:
# Explicitly map "__end__" → END
graph.add_conditional_edges(
    "chat",
    tools_condition,
    {
        "tools": "tools",
        "__end__": END,
    },
)

# Tools → Chat (loop back)
graph.add_edge("tools", "chat")

# Compile graph
chatbot = graph.compile(checkpointer=checkpointer)

# ==========================================================
# 🧾 THREAD LIST HELPER (Sidebar)
# ==========================================================

async def _alist_threads():
    threads = set()
    async for checkpoint in checkpointer.alist(None):
        threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(threads)


def retrieve_all_threads():
    return run_async(_alist_threads())
