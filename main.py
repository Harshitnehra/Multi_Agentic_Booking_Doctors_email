import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

os.environ.pop("SSL_CERT_FILE", None)

app = FastAPI(title="MediAssist API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-load the agent once at startup (avoids re-init on every request)
_agent_instance = None
_executor = ThreadPoolExecutor(max_workers=4)


def _get_agent():
    global _agent_instance
    if _agent_instance is None:
        from agent import DoctorAppointmentAgent
        _agent_instance = DoctorAppointmentAgent()
    return _agent_instance


class UserQuery(BaseModel):
    id_number: int
    messages: str


def _run_agent(id_number: int, message: str):
    """Runs the LangGraph workflow synchronously — called in a thread pool."""
    agent = _get_agent()
    graph = agent.workflow()

    query_data = {
        "messages": [HumanMessage(content=message)],
        "id_number": id_number,
        "next": "",
        "query": "",
        "current_reasoning": "",
    }
    return graph.invoke(query_data, config={"recursion_limit": 20})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/execute")
async def execute_agent(user_input: UserQuery):
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            _executor,
            _run_agent,
            user_input.id_number,
            user_input.messages,
        )

        # ✅ SAFE CHECK
        if not response or "messages" not in response:
            return {
                "messages": [
                    {"role": "assistant", "content": "Sorry, something went wrong. Please try again."}
                ]
            }

        return {"messages": response["messages"]}

    except Exception as exc:
        print("❌ ERROR:", str(exc))   # <-- VERY IMPORTANT
        raise HTTPException(status_code=500, detail=str(exc))