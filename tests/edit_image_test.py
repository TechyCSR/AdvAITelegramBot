from g4f.client import Client
from g4f.Provider import PollinationsImage
import base64

client = Client(
    image_provider=PollinationsImage
)

response = client.images.create_variation(
    image=open("/home/csr/Documents/Git Projects/AdvAITelegramBot-6/generated_images/1747214000_e807590f-a3cb-4d62-9eea-298c754853e7.jpg", "rb"),
    model="dall-e-3",
    # Add any other necessary parameters
)

image_url = response.data[0].url

with open("image.png", "wb") as f:
    f.write(base64.b64decode(image_url))

print(f"Generated image URL: {image_url}")