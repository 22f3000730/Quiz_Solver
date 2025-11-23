from agno.agent import Agent
from agno.models.openai.chat import OpenAIChat
from agno.db.sqlite.sqlite import SqliteDb
import os
from dotenv import load_dotenv
from tools import download_file_as_base64, fetch_page_text, transcribe_audio, run_python_code
import logging

logger = logging.getLogger(__name__)

load_dotenv()

def get_agent():
    api_key = os.getenv("AI_TOKEN")
    if not api_key:
        logger.error("AI_TOKEN is missing from environment variables!")
        raise ValueError("AI_TOKEN not found in environment variables")
    
    logger.info(f"AI_TOKEN loaded. Length: {len(api_key)}")
    logger.info(f"AI_TOKEN prefix: {api_key[:10]}...")
    
    # Set env var just in case
    os.environ["OPENROUTER_API_KEY"] = api_key
    
    # Initialize the agent with OpenRouter model via custom endpoint
    agent = Agent(
        model=OpenAIChat(
            base_url="https://aipipe.org/openrouter/v1",
            api_key=api_key,
            id="google/gemini-2.0-flash-lite-001"
        ),
        description="You are a helpful assistant that solves data-related quiz tasks.",
        instructions=[
            "You will be given a task description, often involving data analysis or web scraping.",
            "You need to solve the task and provide the answer.",
            "The answer should be in the format requested by the task.",
            "If you need to download a file, use the `download_file_as_base64` tool.",
            "Be concise and accurate."
        ],
        tools=[download_file_as_base64, fetch_page_text, transcribe_audio, run_python_code],
        markdown=True,
        debug_mode=True,
        db=SqliteDb(db_file="agent_memory.db"),
        add_history_to_context=True
    )
    return agent
