from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(model="gpt-5-nano", temperature=0, verbosity="low", reasoning_effort="minimal")

system_prompt = SystemMessage(content="You are a helpful assistant.")

def generate_response(user_input, history):
  history_msgs = []
  
  for msg in history:
    if msg.sender == "human":
      history_msgs.append(HumanMessage(content=msg.text))
    elif msg.sender == "ai":
      history_msgs.append(AIMessage(content=msg.text))

  history_msgs.append(HumanMessage(content=user_input))

  prompt = ChatPromptTemplate.from_messages([system_prompt] + history_msgs)

  chain = prompt | llm | StrOutputParser()

  return chain.invoke({})