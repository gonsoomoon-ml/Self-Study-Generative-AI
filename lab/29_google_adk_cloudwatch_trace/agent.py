"""Multi-turn Google ADK agent used to verify CloudWatch tracing via OpenInference + ADOT.

Run it under the ADOT launcher (see run.sh):
    opentelemetry-instrument python agent.py --session-id <id>

What this exercises for Knox Q2(a):
  * openinference-instrumentation-google-adk emits CHAIN/AGENT/LLM/TOOL spans.
  * session.id / user.id are taken from the *keyword* arguments of Runner.run_async,
    so every turn below passes them as keywords on purpose.
  * Three turns reuse one session_id, so CloudWatch should group them into one session.
"""

import argparse
import asyncio
import os

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

APP_NAME = "knox-adk-trace-test"
MODEL = os.environ.get("ADK_MODEL", "gemini-3.8-flash")


def get_weather(city: str) -> dict:
    """Return a canned weather report for a city (test tool, no network call)."""
    table = {
        "seoul": {"city": "Seoul", "temp_c": 14, "condition": "clear"},
        "suwon": {"city": "Suwon", "temp_c": 13, "condition": "cloudy"},
    }
    return table.get(city.lower(), {"city": city, "temp_c": 20, "condition": "unknown"})


def build_agent() -> Agent:
    return Agent(
        name="knox_trace_test_agent",
        model=MODEL,
        description="Tiny travel helper used only to generate traces.",
        instruction=(
            "You are a concise travel helper. Use the get_weather tool when asked "
            "about weather. Keep answers under 40 words. Remember what the user "
            "told you earlier in the conversation."
        ),
        tools=[get_weather],
    )


# Turn 2 deliberately contains fake PII so the masking variant (run B) has
# something visible to redact. The values are synthetic.
TURNS = [
    "Hi, my name is Gildong Hong and my phone number is 010-1234-5678. "
    "I am planning a trip to Seoul next week.",
    "What is the weather like in Seoul right now?",
    "Thanks. What was my name and phone number again, and which city did I ask about?",
]


async def run_conversation(session_id: str, user_id: str) -> None:
    runner = InMemoryRunner(agent=build_agent(), app_name=APP_NAME)
    await runner.session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )

    for i, text in enumerate(TURNS, start=1):
        print(f"\n=== turn {i} (session_id={session_id}) ===")
        print(f"user> {text}")
        message = types.Content(role="user", parts=[types.Part(text=text)])
        # Keyword arguments are required: the OpenInference ADK wrapper reads
        # kwargs['session_id'] and kwargs['user_id'] to set session.id / user.id.
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=message
        ):
            if event.is_final_response() and event.content and event.content.parts:
                reply = "".join(p.text or "" for p in event.content.parts)
                print(f"agent> {reply.strip()}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--user-id", default="knox-test-user")
    args = parser.parse_args()
    asyncio.run(run_conversation(args.session_id, args.user_id))


if __name__ == "__main__":
    main()
