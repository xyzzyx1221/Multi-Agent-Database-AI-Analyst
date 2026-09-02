# 🧠 Multi-Agent Database AI Analyst

An autonomous multi-agent system that analyzes data stored in a **Neon (PostgreSQL) database** using **LangChain**, **LangGraph**, and **OpenAI LLMs**. The system orchestrates multiple specialized agents through linear, conditional, and iterative workflows, with persistent context memory and session logging.

---

## 🚀 Overview

This project acts as an AI-powered data analyst that can:

- Understand natural language queries about your database
- Plan and route tasks across multiple specialized agents
- Generate, validate, and execute SQL queries on Neon DB
- Iterate/self-correct on failed queries or incomplete answers
- Maintain conversational context/memory across turns
- Log every session for auditing and debugging
- Present results through an interactive **Streamlit** UI

---

## 🏗️ Architecture

The system is built as a **LangGraph state machine** where each node is an agent with a specific responsibility. Workflows can be:

- **Linear** → e.g. Query Understanding → SQL Generation → Execution → Response
- **Conditional** → e.g. route to Clarification Agent if query is ambiguous, or to Visualization Agent if user asks for a chart
- **Iterative** → e.g. SQL Validator/Debugger Agent loops with SQL Generator Agent until query executes successfully or max retries reached

```
                         ┌────────────────────┐
                         │   User (Streamlit)  │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌────────────────────┐
                         │  Orchestrator Agent │
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
     ┌─────────────────┐  ┌──────────────────┐  ┌───────────────────┐
     │ Clarification    │  │ SQL Generator     │  │ Visualization      │
     │ Agent            │  │ Agent             │  │ Agent               │
     └─────────────────┘  └────────┬──────────┘  └───────────────────┘
                                     │  (iterative loop)
                                     ▼
                           ┌───────────────────┐
                           │ SQL Validator /    │
                           │ Debugger Agent     │
                           └────────┬──────────┘
                                     │
                                     ▼
                           ┌───────────────────┐
                           │ Execution Agent    │
                           │ (Neon DB)          │
                           └────────┬──────────┘
                                     │
                                     ▼
                           ┌───────────────────┐
                           │ Summarizer /       │
                           │ Response Agent     │
                           └────────┬──────────┘
                                     │
                                     ▼
                           ┌───────────────────┐
                           │ Context Memory     │
                           │ (updated & saved)  │
                           └───────────────────┘
```

---

## 📁 Project Structure

```
multi-agent-db-analyst/
│
├── agents/                     # All agent definitions
│   ├── orchestrator_agent.py   # Routes tasks based on query intent
│   ├── sql_generator_agent.py  # Converts NL query → SQL
│   ├── sql_validator_agent.py  # Validates/debugs SQL (iterative loop)
│   ├── execution_agent.py      # Executes SQL against Neon DB
│   ├── clarification_agent.py  # Asks follow-up Qs on ambiguous input
│   ├── visualization_agent.py  # Generates charts/plots from results
│   └── summarizer_agent.py     # Converts results into NL response
│
├── graph/                      # LangGraph workflow definitions
│   ├── workflow.py             # Defines nodes, edges, conditionals
│   └── state.py                # Shared graph state schema
│
├── memory/                     # Context & conversation memory
│   ├── memory_manager.py       # Read/write memory logic
│   └── store/                  # Persisted memory (vector/db backed)
│
├── logs/                       # Execution & session logs
│   └── sessions/               # One log file per session/run
│
├── data/                       # Database setup & schema
│   ├── db_config.py            # Neon DB connection config
│   ├── schema.sql              # Table definitions
│   └── seed_data.sql           # Sample/seed data (optional)
│
├── app.py                      # Streamlit front-end application
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
└── README.md                   # Project documentation
```

---

## ⚙️ Tech Stack

| Component        | Technology                  |
|-------------------|------------------------------|
| LLM               | OpenAI (GPT models)          |
| Orchestration     | LangChain + LangGraph        |
| Database          | Neon (Serverless PostgreSQL) |
| Memory            | LangChain memory / vector store |
| UI                | Streamlit                    |
| Logging           | Custom session-based logger  |
