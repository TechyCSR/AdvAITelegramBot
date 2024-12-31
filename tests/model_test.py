
from g4f.client import Client as GPTClient
from g4f.cookies import set_cookies

# Initialize the GPT-4 client



gpt_client = GPTClient(provider="Mhystical")

history = []
history.append({"role": "system", "content": "Hello! I am GPT-4, a chatbot."})

ok ="Blackbox"

def get_response(ask):
        
        response = gpt_client.chat.completions.create(
                model="gpt-4o-mini",
            messages=history + [{"role": "user", "content": ask}],
        )
        history.append({"role": "system", "content": response.choices[0].message.content})
        return response.choices[0].message.content
    


while True:
        ask=input("You: ")
        ans=get_response(ask)
        print("AI: ",ans)
        print()

