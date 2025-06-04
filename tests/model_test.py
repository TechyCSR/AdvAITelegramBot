
from g4f.client import Client as GPTClient
from g4f.cookies import set_cookies

# Initialize the GPT-4 client

str="""
Qwen/Qwen3-235B-A22B Done

"""

gpt_client = GPTClient(provider="LegacyLMArena")

history = []
history.append({"role": "system", "content": "Hello! I a  chatbot."})


def get_response(ask):
        
        response = gpt_client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=history + [{"role": "user", "content": ask}],
        )
        history.append({"role": "system", "content": response.choices[0].message.content})
        return response.choices[0].message.content
    


while True:
        ask=input("You: ")
        ans=get_response(ask)
        print("AI: ",ans)
        print()

