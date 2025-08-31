from __future__ import annotations

from typing import Annotated, List, Literal, Optional
from typing_extensions import TypedDict

from pydantic.v1 import BaseModel, Field
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langchain.prompts import PromptTemplate

from core.llm import get_model
from core.settings import settings

# LLM setup
llm = get_model(settings.DEFAULT_MODEL)

# Message State
class SupervisorState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    collected_information: str
    job_description: Optional[str]
    questions: Optional[List[str]]
    next_node_to_invoke: str
    prev_question : str
    current_node : str
    node_decision : Optional[str]

# Structured Output Models
class IntentAnalysis(BaseModel):
    """Structured output for the Intent Agent."""
    collected_information: str = Field(
        description="Merged summary of company_name, role, experience, skills, location, etc."
    )
    next_question_to_ask: Optional[str] = Field(
        description="Polite one-line question for the next missing attribute, or ask for additional info if all are filled. Null if user says proceed/stop."
    )
    node_decision: Literal["incomplete", "complete"] = Field(
        description="'incomplete' if attributes missing or confirming extras, 'complete' if all info filled and confirmed."
    )
    current_node: Literal["invoke_intent"] = Field(
        description="Always 'invoke_intent' for this agent."
    )

class JDAnalysis(BaseModel):
    job_description: str = Field(description="The generated, professional job description.")
    node_decision: Literal["incomplete", "complete"] = Field(
        description="'incomplete' if awaiting feedback or revisions, 'complete' if JD is confirmed."
    )
    current_node: Literal["invoke_jd"] = Field(description="Always 'invoke_jd'.")
    next_question_to_ask: Optional[str] = Field(
        description="A polite one-line question asking for JD feedback, or null if approved."
    )

class QuestionsAnalysis(BaseModel):
    questions: List[str] = Field(
        description="A clean numbered list of exactly 10 technical pre-screening questions."
    )
    current_node: Literal["invoke_questions"] = Field(
        description="Must always be 'invoke_questions'."
    )
    node_decision: Literal["incomplete", "complete"] = Field(
        description="'incomplete' if waiting for feedback, 'complete' if user approves."
    )
    next_question_to_ask: Optional[str] = Field(
        description="A polite one-line question asking for JD feedback, or null if approved."
    )


class RouteDecision(BaseModel):
    next_node: Literal["invoke_intent", "invoke_jd", "invoke_questions", "END"]

# Structured LLMs
intent_analyzer_llm = llm.with_structured_output(IntentAnalysis)
router_llm = llm.with_structured_output(RouteDecision)
jd_llm = llm.with_structured_output(JDAnalysis)
question_llm = llm.with_structured_output(QuestionsAnalysis)

# Supervisor agent
def supervisor_agent(state: SupervisorState) -> dict:

    """This node is the supervisor's brain. It decides the next step at the start of each turn."""

    user_input = _latest_user_text(state)
    current_node = state.get("current_node", "")
    node_decision = state.get("node_decision", "")
    
    supervisor_prompt = PromptTemplate(
        input_variables=["user_input", "current_node", "node_decision"],
        template="""
        You are the Supervisor Agent managing a recruitment workflow.
        Your job is to decide the next node to execute at the start of each turn.

        ### Workflow Sequence ###
        invoke_intent -> invoke_jd -> invoke_questions -> END

        ### Routing Rules ###
        1. If 'current_node' is empty or not provided, the first node to call is 'invoke_intent'.
        2. If 'node_decision' is "incomplete", the next node must be the 'current_node' to continue gathering information or feedback.
        3. If 'node_decision' is "complete", the next node is the one that follows 'current_node' in the sequence.
        4. After 'invoke_questions' is "complete", the next node is "END".

        ### Current State ###
        - User Input: {user_input}
        - Current Node: {current_node}
        - Node Decision: {node_decision}

        ### Output (JSON only) ###
        {{"next_node": "<invoke_intent | invoke_jd | invoke_questions | END>"}}
        """
    )
    prompt = supervisor_prompt.format(user_input=user_input, current_node=current_node, node_decision=node_decision)
    decision: RouteDecision = router_llm.invoke(prompt)
    return {
        "next_node_to_invoke": decision.next_node
    }

