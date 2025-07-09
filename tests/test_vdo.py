from g4f.client import Client
import g4f.Provider

client = Client(
    provider=g4f.Provider.Video,  # No API key required for this provider
)

video_models = client.models.get_video()
print(video_models)  # e.g., ['search', 'sora']

result = client.media.generate(
    model=video_models[0],  # 'search' or 'sora'
    prompt="A futuristic city with flying cars.",
    response_format="url"
)

print(result.data[0].url)