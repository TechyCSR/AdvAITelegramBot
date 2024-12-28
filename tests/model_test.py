
from g4f.client import Client as GPTClient
from g4f.cookies import set_cookies

BING_COOKIE ="12xSAr0O1VL29oRLlW4rPVBdlrD2FPtxsUOfbQCOKY-lSxHoNpFK9K0ksvtffUyNeQHgDXQlV4vSDUzP_M26FEEtAJIHU_j97WYirCpGcYT_AKIaIUQYfETPZLQB779hHw-pftDthZ7vfHWk2L7kNM5d5ZsGiGKhGFEctA4tBDhgZMlGwTXDJTsWkUBwtOzDzfOGkg22iD_QcDC0oZLxUlA"
# Initialize the GPT-4 client

gpt_client = GPTClient()

# Set Bing cookie
set_cookies(".bing.com", {
    "_U": "you.com.har"
})


def get_response(ask):
        
        response = gpt_client.chat.completions.create(
                model="gpt-4o-mini",
            messages=[{"role": "user", "content": ask}]
        )
        return response.choices[0].message.content
    


while True:
        ask=input("You: ")
        ans=get_response(ask)
        print("AI: ",ans)
        print()

