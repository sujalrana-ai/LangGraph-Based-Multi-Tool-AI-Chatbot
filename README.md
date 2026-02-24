# 🤖 LangGraph-Based-Multi-Tool-AI-Chatbot

An advanced agentic AI chatbot built using **LangGraph** for state-managed workflows and **Streamlit** for a seamless user interface. This project integrates multiple tools and features persistent conversation memory.

## ✨ Key Features
- **Agentic Reasoning**: Uses LangGraph to handle complex decision-making and tool-calling loops.
- **Multi-Tool Integration**: Integrated with tools like Tavily Search for real-time information.
- **Persistent State**: Utilizes SQLite checkpointers to maintain conversation history.
- **Observability**: Fully integrated with **LangSmith** for real-time tracing and debugging.

## 🛠️ Tech Stack
- **Framework**: LangChain & LangGraph
- **LLM**: OpenAI (GPT-4o / GPT-3.5)
- **Frontend**: Streamlit
- **Tracing**: LangSmith

## ⚙️ Setup Instructions

 1. **Clone the repository**:
   ```bash
   git clone [https://github.com/sujalrana-ai/LangGraph-Based-Multi-Tool-AI-Chatbot.git](https://github.com/sujalrana-ai/LangGraph-Based-Multi-Tool-AI-Chatbot.git)
   cd LangGraph-Based-Multi-Tool-AI-Chatbot
```
2. Create a Virtual Environment:
```
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate 
```
3. Install Dependencies:
```
pip install -r requirements.txt
```
4. Configure Environment Variables:

 Rename .env.example to .env.

 Add your API keys (OpenAI, LangChain, Tavily).

5. Run the Application:
```
streamlit run chatbot_streamlit_frontend.py
