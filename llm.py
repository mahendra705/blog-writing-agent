from langchain_google_genai import ChatGoogleGenerativeAI

from config import GEMINI_CHAT_MODEL

_chat_model: ChatGoogleGenerativeAI | None = None


def _get_chat_model() -> ChatGoogleGenerativeAI:
    global _chat_model
    if _chat_model is None:
        _chat_model = ChatGoogleGenerativeAI(
            model=GEMINI_CHAT_MODEL,
            temperature=0.7,
        )
    return _chat_model
