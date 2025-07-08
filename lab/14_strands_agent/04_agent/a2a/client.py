import asyncio
from uuid import uuid4

import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import MessageSendParams, SendMessageRequest


async def ask_agent(message: str):
    async with httpx.AsyncClient() as httpx_client:
        # Connect to the agent
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url="http://localhost:9000")

        agent_card = await resolver.get_agent_card()
        print(agent_card)
        client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

        # Send the message
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(
                message={
                    "role": "user",
                    "parts": [{"kind": "text", "text": message}],
                    "messageId": uuid4().hex,
                }
            ),
        )

        return await client.send_message(request)


# Example usage
async def main():
    message = "Tell me about agentic AI"
    response = await ask_agent(message)
    print(response.model_dump(mode="json", exclude_none=True))


if __name__ == "__main__":
    asyncio.run(main())