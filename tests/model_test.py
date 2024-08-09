
from g4f.client import Client as GPTClient

# Initialize the GPT-4 client
gpt_client = GPTClient(provider="HuggingChat")

def get_response(ask):
        

        response = gpt_client.chat.completions.create(
            model="mistralai/Mixtral-8x7B-Instruct-v0.1",
            messages=[{"role": "user", "content": ask}]
        )
        return response.choices[0].message.content
    


while True:
        ask=input("You: ")
        ans=get_response(ask)
        print("AI: ",ans)
        print()

