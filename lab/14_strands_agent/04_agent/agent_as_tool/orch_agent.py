from strands import Agent
from specialized_agents import research_assistant, product_recommendation_assistant, trip_planning_assistant

# Define the orchestrator system prompt with clear tool selection guidance
MAIN_SYSTEM_PROMPT = """
You are an assistant that routes queries to specialized agents:
- For research questions and factual information → Use the research_assistant tool
- For product recommendations and shopping advice → Use the product_recommendation_assistant tool
- For travel planning and itineraries → Use the trip_planning_assistant tool
- For simple questions not requiring specialized knowledge → Answer directly

Always select the most appropriate tool based on the user's query.
"""

# Strands Agents SDK allows easy integration of agent tools
orchestrator = Agent(
    system_prompt=MAIN_SYSTEM_PROMPT,
    callback_handler=None,
    tools=[research_assistant, product_recommendation_assistant, trip_planning_assistant]
)

# Example: E-commerce Customer Service System
customer_query = "I'm looking for hiking boots for a trip to Patagonia next month in korean"

# The orchestrator automatically determines that this requires multiple specialized agents
response = orchestrator(customer_query)

# Behind the scenes, the orchestrator will:
# 1. First call the trip_planning_assistant to understand travel requirements for Patagonia
#    - Weather conditions in the region next month
#    - Typical terrain and hiking conditions
# 2. Then call product_recommendation_assistant with this context to suggest appropriate boots
#    - Waterproof options for potential rain
#    - Proper ankle support for uneven terrain
#    - Brands known for durability in harsh conditions
# 3. Combine these specialized responses into a cohesive answer that addresses both the
#    travel planning and product recommendation aspects of the query

print(response)