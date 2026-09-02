import streamlit as st
import os
from agents.orchestrator import orchestrator
from memory.conversation_store import conversation_store
import uuid

# Page Configuration
st.set_page_config(
    page_title="Conversational DB Analyst",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for a High-Standard Enterprise Look
st.markdown("""
    <style>
    /* Main background */
    .stApp {
        background-color: #FBFB FB;
    }
    
    /* Sidebar - Deep Navy/Slate Professional Theme */
    [data-testid="stSidebar"] {
        background-color: #0F172A !important;
        color: #F8FAFC !important;
    }
    [data-testid="stSidebar"] * {
        color: #F8FAFC !important;
    }
    
    /* Sidebar Headers */
    .sidebar-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #38BDF8 !important;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sidebar-subtitle {
        font-size: 0.9rem;
        color: #94A3B8 !important;
        text-align: center;
        margin-bottom: 2rem;
    }

    /* Chat Message Styling */
    .stChatMessage {
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Custom Report Container */
    .report-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* Header Styling */
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E293B;
        letter-spacing: -0.025em;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #64748B;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Session State Initialization
if "session_id" not in st.session_state:
    st.session_state.session_id = f"session_{uuid.uuid4().hex[:8]}"
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
with st.sidebar:
    st.markdown('<div class="sidebar-title">📈 NexusDB</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-subtitle">Enterprise AI Database Analyst</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown("### 🎯 Guide Prompts")
    
    with st.expander("🔍 Analysis Examples"):
        st.markdown("""
        - *'Who are the top 5 customers by revenue?'*
        - *'What is the total sales for the North region?'*
        """)
    
    with st.expander("🧠 Memory Tests"):
        st.markdown("""
        - Ask for top customers, then:
        - *'What are their email addresses?'*
        """)
    
    with st.expander("📋 Report Requests"):
        st.markdown("""
        - *'Generate a monthly report for January covering sales and returns.'*
        """)
    
    st.markdown("---")
    st.markdown("### ⚙️ System Status")
    st.success("● Neon Postgres: Connected")
    st.caption(f"ID: {st.session_state.session_id}")
    
    if st.button("🗑️ Clear Session", use_container_width=True):
        conversation_store.clear_history(st.session_state.session_id)
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    st.markdown("#### 🛠️ Agent Pipeline")
    st.markdown("🔹 **Planner**\n🔹 **Schema Agent**\n🔹 **Query Agent**\n🔹 **Guardrail**\n🔹 **Insight Agent**\n🔹 **Viz Agent**")

# Main UI
st.title("Enterprise Database Analyst")
st.markdown("Query your business data in natural language. I'll handle the SQL, safety, and analysis.")

# Chat Display
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "technical_trace" in message:
            with st.expander("🔍 View Technical Trace"):
                st.code(message["technical_trace"])
        
        # Handle Chart display inside the loop
        chart_path = message.get("chart")
        if chart_path and os.path.exists(chart_path) and os.path.getsize(chart_path) > 0:
            try:
                st.image(chart_path, caption="Visual Analysis")
            except Exception as e:
                st.warning(f"Could not render chart: {e}")
        elif chart_path:
            st.warning("Chart was generated but is currently unavailable.")

# User Input
if prompt := st.chat_input("Ask me about your sales, customers, or marketing..."):
    # Clear previous chart to avoid displaying old charts for new queries
    chart_path = os.path.join("logs/traces", "chart.png")
    if os.path.exists(chart_path):
        try:
            os.remove(chart_path)
        except Exception:
            pass

    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process Request
    with st.chat_message("assistant"):
        with st.status("🧠 Thinking...", expanded=True) as status:
            st.write("Resolving references...")
            
            # Run orchestrator
            result_state = orchestrator.run(prompt, session_id=st.session_state.session_id)
            
            # CHECK FOR INTERRUPT (Human-in-the-Loop)
              # CHECK FOR INTERRUPT (Human-in-the-Loop)
            snapshot = orchestrator.app.get_state({"configurable": {"thread_id": st.session_state.session_id}})
            if snapshot.next:
                feedback = result_state.get('guardrail_feedback', '')
                
                # AUTOMATIC PASS: If safe, resume immediately
                if "safe to execute" in feedback.lower() and "confirmation required" not in feedback.lower():
                    result_state = orchestrator.resume(st.session_state.session_id)
                    st.write("Executing safe query...")
                else:
                    # MANUAL PASS: Modification detected
                    status.update(label="⚠️ Action Required", state="running")
                    sql_to_verify = result_state.get('sql', 'Unknown SQL')
                    
                    st.warning(f"**Human Confirmation Required**\n\n{feedback}")
                    st.code(sql_to_verify, language="sql")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Confirm Execution", key="confirm"):
                            res_state = orchestrator.resume(st.session_state.session_id)
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": res_state.get('final_result', "Executed successfully."),
                                "technical_trace": f"SQL: {res_state.get('sql')}\nConfirmed by human",
                                "chart": None
                            })
                            st.rerun()
                    with col2:
                        if st.button("❌ Deny", key="deny"):
                            st.error("Execution cancelled by user.")
                            st.rerun()
                    st.stop()

            st.write("Generating SQL and validating safety...")
            st.write("Executing against Neon DB...")
            st.write("Synthesizing insights...")
            
            status.update(label="Analysis Complete!", state="complete", expanded=False)

        # Final Answer
        final_answer = result_state.get('final_result', "I couldn't find an answer.")
        st.markdown(final_answer)
        
        # Add to state
        task_res_list = result_state.get('task_results', [])
        if task_res_list:
            all_sqls = "\n\n".join([f"Task: {tr.get('task')}\nSQL: {tr.get('sql')}" for tr in task_res_list])
            technical_trace = f"{all_sqls}\n\nTasks Executed: {len(task_res_list)}"
        else:
            technical_trace = f"SQL: {result_state.get('sql')}\nTasks: {len(result_state.get('tasks', []))}"
        
        # Determine if a chart exists for this specific result
        # We check the same path the viz agent uses
        chart_path = os.path.join("logs/traces", "chart.png")
        actual_chart = chart_path if os.path.exists(chart_path) and os.path.getsize(chart_path) > 0 else None

        st.session_state.messages.append({
            "role": "assistant", 
            "content": final_answer,
            "technical_trace": technical_trace,
            "chart": actual_chart
        })