# Router Function
def route_logic(state: SupervisorState) -> str:
    """The routing logic that directs the graph to the next worker node or ends the process."""
    return state["next_node_to_invoke"]

# Helper Function
def _latest_user_text(state: SupervisorState) -> str:
    for m in reversed(state["messages"]):
        if isinstance(m, HumanMessage):
            return m.content
    return ""

# Intent Agent(Collects data from hiring manager)
def invoke_intent(state: SupervisorState) -> dict:
    """Intent Agent: Collects user requirements for the job description."""

    prev_question = state.get("prev_question", "")
    collected_information = state.get("collected_information", "")
    user_input = _latest_user_text(state)

    analysis_prompt = PromptTemplate(
    input_variables=["prev_question", "user_input", "collected_information"],
    template="""
    You are the Intent Agent, a professional and methodical information gatherer for a recruitment supervisor agent. Your mission is to systematically collect all necessary details for a job role from a hiring manager.

    ### Core Mission ###
    Your process is divided into two main phases:
    1.  **Mandatory Collection:** Systematically ask for each required attribute until all are filled or refused.
    2.  **Optional Collection Loop:** Once all mandatory attributes are handled, enter a confirmation loop for additional details.

    ### Mandatory Attributes (in order) ###
    [company_name, role, skills, experience, mode_of_work, location]

    ### Operational Scenarios (Follow these rules STRICTLY) ###

    --- Phase 1: Mandatory Collection ---
    1.  **Condition:** One or more Mandatory Attributes are still missing from `collected_information` and have not been refused.
        - **Action:** Identify the NEXT missing attribute from the list. Extract any relevant information from the `user_input` and merge it.
        - **Output:**
            - `node_decision`: "incomplete"
            - `next_question_to_ask`: A polite, single-line question for the identified missing attribute (e.g., "What is the primary location for this role?").

    --- Transition to Phase 2 ---
    2.  **Condition:** All Mandatory Attributes have been collected or refused (i.e., the `user_input` provided the final missing piece, or the user refused the last remaining question).
        - **Action:** Merge the final piece of information if provided.
        - **Output:**
            - `node_decision`: "incomplete"
            - `next_question_to_ask`: "Great, I have the core details. Would you like to add any other information, such as salary, benefits, or specific responsibilities? (Yes/No)"

    --- Phase 2: Optional Collection Loop ---
    **Condition for all following scenarios: All Mandatory Attributes are present or have been marked as refused.**

    3.  **User Confirms "No" (Approval):**
        - **Condition:** The `prev_question` was a confirmation question AND the `user_input` has a clear "No" intent (e.g., "no", "that's all", "proceed").
        - **Action:** The information collection is complete.
        - **Output:**
            - `node_decision`: "complete"
            - `next_question_to_ask`: null

    4.  **User Confirms "Yes" (Wants to add more):**
        - **Condition:** The `prev_question` was a confirmation question AND the `user_input` has a clear "Yes" intent (e.g., "yes", "I have more").
        - **Action:** Prepare to receive the new information.
        - **Output:**
            - `node_decision`: "incomplete"
            - `next_question_to_ask`: "Excellent. Please provide the additional information you'd like to include."

    5.  **User Provides Optional Information:**
        - **Condition:** The `prev_question` was asking for additional info AND the `user_input` contains that new information.
        - **Action:** Merge the new optional details into `collected_information`.
        - **Output:**
            - `node_decision`: "incomplete"
            - **Crucially, you MUST return to the confirmation step.** Ask: "I've added that information. Is there anything else you'd like to add? (Yes/No)"

    ### General Rules ###
    - **Handling User Refusals:** If a user's response indicates they cannot or will not provide an answer for an attribute (e.g., "none", "not applicable", "skip"), you MUST record that attribute's value as "Not Provided" in `collected_information` and never ask for it again.
    - **Data Integrity:** Do not overwrite existing data unless the user explicitly asks for an update.
    - **Greeting:** Always greet the user back if their first message is a greeting.

    ### Output JSON Schema (MUST be valid JSON) ###
    {{
        "collected_information": "<updated string summary of all details>",
        "next_question_to_ask": "<the exact one-line question to ask the user, or null>",
        "node_decision": "<incomplete | complete>",
        "current_node": "invoke_intent"
    }}

    --- CONTEXT ---
    Current Collected Information: {collected_information}
    Previous Question Asked: {prev_question}
    Latest User Input: {user_input}
    """
    )
    
    analysis: IntentAnalysis = intent_analyzer_llm.invoke(analysis_prompt.format(
        prev_question=prev_question,
        collected_information=collected_information,
        user_input=user_input
    ))

    display_summary = f"**Collected Information:**\n```\n{analysis.collected_information}\n```"

    if analysis.node_decision == "incomplete":
        response_content = f"{analysis.next_question_to_ask}\n\n{display_summary}"
    else:
        response_content = f"✅ Great, I have all the required details.\n\n{display_summary}\n\nI will now proceed with drafting the job description. Click 'Ok to continue'"

    return {
        "collected_information": analysis.collected_information,
        "current_node": analysis.current_node,
        "node_decision": analysis.node_decision,
        "prev_question" : analysis.next_question_to_ask,
        "messages": [AIMessage(content=response_content)]
    }

