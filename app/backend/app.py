"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at GitHub Copilot High School.
"""

from contextlib import asynccontextmanager
from html import escape
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
import os
from pathlib import Path


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - cleanup SDK client on shutdown."""
    yield
    # Shutdown: stop the Copilot client
    from backend.assistant import stop_client
    await stop_client()


app = FastAPI(
    title="GitHub Copilot High School API",
    description="API for viewing and signing up for extracurricular activities",
    lifespan=lifespan,
)

# Mount the static files directory (frontend)
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(current_dir.parent,
          "frontend")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@githubcopilot.edu", "daniel@githubcopilot.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@githubcopilot.edu", "sophia@githubcopilot.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@githubcopilot.edu", "olivia@githubcopilot.edu"]
    }
}


def get_open_spots(activity):
    """Return the number of remaining spots for a single activity."""
    return max(activity["max_participants"] - len(activity["participants"]), 0)


def render_activities_page():
    """Render a plain HTML page listing every activity and its open spots."""
    activity_cards = []

    for name, activity in activities.items():
        activity_cards.append(
            f"""
            <article class="activity-card">
              <h4>{escape(name)}</h4>
              <p>{escape(activity["description"])}</p>
              <p><strong>Schedule:</strong> {escape(activity["schedule"])}</p>
              <p><strong>Spots open:</strong> {get_open_spots(activity)}</p>
            </article>
            """
        )

    return f"""
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>School Activities</title>
        <link rel="stylesheet" href="/static/styles.css" />
      </head>
      <body>
        <header>
          <h1>GitHub Copilot High School</h1>
          <h2>School Activities</h2>
        </header>
        <main>
          <section class="activities-overview">
            <h3>Available Activities</h3>
            {''.join(activity_cards)}
          </section>
        </main>
      </body>
    </html>
    """


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/activities/view", response_class=HTMLResponse)
def activities_view():
    return render_activities_page()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.post("/assistant/stream")
async def assistant_stream(request: Request):
    """
    Stream assistant responses via Server-Sent Events (SSE).
    
    Accepts JSON body with a "prompt" field and returns a text/event-stream
    response with the assistant's answer streamed chunk by chunk.
    """
    from backend.assistant import stream_answer

    body = await request.json()
    prompt = body.get("prompt", "")

    async def event_generator():
        async for chunk in stream_answer(prompt):
            # SSE format: data: <content>\n\n
            yield f"data: {chunk}\n\n"
        # Signal end of stream
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
