import asyncio
from strands import Agent
from strands.multiagent.a2a import A2AAgent

async def main():
    # Create a basic agent
    agent = Agent(name="AI assistant", description="A helpful AI assistant")

    # Wrap it with A2A capabilities
    a2a_agent = A2AAgent(agent=agent)

    # Start the A2A server
    print("Starting A2A server on http://localhost:9000")
    await a2a_agent.serve()

if __name__ == "__main__":
    asyncio.run(main())