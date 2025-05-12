import chainlit as cl
import os
from agents import Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI, set_tracing_disabled
from dotenv import load_dotenv
import asyncio
from typing import Optional,Dict

load_dotenv()
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY")
GITHUB_CLIENT_ID=os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET=os.getenv("GITHUB_CLIENT_SECRET")

provider = AsyncOpenAI(
    api_key=GEMINI_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/",
)

@cl.password_auth_callback
async def login(username:str, password:str)->Optional[cl.User]:
    if (username,password)==("Ali1@gmail.com","55445"):
        return cl.User(identifier="admin", metadata={"role":"admin"})
    return None

@cl.oauth_callback
async def github_login(provider_id:str, token:str, raw_user_data:Dict[str,str], default_user:cl.User)-> Optional[cl.User]:
    print(f"logging into the github","="*9)
    print(f"provider_id,{provider_id}")
    print(f"token,{token}")
    print(f"raw_user_data,{raw_user_data}")

    try:
        return default_user
    except Exception as e:
        print(f"login failed:{e}")
        return None
    
@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("history",[])
    await cl.Message(content="Hi there, I am John your STUDY assistant").send()

@cl.on_message
async def on_message(message: cl.Message):
    if "continue without an account" in message.content.lower():
        await cl.Message(content="You must login to continue with your assistant..").send()
        return
    history=cl.user_session.get("history")
    history.append({"role":"user", "content": message.content})

    agent= Agent(
        name="Study Assistant",
        instructions=("You are a study assistant that answers every study related problem efficiently and solves those problems"
        "You should also answer implementation in real life questions"
        "You should be sensitive if someone is sad not able to solve questions first you should make him feel better then answer those questions"
        ),
        model=OpenAIChatCompletionsModel(model="gemini-1.5-flash", openai_client=provider),
    )

    try:
       
        result =Runner.run_streamed(agent, input=history)
     
        # Stream the response token by token
        async for event in result.stream_events():
            if event.type == "raw_response_event" and hasattr(event.data, 'delta'):
                token = event.data.delta
                await message.stream_token(token)
                await asyncio.sleep(0.08)
        
        message.content = result.final_output
        await message.update()
        
        history.append({"role": "assistant", "content": result.final_output})
        cl.user_session.set("history", history)
        
    except Exception as e:
        await cl.Message(content=f"Error occurred while running the response: {str(e)}").send()

    full_history="\n".join([f"{m['role'].capitalize()}: {m['content'][:55].strip()}....."for m in history])
    await cl.Message(content=f"History:{full_history}").send()