# Job Description agent (Generated job description based on collected information)
def invoke_jd(state: SupervisorState) -> dict:

    """JD Agent: Generates or refines a job description."""
    
    previous_jd = state.get("job_description", "")
    user_input = _latest_user_text(state)

    jd_prompt = PromptTemplate(
    input_variables=["collected_information", "user_input", "previous_job_description"],
    template="""
    You are the JD Agent, an expert in crafting compelling job descriptions and managing a precise, multi-turn feedback loop with a user.

    ### JD Generation Quality Standards ###
    When generating or revising a JD, you MUST:
    1.  **Use Your Brain:** Do not just list the raw facts from `collected_information`. Infer standard responsibilities and skills implied by the role to create a complete picture.
    2.  **Be Creative & Professional:** The tone should be engaging, professional, and candidate-friendly.
    3.  **Follow a Strict Structure:** The JD must be organized into these sections:
        - Job Title
        - Company Overview (a brief, engaging paragraph if company name is known)
        - Key Responsibilities (bullet points)
        - Required Skills & Qualifications (bullet points)
        - Preferred Qualifications (optional, but good to include)
        - Location & Work Model

    ### Core Conversational Flow ###
    Generate -> Confirm (Yes/No) -> Get Edits -> Revise -> Re-confirm (Yes/No)

    ### Operational Scenarios (Follow these rules STRICTLY) ###

    --- Initial Generation ---
    1.  **Condition:** `previous_job_description` is empty.
        - **IMPORTANT:** In this scenario, you MUST IGNORE the `Latest User Input`. It is not relevant to the initial draft.
        - **Action:** Craft a new, high-quality JD from `collected_information` following all "JD Generation Quality Standards".
        - **Output:**
            - `node_decision`: "incomplete"
            - `next_question_to_ask`: "Here is a draft of the job description. Do you want to make any changes? (Yes/No)"

    --- Feedback Loop ---
    **Condition for all following scenarios: `previous_job_description` is NOT empty.** Now, you must analyze the `Latest User Input`.

    2.  **User Confirms "No" (Approval):**
        - **Condition:** The `user_input` has a clear "No" intent (e.g., "no", "it's good", "proceed", "looks perfect", "no changes").
        - **Action:** Keep the `previous_job_description` as the final version.
        - **Output:**
            - `node_decision`: "complete"
            - `next_question_to_ask`: null

    3.  **User Confirms "Yes" (Wants to make changes):**
        - **Condition:** The `user_input` has a clear "Yes" intent (e.g., "yes", "I want to make changes", "I have feedback").
        - **Action:** Keep the `previous_job_description` unchanged for now.
        - **Output:**
            - `node_decision`: "incomplete"
            - `next_question_to_ask`: "Understood. Can you please share the information to be updated?"

    4.  **User Provides Specific Edits:**
        - **Condition:** The `user_input` contains specific instructions for changes (e.g., "add Python to the skills", "change the title to Senior Engineer").
        - **Action:** Analyze the user_input properly and Incorporate the user's feedback into the `previous_job_description` to create a new, revised JD, adhering to the Quality Standards.
        - **Output:**
            - `node_decision`: "incomplete"
            - **Crucially, you MUST return to the confirmation step.** Ask: "I've updated the JD with your changes. Do you want to make any further changes? (Yes/No)"

    ### Output JSON Schema (MUST be valid JSON) ###
    {{
      "job_description": "<The new, revised, or existing JD>",
      "node_decision": "<incomplete | complete>",
      "current_node": "invoke_jd",
      "next_question_to_ask": "<The exact question to ask the user, or null if complete>"
    }}

    --- CONTEXT ---
    Collected Information: {collected_information}
    Previous Job Description: {previous_job_description}
    Latest User Input: {user_input}
    """
    )

    jd_analysis: JDAnalysis = jd_llm.invoke(
        jd_prompt.format(
            collected_information=state.get("collected_information"),
            user_input=user_input,
            previous_job_description=previous_jd
        )
    )

    jd_display = f"📝 **Job Description Draft:**\n\n{jd_analysis.job_description}"

    if jd_analysis.node_decision == "incomplete":
        # If the process is incomplete, we must ask the next question.
        message_text = f"{jd_display}\n\n{jd_analysis.next_question_to_ask}"
    else:
        # If the process is complete, we confirm and state the next step.
        message_text = f"{jd_display}\n\n✅ Great! The job description is approved. Moving on to screening questions. Click 'Ok to continue'"

    return {
        "job_description": jd_analysis.job_description,
        "messages": [AIMessage(content=message_text)],
        "current_node": "invoke_jd",
        "node_decision": jd_analysis.node_decision,
    }

