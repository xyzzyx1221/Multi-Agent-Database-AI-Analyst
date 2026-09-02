import os
import json
from typing import Annotated, TypedDict, Union, List, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
import operator

from agents.schema_agent import schema_agent
from agents.query_agent import query_agent
from agents.guardrail_agent import guardrail_agent
from agents.insight_agent import insight_agent
from agents.viz_report_agent import viz_report_agent
from tools.db_executor import executor
from memory.conversation_store import conversation_store
from memory.reference_resolver import reference_resolver
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    session_id: str
    question: str
    sql: str
    schema_context: str
    retry_count: int
    current_task_index: int
    tasks: List[Dict[str, Any]]
    task_results: List[Dict[str, Any]]
    is_safe: bool
    guardrail_feedback: str
    final_result: Union[list, str, None]

class Orchestrator:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        
        workflow = StateGraph(AgentState)

        # Nodes
        workflow.add_node("resolve_references", self.resolve_references_node)
        workflow.add_node("planner", self.planner_node)
        workflow.add_node("fetch_schema", self.fetch_schema_node)
        workflow.add_node("generate_sql", self.generate_sql_node)
        workflow.add_node("validate_sql", self.validate_sql_node)
        workflow.add_node("execute_sql", self.execute_sql_node)
        workflow.add_node("generate_insight", self.generate_insight_node)
        workflow.add_node("generate_report", self.generate_report_node)

        # Edges
        workflow.set_entry_point("resolve_references")
        workflow.add_edge("resolve_references", "planner")
        
        # ROUTER: Decision point after planning
        workflow.add_conditional_edges(
            "planner",
            self.should_have_tasks,
            {
                "has_tasks": "fetch_schema",
                "no_tasks": "generate_insight"
            }
        )
        
        workflow.add_edge("fetch_schema", "generate_sql")
        workflow.add_edge("generate_sql", "validate_sql")

        # Inner Loop: Security/Syntax Retry
        workflow.add_conditional_edges(
            "validate_sql",
            self.should_retry,
            {
                "retry": "generate_sql",
                "proceed": "execute_sql",
                "wait_for_human": END,
                "end": END
            }
        )

        # Outer Loop: Task Sequence
        workflow.add_conditional_edges(
            "execute_sql",
            self.should_next_task,
            {
                "next_task": "generate_sql",
                "finish": "generate_insight"
            }
        )

        # Final Reporting Path
        workflow.add_conditional_edges(
            "generate_insight",
            self.should_viz,
            {
                "viz": "generate_report",
                "end": END
            }
        )
        workflow.add_edge("generate_report", END)

        self.memory = MemorySaver()
        self.app = workflow.compile(checkpointer=self.memory, interrupt_before=["execute_sql"])

    def resolve_references_node(self, state: AgentState):
        history = conversation_store.load_history(state["session_id"])
        is_follow_up, resolved_question = reference_resolver.resolve(state["question"], history)
        
        if isinstance(resolved_question, str) and resolved_question.startswith("PIVOT:"):
            conversation_store.clear_history(state["session_id"])
            resolved_question = resolved_question.replace("PIVOT:", "")
            
        return {"question": resolved_question}

    def planner_node(self, state: AgentState):
        schema = schema_agent.get_relevant_schema(state["question"])
        prompt = f"""You are a Task Planner. Break the request into SQL tasks.
User Question: {state['question']}
Schema: {schema}

RULES:
1. If it's a 'report', 'summary', or multiple metrics, create multiple tasks.
2. If it's a greeting (hi, hello) or non-DB request, return an empty list [].
3. Use dates for 2025/2026.

Return JSON: {{"tasks": [{{'goal': '...', 'type': 'sql'}}]}}
Return ONLY the JSON.
"""
        try:
            response = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            plan_data = json.loads(content)
            tasks = plan_data.get("tasks", [])
        except Exception as e:
            print("Planner error:", e)
            tasks = []
        
        return {
            "tasks": tasks, 
            "current_task_index": 0, 
            "task_results": [],
            "retry_count": 0,
            "guardrail_feedback": "",
            "is_safe": True
        }

    def should_have_tasks(self, state: AgentState):
        if state.get("tasks") and len(state["tasks"]) > 0:
            return "has_tasks"
        return "no_tasks"

    def fetch_schema_node(self, state: AgentState):
        context = schema_agent.get_relevant_schema(state["question"])
        return {"schema_context": context}

    def generate_sql_node(self, state: AgentState):
        idx = state["current_task_index"]
        task = state["tasks"][idx]
        retry_count = state.get("retry_count", 0)
        is_safe = state.get("is_safe", True)
        
        feedback = state.get("guardrail_feedback", "")
        if not is_safe and feedback and "NEEDS_CONFIRMATION" not in feedback.upper():
            retry_count += 1
            prompt_ext = f"\n\nPrevious error: {feedback}"
        else:
            prompt_ext = ""
            
        sql = query_agent.generate_sql(task['goal'] + prompt_ext, state["schema_context"])
        return {"sql": sql, "retry_count": retry_count, "guardrail_feedback": "", "is_safe": True}

    def validate_sql_node(self, state: AgentState):
        is_safe, reasoning = guardrail_agent.validate_sql(state["sql"], state["question"])
        return {"is_safe": is_safe, "guardrail_feedback": reasoning}

    def should_retry(self, state: AgentState):
        if state["is_safe"]: return "proceed"
        if "NEEDS_CONFIRMATION" in state.get("guardrail_feedback", "").upper(): return "wait_for_human" 
        return "retry" if state["retry_count"] < 2 else "end"

    def execute_sql_node(self, state: AgentState):
        try:
            res = executor.execute(state["sql"], validated=True)
            task_goal = state["tasks"][state["current_task_index"]]["goal"]
            task_sql = state["sql"]
            conversation_store.save_turn(state["session_id"], {
                "question": state["question"], "sql": task_sql, "final_result": str(res)
            })
            current_results = list(state.get("task_results", []))
            current_results.append({"task": task_goal, "sql": task_sql, "result": res})
            return {
                "task_results": current_results, 
                "retry_count": 0, 
                "guardrail_feedback": "",
                "is_safe": True,
                "current_task_index": state["current_task_index"] + 1
            }
        except Exception as e:
            return {"final_result": f"Error: {str(e)}"}

    def should_next_task(self, state: AgentState):
        return "next_task" if state["current_task_index"] < len(state["tasks"]) else "finish"

    def generate_insight_node(self, state: AgentState):
        # If there is already an error in final_result, return it immediately
        if state.get("final_result") and "Error:" in str(state["final_result"]):
            return {"final_result": state["final_result"]}
            
        tasks = state.get("tasks", [])
        results = state.get("task_results", [])
        
        # If no tasks were planned for this specific turn, results are stale/previous
        if not tasks:
            results = []
            
        insight = insight_agent.generate_insight(state["question"], results, state.get("schema_context", ""))
        return {"final_result": insight}

    def generate_report_node(self, state: AgentState):
        report = viz_report_agent.generate_report(state["question"], state["task_results"])
        return {"final_result": report}

    def should_viz(self, state: AgentState):
        if len(state.get("tasks", [])) > 7 or "report" in state["question"].lower():
            return "viz"
        return "end"

    def run(self, question: str, session_id: str = "default_user"):
        config = {"configurable": {"thread_id": session_id}}
        inputs = {
            "question": question, 
            "session_id": session_id, 
            "messages": [], 
            "retry_count": 0,
            "task_results": [],
            "tasks": [],
            "sql": "",
            "final_result": None,
            "guardrail_feedback": ""
        }
        self.app.invoke(inputs, config=config)
        
        # Automatically resume execution while interrupted at execute_sql if safe
        while True:
            snapshot = self.app.get_state(config)
            if not snapshot.next or "execute_sql" not in snapshot.next:
                break
            feedback = snapshot.values.get("guardrail_feedback", "")
            if "safe to execute" in feedback.lower() and "confirmation required" not in feedback.lower():
                self.app.invoke(None, config=config)
            else:
                break
                
        return self.app.get_state(config).values

    def resume(self, session_id: str):
        config = {"configurable": {"thread_id": session_id}}
        return self.app.invoke(None, config=config)

orchestrator = Orchestrator()
