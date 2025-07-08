from strands import Agent, tool
from strands_tools import retrieve, http_request

# Define a specialized system prompt
RESEARCH_ASSISTANT_PROMPT = """
You are a specialized research assistant. Focus only on providing
factual, well-sourced information in response to research questions.
Always cite your sources when possible.
"""

@tool
def research_assistant(query: str) -> str:
    """
    Process and respond to research-related queries.

    Args:
        query: A research question requiring factual information

    Returns:
        A detailed research answer with citations
    """
    print(f"🔍 Research Assistant 호출됨: {query}")
    try:
        # Strands Agents SDK makes it easy to create a specialized agent
        research_agent = Agent(
            system_prompt=RESEARCH_ASSISTANT_PROMPT,
            tools=[retrieve, http_request]  # Research-specific tools
        )

        # Call the agent and return its response
        response = research_agent(query)
        print(f"✅ Research Assistant 응답 완료")
        return str(response)
    except Exception as e:
        print(f"❌ Research Assistant 오류: {str(e)}")
        return f"Error in research assistant: {str(e)}"
    
@tool
def product_recommendation_assistant(query: str) -> str:
    """
    Handle product recommendation queries by suggesting appropriate products.

    Args:
        query: A product inquiry with user preferences

    Returns:
        Personalized product recommendations with reasoning
    """
    print(f"🛍️ Product Recommendation Assistant 호출됨: {query}")
    try:
        product_agent = Agent(
            system_prompt="""You are a specialized product recommendation assistant.
            Provide personalized product suggestions based on user preferences.""",
            tools=[retrieve, http_request],  # Tools for getting product data
        )
        # Implementation with response handling
        # ...
        processed_response = "Product recommendation response"  # 임시 응답
        print(f"✅ Product Recommendation Assistant 응답 완료")
        return processed_response
    except Exception as e:
        print(f"❌ Product Recommendation Assistant 오류: {str(e)}")
        return f"Error in product recommendation: {str(e)}"

@tool
def trip_planning_assistant(query: str) -> str:
    """
    Create travel itineraries and provide travel advice.

    Args:
        query: A travel planning request with destination and preferences

    Returns:
        A detailed travel itinerary or travel advice
    """
    print(f"✈️ Trip Planning Assistant 호출됨: {query}")
    try:
        travel_agent = Agent(
            system_prompt="""You are a specialized travel planning assistant.
            Create detailed travel itineraries based on user preferences.""",
            tools=[retrieve, http_request],  # Travel information tools
        )
        # Implementation with response handling
        # ...
        processed_response = "Trip planning response"  # 임시 응답
        print(f"✅ Trip Planning Assistant 응답 완료")
        return processed_response
    except Exception as e:
        print(f"❌ Trip Planning Assistant 오류: {str(e)}")
        return f"Error in trip planning: {str(e)}"    