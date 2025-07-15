from g4f.client import AsyncClient
import g4f.Provider
import asyncio
client = AsyncClient(
    provider=g4f.Provider.Video,  # No API key required for this provider
)

video_models = client.models.get_video()
print(video_models)  # e.g., ['search', 'sora']

async def main():
    result = await client.media.generate(
        model=video_models[0],  # 'search' or 'sora'
        prompt="A flying car",
        response_format="url",
    )

    print(result.data[0].url)


if __name__ == "__main__":
    asyncio.run(main())