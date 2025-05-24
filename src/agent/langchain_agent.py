import os
import asyncio
from typing import List, Dict, Any, Optional

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI # CORRECTED IMPORT
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.tools import BaseTool, tool
from langchain_anthropic import ChatAnthropic
from langchain_aws.chat_models import ChatBedrock
from langchain.tools import StructuredTool

from vision_tools import browse_url, take_screenshot_base64, click_coordinates, type_text_at_coordinates, move_mouse
from config import EXTERNAL_LLM_API_KEY, EXTERNAL_LLM_MODEL_NAME
from langchain.agents.structured_chat.base import StructuredChatAgent
from langchain.agents import AgentType, initialize_agent

async def run_agent_executor_task(
    prompt_messages: List[Dict[str, Any]],
    external_llm_model_name: str = EXTERNAL_LLM_MODEL_NAME,
    external_llm_api_key: str = EXTERNAL_LLM_API_KEY,
) -> str:

    # llm = ChatGoogleGenerativeAI(
    #     model=external_llm_model_name,
    #     google_api_key=external_llm_api_key,
    #     temperature=0.0
    # )

    llm= ChatBedrock(
    model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0",  # Replace with your desired Claude model
    credentials_profile_name="splunk-dev",
    region_name = "us-east-1", #"us-east-1", # Ensure AWS_REGION is set
    model_kwargs={'temperature': 0.2}
)
#     llm=ChatAnthropic(
#     model="claude-3-5-haiku-latest",
#     max_tokens=1024,
#     api_key="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" # Set this in your .env file
# ) 

  
    
    # Define the tools using StructuredTool with coroutine support
    tools = [
        StructuredTool.from_function(
            func=browse_url,  # This is just for schema, not actually called
            name="browse_url",
            description="Navigates the browser to the specified URL. Returns a summary of the page content.",
            coroutine=browse_url,  # This is what gets called
            return_direct=False
        ),
        StructuredTool.from_function(
            func=take_screenshot_base64,
            name="take_screenshot_base64",
            description="Takes a full-page screenshot and returns it as a base64 encoded PNG string.",
            coroutine=take_screenshot_base64,
            return_direct=False
        ),
        StructuredTool.from_function(
            func=click_coordinates,
            name="click_coordinates",
            description="Clicks at the specified x, y coordinates on the page along with the type of click left or right.",
            coroutine=click_coordinates,
            return_direct=False
        ),
        StructuredTool.from_function(
            func=move_mouse,
            name="move_mouse",
            description="moves mouse to the specified x, y coordinates on the page",
            coroutine=move_mouse,
            return_direct=False
        ),
        StructuredTool.from_function(
            func=type_text_at_coordinates,
            name="type_text_at_coordinates",
            description="Types text into an element at the specified x, y coordinates on the page.",
            coroutine=type_text_at_coordinates,
            return_direct=False
        )
    ]

    # Create the agent with structured tools
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(
                content="You are a helpful AI agent that can interact with web pages and use tools to achieve your goals. "
                "Your primary method of interaction is by analyzing screenshots and providing precise x, y coordinates to the 'click_coordinates' and 'type_text_at_coordinates' tools. "
                "Always take a screenshot first to understand the current state of the page. "
                "When you identify an element (like an input field, button, or link), provide its estimated center x, y coordinates to the relevant tool."
            ),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            HumanMessage(content="{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )
    
    # Create the agent
    agent = StructuredChatAgent.from_llm_and_tools(
        llm=llm,
        tools=tools,
        prompt=prompt
    )
    
    
    # Create an async-compatible executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True
    )

    formatted_prompt_messages: List[BaseMessage] = []
    for msg in prompt_messages:
        if msg["role"] == "user":
            formatted_prompt_messages.append(HumanMessage(content=msg["parts"][0]["text"]))

    try:
        # Use arun instead of invoke for async execution
        response = await agent_executor.arun(
            input=formatted_prompt_messages[0].content
        )
        return response
    except Exception as e:
        print(f"Error during agent execution: {e}")
        raise e
    finally:
        pass