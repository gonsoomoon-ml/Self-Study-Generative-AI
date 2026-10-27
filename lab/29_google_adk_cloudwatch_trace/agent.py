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
from opentelemetry import trace
from opentelemetry.sdk.trace import SpanProcessor

APP_NAME = "knox-adk-trace-test"
MODEL = os.environ.get("ADK_MODEL", "gemini-3.8-flash")

# Experiment (COPY_SESSION_ID=1): ADK's native LLM spans (scope gcp.vertex.agent)
# carry gen_ai.conversation.id but not session.id, and CloudWatch's agent-level
# token totals showed 0. This processor stamps session.id/user.id on every span
# so we can see whether the aggregation keys on session.id.
_CURRENT = {"session_id": None, "user_id": None}


class SessionIdStamper(SpanProcessor):
    # Experiment 4 (COPY_ROOT_TOKENS=1): per-trace token sums copied onto the root span.
    _trace_tokens: dict = {}

    def on_start(self, span, parent_context=None):
        sid, uid = _CURRENT["session_id"], _CURRENT["user_id"]
        if sid and not span.attributes.get("session.id"):
            span.set_attribute("session.id", sid)
        if uid and not span.attributes.get("user.id"):
            span.set_attribute("user.id", uid)

    def _on_ending(self, span):
        # NOTE: the installed opentelemetry-sdk (1.44) names the hook `_on_ending`
        # (underscore) and calls it before the span is sealed, so attributes can still be set.
        # Experiment 2 (COPY_TOKEN_TOTAL=1): ADK's LLM span has gen_ai.usage.input_tokens /
        # output_tokens but no gen_ai.usage.total_tokens or gen_ai.system. Add them to see
        # whether the console's "Total tokens" aggregation keys on those.
        if os.environ.get("COPY_TOKEN_TOTAL") != "1":
            return
        a = span.attributes or {}
        i, o = a.get("gen_ai.usage.input_tokens"), a.get("gen_ai.usage.output_tokens")

        # Experiment 4: the root span (no parent) ends last; write the per-trace sums on it.
        if (
            os.environ.get("COPY_ROOT_TOKENS") == "1"
            and span.parent is None
            and span.context.trace_id in self._trace_tokens
        ):
            ti, to = self._trace_tokens.pop(span.context.trace_id)
            attrs = span._attributes  # noqa: SLF001
            was_immutable = getattr(attrs, "_immutable", False)
            try:
                attrs._immutable = False  # noqa: SLF001
                attrs["gen_ai.usage.input_tokens"] = ti
                attrs["gen_ai.usage.output_tokens"] = to
                attrs["gen_ai.usage.total_tokens"] = ti + to
                attrs["llm.token_count.prompt"] = ti
                attrs["llm.token_count.completion"] = to
                attrs["llm.token_count.total"] = ti + to
            finally:
                attrs._immutable = was_immutable  # noqa: SLF001
            print(f"[experiment] root span '{span.name}' stamped with tokens in={ti} out={to}")
            return

        if i is None or o is None:
            return
        if os.environ.get("COPY_ROOT_TOKENS") == "1":
            ti, to = self._trace_tokens.get(span.context.trace_id, (0, 0))
            self._trace_tokens[span.context.trace_id] = (ti + int(i), to + int(o))
        # The SDK marks attributes immutable right before _on_ending, so set_attribute()
        # is silently dropped here. Write through the underlying BoundedAttributes instead
        # (same trick the AWS data-protection doc uses for redaction in _on_ending).
        attrs = span._attributes  # noqa: SLF001
        was_immutable = getattr(attrs, "_immutable", False)
        try:
            attrs._immutable = False  # noqa: SLF001
            if "gen_ai.usage.total_tokens" not in a:
                attrs["gen_ai.usage.total_tokens"] = int(i) + int(o)
            if "gen_ai.system" not in a:
                attrs["gen_ai.system"] = a.get("gen_ai.provider.name", "gemini")
            # Experiment 3 (FAKE_BEDROCK=1): relabel the LLM span as a Bedrock model call to
            # test whether the console's token aggregation only counts recognised providers.
            # Diagnostic only; the call was still made to Gemini.
            if os.environ.get("FAKE_BEDROCK") == "1":
                model_id = os.environ.get("FAKE_BEDROCK_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
                attrs["gen_ai.system"] = "aws.bedrock"
                attrs["gen_ai.provider.name"] = "aws.bedrock"
                attrs["gen_ai.request.model"] = model_id
                attrs["gen_ai.response.model"] = model_id
                attrs["llm.model_name"] = model_id
                attrs["llm.provider"] = "aws"
        finally:
            attrs._immutable = was_immutable  # noqa: SLF001

    def on_end(self, span):
        pass

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis=None):
        return True


def install_session_stamper() -> None:
    provider = trace.get_tracer_provider()
    if hasattr(provider, "add_span_processor"):
        provider.add_span_processor(SessionIdStamper())
        print("[experiment] SessionIdStamper installed: session.id copied onto every span")
    else:
        print("[experiment] tracer provider has no add_span_processor; stamper not installed")


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
    _CURRENT["session_id"], _CURRENT["user_id"] = session_id, user_id
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
    if os.environ.get("COPY_SESSION_ID") == "1" or os.environ.get("COPY_TOKEN_TOTAL") == "1":
        install_session_stamper()
    asyncio.run(run_conversation(args.session_id, args.user_id))


if __name__ == "__main__":
    main()
