from typing import Literal, Any
from pydantic import BaseModel, Field
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.types import Command
from langgraph.graph.message import add_messages
from langgraph.graph import START, StateGraph, END
from langgraph.prebuilt import create_react_agent
from typing_extensions import TypedDict, Annotated

from prompt_library.prompt import system_prompt
from utils.llms import LLMModel
from toolkit.toolkits import (
    check_availability_by_doctor,
    check_availability_by_specialization,
    set_appointment,
    cancel_appointment,
    reschedule_appointment,
)


# ─── Router: Pydantic BaseModel (required for Groq structured output) ─────────
# Groq does NOT support TypedDict with with_structured_output — must use BaseModel.

class Router(BaseModel):
    next: Literal["information_node", "booking_node", "FINISH"] = Field(
        description="Which worker to route to next, or FINISH if the query is resolved."
    )
    reasoning: str = Field(
        description="Brief explanation of why this routing decision was made."
    )


# ─── Agent state (TypedDict is fine here — only Router needs BaseModel) ───────

class AgentState(TypedDict):
    messages: Annotated[list[Any], add_messages]
    id_number: int
    next: str
    query: str
    current_reasoning: str


# ─── Agent ────────────────────────────────────────────────────────────────────

class DoctorAppointmentAgent:
    def __init__(self):
        llm_model = LLMModel()
        self.llm_model = llm_model.get_model()

    # ── Supervisor ────────────────────────────────────────────────────────────

    def supervisor_node(
        self, state: AgentState
    ) -> Command[Literal['information_node', 'booking_node', '__end__']]:
        print("── supervisor_node ──")

        # Build message list: system prompt + id context + conversation
        messages = (
            [SystemMessage(content=system_prompt)]
            + [HumanMessage(content=f"User's identification number is {state['id_number']}")]
            + list(state["messages"])
        )

        query = state['messages'][0].content if len(state['messages']) == 1 else ''

        try:
            response: Router = self.llm_model.with_structured_output(Router).invoke(messages)
            goto = response.next
            reasoning = response.reasoning
        except Exception as exc:
            print(f"Supervisor structured-output error: {exc}")
            # Safe fallback: route to information node so user gets some response
            goto = "information_node"
            reasoning = f"Fallback due to routing error: {exc}"

        print(f"supervisor → {goto} | {reasoning}")

        if goto == "FINISH":
            goto = END

        if query:
            return Command(
                goto=goto,
                update={
                    'next': str(goto),
                    'query': query,
                    'current_reasoning': reasoning,
                    'messages': [HumanMessage(content=f"User's identification number is {state['id_number']}")]
                }
            )
        return Command(
            goto=goto,
            update={'next': str(goto), 'current_reasoning': reasoning}
        )

    # ── Information Node ──────────────────────────────────────────────────────

    def information_node(self, state: AgentState) -> Command[Literal['__end__']]:
        print("── information_node ──")

        info_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "You are a specialized agent providing information about doctor availability "
                    "and hospital FAQs. Use the available tools to answer queries.\n"
                    "Ask the user politely if you need more details to call a tool.\n"
                    "Today's date is 03-04-2026 (DD-MM-YYYY)."
                )
            ),
            ("placeholder", "{messages}"),
        ])

        try:
            information_agent = create_react_agent(
                model=self.llm_model,
                tools=[check_availability_by_doctor, check_availability_by_specialization],
                prompt=info_prompt,
            )

            result = information_agent.invoke(state)

            return Command(
                update={
                    "messages": [
                        AIMessage(content=result["messages"][-1].content, name="information_node")
                    ],
                    "next": "END"
                },
                goto=END,
            )
        except Exception as e:
            print("❌ information_node error:", e)
            return Command(
                update={
                    "messages": [
                        AIMessage(content="Something went wrong while retrieving information.", name="information_node")
                    ],
                    "next": "END"
                },
                goto=END,
            )

    # ── Booking Node ──────────────────────────────────────────────────────────

    def booking_node(self, state: AgentState) -> Command[Literal['__end__']]:
        print("── booking_node ──")

        booking_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "You are a specialized agent for booking, cancelling, and rescheduling "
                    "doctor appointments. Use the available tools.\n"
                    "Ask the user politely if you need more details to call a tool.\n"
                    "Today's date is 03-04-2026 (DD-MM-YYYY).\n"
                    "After a successful booking or cancellation, always tell the user "
                    "that a confirmation email has been sent to them."
                )
            ),
            ("placeholder", "{messages}"),
        ])

        try:
            booking_agent = create_react_agent(
                model=self.llm_model,
                tools=[set_appointment, cancel_appointment, reschedule_appointment],
                prompt=booking_prompt,
            )

            result = booking_agent.invoke(state)

            return Command(
                update={
                    "messages": [
                        AIMessage(content=result["messages"][-1].content, name="booking_node")
                    ],
                    "next": "END"
                },
                goto=END,
            )
        except Exception as e:
            print("❌ booking_node error:", e)
            return Command(
                update={
                    "messages": [
                        AIMessage(content="Something went wrong while processing the booking.", name="booking_node")
                    ],
                    "next": "END"
                },
                goto=END,
            )

    # ── Build Graph ───────────────────────────────────────────────────────────

    def workflow(self):
        graph = StateGraph(AgentState)
        graph.add_node("supervisor", self.supervisor_node)
        graph.add_node("information_node", self.information_node)
        graph.add_node("booking_node", self.booking_node)
        graph.add_edge(START, "supervisor")
        self.app = graph.compile()
        return self.app