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
- Guardrails Available To Prevent Modification queries via Human In The Loop
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
├── agents/                     
│   ├── orchestrator_agent.py  
│   ├── sql_generator_agent.py  
│   ├── sql_validator_agent.py  
│   ├── execution_agent.py      
│   ├── clarification_agent.py  
│   ├── visualization_agent.py  
│   └── summarizer_agent.py     
│
├── graph/                      
│   ├── workflow.py             
│   └── state.py               
│
├── memory/                     
│   ├── memory_manager.py       
│   └── store/                  
│
├── logs/                       
│   └── sessions/               
│
├── data/                       
│   ├── db_config.py            
│   ├── schema.sql              
│   └── seed_data.sql           
│
├── app.py                      
├── requirements.txt            
├── .env.example                
└── README.md                   
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
