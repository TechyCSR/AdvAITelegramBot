import g4f
import g4f.Provider

def chat_completion(prompt):
    client = g4f.Client(provider=g4f.Provider.Blackbox)
    images = [
        [open("./generated_images/image.png","rb"), "image.png"]
    ]
    response = client.chat.completions.create([{"content": prompt, "role": "user"}],  images=images, model="gpt-4o")
    print(response.choices[0].message.content)

prompt = "what are on this images?"
chat_completion(prompt)