from g4f.client import Client
from g4f.Provider import PollinationsImage
import base64
client = Client(
    image_provider=PollinationsImage
)

response = client.images.generate(
    model="flux-pro",
    prompt="a white siamese cat",
    response_format="b64_json"
)

base64_text = response.data[0].b64_json

with open("image.png", "wb") as f:
    f.write(base64.b64decode(base64_text))


print(f"Generated image URL: {base64_text}")