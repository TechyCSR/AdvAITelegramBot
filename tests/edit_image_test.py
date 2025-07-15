import asyncio
from g4f.client import AsyncClient
from g4f.Provider import PollinationsAI

async def main():
    client = AsyncClient(image_provider=PollinationsAI)

    response = await client.images.create_variation(
        image=open("./generated_images/1749042674_create+a+variation+of+this+image_5047378b1f6674cd.jpeg", "rb"),
        model="flux",
        # prompt="add a lion to the right side of the given image",
    )

    image_url = response.data[0].url
    print(f"Generated image URL: {image_url}")

asyncio.run(main())