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

from tools.vision_tools import browse_url, take_screenshot_base64, click_coordinates, type_text_at_coordinates, move_mouse
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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
    region_name = "us-east-2", #"us-east-1", # Ensure AWS_REGION is set
    #model_kwargs={'temperature': 0.2}
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
                content="""You are a helpful assistant and can use tools to perform actions on my chromium browser.

For the very first task, you will use the navigate_to function to open the specified webpage.

To open apps, move the mouse over the center of the app icon and single-click.

If you want to press a key more than once, join them together with a '+'.

I like you to refresh the google page every time you start a new task (after the first one). Also, if possible, always work on a new tab.

After each action, check the screen to ensure the action had the intended effect. Do not assume completion until verified.

Be careful when selecting menu items—look first, move the mouse carefully, then click.

Before writing text, ensure the cursor is in the correct location. Always look at the screen before performing any action.

Also, ensure when trying to look for downloading users data, like a lot of users, look for options like organizations, team members, etc. As these pages usually have all the user data there.

Also, when interacting with dropdowns, always use a tab to reach the dropdown field, use the space bar to open the dropdown, use arrow keys to constantly move around the dropdown. When each element gets highlighted, take a screenshot to verify if it's the one you are looking for. Once you reach the element you look for, press Enter to select the value.

To look for the update button, go for Ctrl+F, type 'update' in it."""
            ),
            #MessagesPlaceholder(variable_name="chat_history", optional=True),
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
        response = await agent_executor.ainvoke(
            input=formatted_prompt_messages[0].content
        )
        return response
    except Exception as e:
        print(f"Error during agent execution: {e}")
        raise e
    finally:
        pass