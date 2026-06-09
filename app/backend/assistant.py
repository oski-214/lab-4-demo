"""
Copilot SDK Assistant Module

Manages the CopilotClient lifecycle and provides streaming assistant functionality
for the High School Activities API.
"""

import asyncio
from typing import AsyncGenerator

from copilot import CopilotClient
from copilot.session import PermissionHandler
from copilot.generated.session_events import SessionEventType
from copilot.tools import define_tool
from pydantic import BaseModel, Field

# Import the real activities dict from the main app
from backend.app import activities

# Global client instance (lazy initialization)
_client: CopilotClient | None = None
_client_lock = asyncio.Lock()


async def get_client() -> CopilotClient:
    """Get or create the CopilotClient instance (lazy initialization)."""
    global _client
    async with _client_lock:
        if _client is None:
            _client = CopilotClient()
            await _client.start()
        return _client


async def stop_client() -> None:
    """Stop the CopilotClient if it's running."""
    global _client
    async with _client_lock:
        if _client is not None:
            await _client.stop()
            _client = None


# --- Tool Definitions ---

@define_tool(description="List every activity with schedule and spots left.")
async def list_activities() -> list[dict]:
    """Return all activities with their details and availability."""
    return [
        {
            "name": name,
            "description": data["description"],
            "schedule": data["schedule"],
            "spots_left": data["max_participants"] - len(data["participants"]),
        }
        for name, data in activities.items()
    ]


class RegisterKidParams(BaseModel):
    name: str = Field(
        description="The kid's name or email, e.g. 'Maya' or 'maya@githubcopilot.edu'."
    )
    activity: str = Field(
        description="Exact activity name, e.g. 'Chess Club'."
    )


@define_tool(
    description="Sign a kid up for one activity. Returns a confirmation, "
                "or an error message if the activity does not exist."
)
async def register_kid(params: RegisterKidParams) -> str:
    """Register a student for an activity."""
    if params.activity not in activities:
        available = ", ".join(activities.keys())
        return f"Error: no activity named {params.activity!r}. Available: {available}."
    
    activities[params.activity]["participants"].append(params.name)
    return f"Signed up {params.name} for {params.activity}."


# --- Streaming Response Generator ---

async def stream_answer(prompt: str) -> AsyncGenerator[str, None]:
    """
    Stream assistant responses as an async generator.
    
    Yields text chunks as they arrive from the SDK, suitable for SSE streaming.
    """
    client = await get_client()
    
    session = await client.create_session(
        on_permission_request=PermissionHandler.approve_all,
        model="gpt-4.1",
        tools=[list_activities, register_kid],
        streaming=True,
    )

    done = asyncio.Event()
    chunks: asyncio.Queue[str | None] = asyncio.Queue()

    def handle_event(event) -> None:
        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            chunks.put_nowait(event.data.delta_content)
        elif event.type == SessionEventType.SESSION_IDLE:
            chunks.put_nowait(None)  # Signal completion
            done.set()

    session.on(handle_event)

    # Start sending the prompt
    send_task = asyncio.create_task(session.send_and_wait(prompt))

    # Yield chunks as they arrive
    while True:
        chunk = await chunks.get()
        if chunk is None:
            break
        yield chunk

    # Ensure send task completes
    await send_task
