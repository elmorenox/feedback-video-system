# src/services/dialogue/chains.py
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
from src.settings import settings
from src.logging_config import app_logger


def create_chat_model() -> ChatOpenAI:
    """Initialize ChatGPT model"""
    app_logger.debug("creating chat model")
    return ChatOpenAI(
        temperature=0,
        model_name="gpt-4o",
        api_key=settings.OPENAI_API_KEY
    )


def create_script_chain() -> LLMChain:
    """Create chain for script generation"""
    app_logger.debug("Creating ")
    chat: ChatOpenAI = create_chat_model()
    app_logger.debug("Returning LLMChain")
    return LLMChain(
        llm=chat,
        prompt=ChatPromptTemplate.from_messages([
            ("system", "You are a script generator for educational feedback videos."),
            ("human", "{prompt}"),
            ("human", "{grading_data}")
        ])
    )
