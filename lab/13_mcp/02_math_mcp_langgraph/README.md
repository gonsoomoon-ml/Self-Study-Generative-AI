# Creating an MCP Server and Integrating with LangGraph
- https://medium.com/@sajith_k/creating-an-mcp-server-and-integrating-with-langgraph-5f4fa434a4c7

이 폴더는 위의 블로그의 코드를 Amazon Bedrock 으로 구현을 했습니다.
아래는 각 파일 실행 결과를 보여 주고 있습니다.

## math_client_mcp.py  실행시

- 
```
python math_server_mcp.py 먼저 실행 후에 
아래 실행

(mcp) moongons@bcd074660793 02_math_mcp_langgraph % python math_client_mcp.py
Processing request of type ListPromptsRequest

/////////////////prompts//////////////////
name='example_prompt' description='Example prompt description' arguments=[PromptArgument(name='question', description=None, required=True)]
name='system_prompt' description='System prompt description' arguments=[]
Processing request of type ListResourcesRequest

/////////////////resources//////////////////
uri=AnyUrl('config://app') name='get_config' description='Static configuration data' mimeType='text/plain' size=None annotations=None
Processing request of type ListResourceTemplatesRequest

/////////////////resource_templates//////////////////
uriTemplate='greeting://{name}' name='get_greeting' description='Get a personalized greeting' mimeType=None annotations=None
Processing request of type ListToolsRequest

/////////////////tools//////////////////
name='add' description='Add two numbers' inputSchema={'properties': {'a': {'title': 'A', 'type': 'integer'}, 'b': {'title': 'B', 'type': 'integer'}}, 'required': ['a', 'b'], 'title': 'addArguments', 'type': 'object'} annotations=None
name='multiply' description='Multiply two numbers' inputSchema={'properties': {'a': {'title': 'A', 'type': 'integer'}, 'b': {'title': 'B', 'type': 'integer'}}, 'required': ['a', 'b'], 'title': 'multiplyArguments', 'type': 'object'} annotations=None
Processing request of type GetPromptRequest

/////////////////prompt//////////////////

    You are a math assistant. Answer the question.
    Question: what is 2+2
    
Processing request of type ReadResourceRequest

/////////////////content//////////////////
Hello, Alice!
Processing request of type CallToolRequest

/////////////////result//////////////////
4
```
## math_client_langgraph_mcp.py  실행시
- LLM에 MCP 툴을 바인딩하여, LLM이 툴을 직접 사용할 수 있게 함

```
(mcp) moongons@bcd074660793 02_math_mcp_langgraph % python math_client_langgraph_mcp.py
Processing request of type ListToolsRequest
Available tools: ['add', 'multiply']
Processing request of type GetPromptRequest
Available prompts: ['\n    You are a math assistant. Answer the question.\n    Question: what is 2+2\n    ']
Processing request of type GetPromptRequest
Available prompts: ['\n    You are an AI assistant use the tools if needed.\n    ']
Processing request of type ReadResourceRequest
Processing request of type ReadResourceRequest
Available resources: ['Hello, Alice!', 'App configuration here']
Processing request of type ListToolsRequest
Processing request of type GetPromptRequest
system_prompt from load_mcp_prompt:
 [HumanMessage(content='\n    You are an AI assistant use the tools if needed.\n    ', additional_kwargs={}, response_metadata={})]
prompt_template from ChatPromptTemplate:
 input_variables=['messages'] input_types={'messages': list[typing.Annotated[typing.Union[typing.Annotated[langchain_core.messages.ai.AIMessage, Tag(tag='ai')], typing.Annotated[langchain_core.messages.human.HumanMessage, Tag(tag='human')], typing.Annotated[langchain_core.messages.chat.ChatMessage, Tag(tag='chat')], typing.Annotated[langchain_core.messages.system.SystemMessage, Tag(tag='system')], typing.Annotated[langchain_core.messages.function.FunctionMessage, Tag(tag='function')], typing.Annotated[langchain_core.messages.tool.ToolMessage, Tag(tag='tool')], typing.Annotated[langchain_core.messages.ai.AIMessageChunk, Tag(tag='AIMessageChunk')], typing.Annotated[langchain_core.messages.human.HumanMessageChunk, Tag(tag='HumanMessageChunk')], typing.Annotated[langchain_core.messages.chat.ChatMessageChunk, Tag(tag='ChatMessageChunk')], typing.Annotated[langchain_core.messages.system.SystemMessageChunk, Tag(tag='SystemMessageChunk')], typing.Annotated[langchain_core.messages.function.FunctionMessageChunk, Tag(tag='FunctionMessageChunk')], typing.Annotated[langchain_core.messages.tool.ToolMessageChunk, Tag(tag='ToolMessageChunk')]], FieldInfo(annotation=NoneType, required=True, discriminator=Discriminator(discriminator=<function _get_type at 0x10411a200>, custom_error_type=None, custom_error_message=None, custom_error_context=None))]]} partial_variables={} messages=[SystemMessagePromptTemplate(prompt=PromptTemplate(input_variables=[], input_types={}, partial_variables={}, template='\n    You are an AI assistant use the tools if needed.\n    '), additional_kwargs={}), MessagesPlaceholder(variable_name='messages')]
User: 오늘 저녁 무엇을 먹을까?
AI: 오늘 저녁 메뉴를 고민하고 계시군요. 집에 있는 재료들을 활용해 간단하면서도 맛있는 요리를 해보는 것은 어떨까요? 예를 들어 밥과 함께 나물무침이나 계란후라이 등을 곁들이면 간단하면서도 든든한 한끼가 될 수 있습니다. 또는 면요리나 간단한 스테이크 등 본인의 기호에 맞는 메뉴를 선택하셔도 좋겠습니다. 건강하고 맛있는 식사 되시길 바랍니다!
User: 3 + 3
Processing request of type CallToolRequest
AI: 3 + 3 = 6 입니다.
User: 10 / 2
Processing request of type CallToolRequest
AI: 제공된 도구로는 10을 2로 나누는 계산을 할 수 없는 것 같습니다. 정수 곱셈만 가능한 것으로 보입니다. 나눗셈 계산은 직접 해야 할 것 같네요. 10 / 2 = 5 입니다.
```