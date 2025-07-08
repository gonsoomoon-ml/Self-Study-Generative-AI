from strands import Agent
from strands_tools import swarm

# Create an agent with swarm capability
agent = Agent(tools=[swarm])

# Process a complex task with multiple agents in parallel
result = agent.tool.swarm(
    # task="Analyze this dataset and identify market trends in korean",
    
    task="서울의 여름에 와이프, 고1, 중2 남자 아들과 같이 여행 장소와 계획을 세워줘",
    swarm_size=4,
    coordination_pattern="collaborative"
)

# The result contains contributions from all swarm agents
print(result["content"])