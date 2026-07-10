import os
import sqlite3
import json
from typing import List, TypedDict, Annotated, Literal, Dict, Any
from datetime import datetime
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from tavily import TavilyClient
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class ChatbotState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    streaming=True,
    api_key=GROQ_API_KEY
)

@tool
def generate_medical_report(
    name: str, 
    age: str, 
    gender: str, 
    patient_id: str, 
    location: str, 
    complaints: str, 
    notes: str, 
    diagnosis: str, 
    medications: Any = None, 
    instructions: Any = None, 
    treatment_steps: Any = None
) -> str:
    """Generates a formal general medicine consultation report."""
    # Simplified for now, similar to others but for GP
    return f"Report generated for {name}. [General Physician Report]"
    # Simplified for now, similar to others but for GP
    return f"Report generated for {name}. [General Physician Report]"

@tool
def search_tool(query: str) -> str:
    """
    CRITICAL: Use this tool to check for the latest 2024-2026 FDA drug approvals, clinical guidelines,
    or looking up medical information that is not in the internal knowledge base.
    PRIORITY: Always search "https://dailymed.nlm.nih.gov/dailymed/index.cfm" first for medication details.
    """
    client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
    # Prepend site filter if it looks like a drug search
    is_drug_search = any(term in query.lower() for term in ["drug", "medication", "dose", "tablet", "syrup", "fda"])
    search_query = f"site:dailymed.nlm.nih.gov {query}" if is_drug_search else query
    
    raw_response = client.search(query=search_query, search_depth="advanced", max_results=5)
        
    prompt = ChatPromptTemplate.from_template("""
        You are a Medical Data Refiner for General Medicine. Your job is to take raw search results and make them professional and clean.
        
        QUERY: {query}
        RAW DATA: {raw_data}
        
        INSTRUCTIONS:
        1. If searching for medications, prioritize data from DailyMed (nlm.nih.gov).
        2. Summarize the latest 2024-2026 medical data, clinical guidelines, and FDA status.
        3. Remove all HTML tags, broken links, and advertisements.
        4. If information is missing, simply state 'Information not found in current search'.
        
        CLEAN SUMMARY:
        """)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"query": query, "raw_data": raw_response})

# Filter messages to save tokens
def filter_messages(messages: List[BaseMessage]) -> List[BaseMessage]:
    # 1. Always keep the System Message (usually the first one)
    system_messages = [msg for msg in messages if isinstance(msg, SystemMessage)]
    other_messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]

    # 2. Strategic "Sandwich" Windowing (Solution 3): 
    # Keep first 15 (Intake) and last 25 (Context) with a summary marker.
    if len(other_messages) > 40:
        intake_phase = other_messages[:15]
        recent_context = other_messages[-25:]
        
        middle_count = len(other_messages) - 40
        summary_marker = SystemMessage(content=f"[SYSTEM NOTE: {middle_count} middle messages have been condensed to save memory. The earlier clinical history and patient details are still accessible.]")
        
        other_messages = intake_phase + [summary_marker] + recent_context

    # 3. Filter out massive HTML reports from ToolMessages
    filtered_messages = []
    for msg in other_messages:
        if isinstance(msg, ToolMessage) and msg.name == "generate_medical_report":
            new_msg = ToolMessage(
                content="[Medical Report Generated Successfully - Full HTML content hidden to save tokens]",
                tool_call_id=msg.tool_call_id,
                name=msg.name,
                artifact=msg.artifact,
                status=msg.status
            )
            filtered_messages.append(new_msg)
        else:
            filtered_messages.append(msg)

    return system_messages + filtered_messages

tools = [generate_medical_report, search_tool]
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)

def model_calling(messages: List[BaseMessage]) -> AIMessage:
    system_message = SystemMessage(content=(
        "ROLE: You are Dr. Alara, a General Physician. "
        "STYLE: Professional, thorough, and guiding. "
        "MISSION: You are the first point of contact for patients. Your job is to assess general health, provide basic treatments, and most importantly, REFER to specialists when appropriate. "
        
        "\nREFERRAL LOGIC:"
        "1. If the patient has skin issues, recommend they see our Dermatologist (Dr. Zavian)."
        "2. If the patient has ear, nose, or throat issues, recommend our ENT Specialist (Dr. Anees)."
        "3. If the patient has mental health or behavioral issues, recommend our AI Psychiatrist (Dr. Aria)."
        "Always explain WHY the referral is helpful."

        "\nCLINICAL RIGOR: Get Name, Age, Location and Gender first. Ask clarifying questions about symptoms. "
        "Speak in simple English."
        
        "\nREPORTING & INTEGRITY:"
        "- MANDATORY: You are strictly FORBIDDEN from typing a medical report, summary, or diagnosis as text in the chat. You MUST use the 'generate_medical_report' tool for the final output."
        "- Only generate the report when the user is satisfied and asks for it."
        "- RE-VERIFICATION RULE: If demographics (Name, Age, Location, Gender) are missing from your current memory window, you MUST re-ask the patient for them before calling the tool."
        "- PATIENT ID: Always generate a unique 8-digit alphanumeric ID (e.g., GEN-112233) for the report."
        "- MEDICATION MAPPING: The 'medications' argument must be a LIST of dictionaries. Each dictionary MUST use these exact keys: {'name': '...', 'dosage': '...', 'duration': '...'}. Populate this using data from search tools."
    ))
    if not any(isinstance(msg, SystemMessage) for msg in messages):
        messages = [system_message] + messages
        
    # Apply filtering
    final_messages = filter_messages(messages)
    
    return llm_with_tools.invoke(final_messages)

def chat_node(state: ChatbotState):
    return {"messages": model_calling(state["messages"])}

graph = StateGraph(ChatbotState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)
graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge('tools', 'chat_node')

DB_NAME = "general.db"
conn = sqlite3.connect(database=DB_NAME, check_same_thread=False)
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    checkpointer = SqliteSaver(conn=conn)
except ImportError:
    from langgraph.checkpoint.memory import MemorySaver
    checkpointer = MemorySaver()

chatbot_compiled = graph.compile(checkpointer=checkpointer)
