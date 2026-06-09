import asyncio
from copy import deepcopy

from copilot import CopilotClient
from copilot.session import PermissionHandler
from copilot.generated.session_events import SessionEventType
from copilot.tools import define_tool
from pydantic import BaseModel, Field


activities: dict[str, dict] = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
}


@define_tool(description="List every activity with schedule and spots left.")
async def list_activities() -> list[dict]:
    return [
        {
            "name": name,
            "description": d["description"],
            "schedule": d["schedule"],
            "spots_left": d["max_participants"] - len(d["participants"]),
        }
        for name, d in activities.items()
    ]


class RegisterKidParams(BaseModel):
    name: str = Field(description="The kid's name or email, e.g. 'Maya' or 'maya@mergington.edu'.")
    activity: str = Field(description="Exact activity name, e.g. 'Chess Club'.")


@define_tool(
    description="Sign a kid up for one activity. Returns a confirmation, "
                "or an error message if the activity does not exist."
)
async def register_kid(params: RegisterKidParams) -> str:
    if params.activity not in activities:
        available = ", ".join(activities.keys())
        return f"Error: no activity named {params.activity!r}. Available: {available}."
    activities[params.activity]["participants"].append(params.name)
    return f"Signed up {params.name} for {params.activity}."


async def main() -> None:
    before = deepcopy(activities)
    client = CopilotClient()
    await client.start()
    try:
        session = await client.create_session(
            on_permission_request=PermissionHandler.approve_all,
            model="gpt-4.1",
            tools=[list_activities, register_kid],
            streaming=True,
        )

        done = asyncio.Event()

        def handle_event(event) -> None:
            if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
                print(event.data.delta_content, end="", flush=True)
            elif event.type == SessionEventType.SESSION_IDLE:
                done.set()

        session.on(handle_event)

        print("Type a message and press Enter. h Type 'quit' to exit.\n")
        while True:
            try:
                prompt = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not prompt:
                continue
            if prompt.lower() in {"quit", "exit"}:
                break

            done.clear()
            print("assistant> ", end="", flush=True)
            send_task = asyncio.create_task(session.send_and_wait(prompt))
            await done.wait()
            await send_task
            print("\n")
    finally:
        await client.stop()

    print("--- Participants before vs. after ---")
    for name in activities:
        print(f"{name}:")
        print(f"  before: {before[name]['participants']}")
        print(f"  after : {activities[name]['participants']}")


if __name__ == "__main__":
    asyncio.run(main())