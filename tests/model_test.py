from g4f.client import Client

client = Client()
response = client.chat.completions.create(
    model="gpt-5",
    messages=[{"role": "user", "content": "Explain the theory of relativity in simple terms."}],
    web_search=False
)
print(response.choices[0].message.content)