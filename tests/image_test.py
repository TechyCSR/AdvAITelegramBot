# from g4f.client import Client
# from g4f.Provider import PollinationsImage
# import base64
# client = Client(
#     image_provider=PollinationsImage
# )

# response = client.images.generate(
#     model="flux-pro",
#     prompt="a white siamese cat",
#     response_format="b64_json"
# )

# base64_text = response.data[0].b64_json

# with open("image.png", "wb") as f:
#     f.write(base64.b64decode(base64_text))


# print(f"Generated image URL: {base64_text}")

import asyncio
from g4f.client import AsyncClient
from g4f.Provider import PollinationsImage

async def main():
    client = AsyncClient(
        image_provider=PollinationsImage
    )
    
    response = await client.images.generate(
        prompt="a white girl with blue eyes",
        model="flux-pro",
        response_format="url"
        # Add any other necessary parameters
    )
    
    image_url = response.data[0].url
    print(f"Generated image URL: {image_url}")

asyncio.run(main())