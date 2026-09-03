import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from config import TEMPERATURE

load_dotenv()

llm = ChatOpenAI(
    api_key=os.getenv("api_key"),
    model=os.getenv("model", "openai/gpt-oss-120b:free"),
    base_url=os.getenv("base_url"),
    temperature=TEMPERATURE,
)


def ask_llm(system_prompt: str, history: list) -> str:
    messages = [SystemMessage(content=system_prompt)]

    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    response = llm.invoke(messages)
    return response.content

#流式输出
def ask_llm_stream(system_prompt: str, history: list):
    messages = [SystemMessage(content=system_prompt)]

    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    for chunk in llm.stream(messages):
        content = chunk.content

        if isinstance(content, str) and content:
            yield content




# 绘制图片
def draw_image(system_prompt: str, history: list) -> str:
    messages = [SystemMessage(content=system_prompt)]

    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    response = llm.invoke(messages)
    return response.content