# Questioning Agent (Generate screening questions based on job description)
def invoke_questions(state: SupervisorState) -> dict:
    """
    Question Agent: Generates technical screening questions, asks for confirmation,
    and refines them based on user feedback.
    """
    # Get previous questions from state to make the prompt context-aware.
    previous_questions = state.get("questions", [])
    user_input = _latest_user_text(state)

    questions_prompt = PromptTemplate(
        input_variables=["job_description", "user_input", "previous_questions"],
        template="""
        You are the Question Generation Agent, an expert at creating precise technical screening questions and managing a feedback loop with a user.

        ### Quality Standards for Questions ###
        1.  **Strictly Technical:** Generate exactly 10 questions. No HR, behavioral, or soft-skill questions.
        2.  **Directly Relevant:** Each question must be derived from the skills, technologies, or responsibilities listed in the `job_description`.
        3.  **Clear and Concise:** Questions should be unambiguous and professional.

        ### Core Conversational Flow ###
        Generate -> Confirm (Yes/No) -> Get Edits -> Revise -> Re-confirm (Yes/No)

        ### Operational Scenarios (Follow these rules STRICTLY) ###

        --- Initial Generation ---
        1.  **Condition:** `previous_questions` is empty.
            - **IMPORTANT:** In this scenario, you MUST IGNORE the `Latest User Input`.
            - **Action:** Generate a new list of 10 high-quality technical questions based on the `job_description`, following all Quality Standards.
            - **Output:**
                - `node_decision`: "incomplete"
                - `next_question_to_ask`: "Here are 10 proposed technical screening questions. Do you want to make any changes?(Yes/No)"

        --- Feedback Loop ---
        **Condition for all following scenarios: `previous_questions` is NOT empty.** Now, you must analyze the `Latest User Input`.

        2.  **User Confirms "No" (Approval):**
            - **Condition:** The `user_input` has a clear "No" intent (e.g., "no", "they are good", "approved", "proceed").
            - **Action:** Keep the `previous_questions` list as the final version.
            - **Output:**
                - `node_decision`: "complete"
                - `next_question_to_ask`: null

        3.  **User Confirms "Yes" (Wants to make changes):**
            - **Condition:** The `user_input` has a clear "Yes" intent (e.g., "yes", "I want changes").
            - **Action:** Keep the `previous_questions` list unchanged for now.
            - **Output:**
                - `node_decision`: "incomplete"
                - `next_question_to_ask`: "Understood. Can you please share the specific changes you'd like to make?"

        4.  **User Provides Specific Edits:**
            - **Condition:** The `user_input` contains specific instructions (e.g., "change question 5", "add a question about Kubernetes", "remove the one about SQL").
            - **Action:** Revise the `previous_questions` list to incorporate the user's feedback, ensuring the final list still has exactly 10 questions.
            - **Output:**
                - `node_decision`: "incomplete"
                - **Crucially, you MUST return to the confirmation step.** Ask: "I've updated the questions based on your feedback. Do you want to make any further changes? (Yes/No)"

        ### Output JSON Schema (MUST be valid JSON) ###
        {{
          "questions": ["Q1...", "Q2...", "... up to Q10"],
          "node_decision": "<incomplete | complete>",
          "current_node": "invoke_questions"
        }}

        --- CONTEXT ---
        Job Description: {job_description}
        Previous Questions: {previous_questions}
        Latest User Input: {user_input}
        """
    )

    analysis: QuestionsAnalysis = question_llm.invoke(questions_prompt.format(
        job_description=state["job_description"],
        user_input=user_input,
        previous_questions=previous_questions,
    ))

    display_questions = "\n".join(f"{ref_no+1} {question}" for ref_no, question in enumerate(analysis.questions))

    if analysis.node_decision == "complete":
        response_content = (
            f"✅ Great! The screening questions are approved.\n\n"
            f"\n**Finalized Job Description:**\n{state['job_description']}\n\n"
            f"\n**Finalized Questions:**\n{display_questions}\n\n"
            "\nThis concludes our session."
        )
    else: # incomplete
        # The LLM will have already generated the correct follow-up question.
        follow_up_question = "Do these look good, or would you like me to refine them? (Yes/No)"
        if "please share the information" in analysis.next_question_to_ask.lower():
             follow_up_question = "Understood. Can you please share the information to be updated?"
        elif "further changes" in analysis.next_question_to_ask.lower():
            follow_up_question = "I've updated the questions. Do you want to make any further changes? (Yes/No)"

        response_content = (
            f"Here are the current screening questions:\n\n{display_questions}\n\n"
            f"{follow_up_question}"
        )

    return {
        "questions": analysis.questions,
        "current_node": analysis.current_node,
        "node_decision": analysis.node_decision,
        "messages": [AIMessage(content=response_content)],
    }


# Graph Assembly
graph_builder = StateGraph(SupervisorState)

# Nodes
graph_builder.add_node("supervisor_agent", supervisor_agent)
graph_builder.add_node("invoke_intent", invoke_intent)
graph_builder.add_node("invoke_jd", invoke_jd)
graph_builder.add_node("invoke_questions", invoke_questions)

# Edges
graph_builder.set_entry_point("supervisor_agent")
graph_builder.add_conditional_edges("supervisor_agent", route_logic, {
    "invoke_intent": "invoke_intent",
    "invoke_jd": "invoke_jd",
    "invoke_questions": "invoke_questions",
    "END": END,
})
graph_builder.add_edge("invoke_intent", END)
graph_builder.add_edge("invoke_jd", END)
graph_builder.add_edge("invoke_questions", END)

# Compile the Agent
# The checkpointer will be added by the service, making the graph stateful.
supervisor_agent = graph_builder.compile()