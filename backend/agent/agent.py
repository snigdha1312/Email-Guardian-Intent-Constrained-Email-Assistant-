import os
import asyncio
from typing import Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
import dotenv

# Load environment variables (e.g. API keys from .env if present)
dotenv.load_dotenv()

async def _run_agent_async(user_message: str, identity: str) -> str:
    """Helper async function to run the LangChain agent connected to the MCP server."""
    # Find backend absolute path to configure subprocess correctly
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    # Configure STDIO parameters to spawn the MCP server script
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", os.path.join(backend_dir, "mcp_server/server.py")],
        env={
            "PYTHONPATH": backend_dir,
            **os.environ
        }
    )
    
    # Connect to the MCP server via stdio
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Automatically load and convert MCP tools to LangChain tools
            tools = await load_mcp_tools(session)
            
            # Choose LLM based on available keys. Prefer Anthropic, fallback to OpenAI.
            if os.environ.get("ANTHROPIC_API_KEY"):
                llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0)
            else:
                # Default fallback (OpenAI will raise an error if key is missing when invoked)
                llm = ChatOpenAI(model="gpt-4o", temperature=0)
            
            # Instruct the agent with the system prompt, dynamically binding the active identity
            system_prompt = (
                "You are an email assistant. Summarize inboxes, draft replies, and only send, archive, or "
                f"schedule when explicitly asked. Always pass identity='{identity}' when calling any tool "
                "that requires an identity."
            )
            
            # Create a ReAct agent using langgraph prebuilt template
            agent = create_react_agent(
                model=llm,
                tools=tools,
                state_modifier=system_prompt
            )
            
            # Run agent with the user query
            result = await agent.ainvoke({
                "messages": [HumanMessage(content=user_message)]
            })
            
            # Get and return the final text response from the agent
            messages = result.get("messages", [])
            if messages:
                return messages[-1].content
            return "No response received from agent."

def run_agent(user_message: str, identity: str = "primary_user") -> str:
    """
    Runs the email assistant agent synchronously.
    Takes a natural language request, plans/calls tools, and returns a response.
    """
    return asyncio.run(_run_agent_async(user_message, identity))
