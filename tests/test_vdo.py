import os
import time
from g4f.client import AsyncClient
import g4f.Provider
import asyncio

video_gen = True  # Set to False to disable video generation

if video_gen:

    from google import genai
    from google.genai.types import GenerateVideosConfig

    # Ensure environment variables are set externally or here
    # os.environ["GOOGLE_CLOUD_PROJECT"] = "your-project-id"
    # os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    # os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

    client = genai.Client()

    # TODO: Update this with your actual GCS bucket URI
    output_gcs_uri = "gs://techycsr/test_vdo_output"

    operation = client.models.generate_videos(
        model="veo-3.0-generate-preview",
        prompt="a cat studying naturally",
        config=GenerateVideosConfig(
            aspect_ratio="16:9",
            output_gcs_uri=output_gcs_uri,
        ),
    )

    while not operation.done:
        time.sleep(15)
        operation = client.operations.get(operation)
        print(operation)

    if operation.response:
        video_uri = operation.result.generated_videos[0].video.uri
        print(video_uri)

        # Download the video from GCS and save locally
        from google.cloud import storage
        import re

        # Extract bucket and blob name from the URI
        match = re.match(r'gs://([^/]+)/(.+)', video_uri)
        if match:
            bucket_name, blob_name = match.groups()
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.download_to_filename('generated_images/generated_video.mp4')
            print('Video downloaded and saved as generated_video.mp4')
        else:
            print('Failed to parse GCS URI:', video_uri)
else:
    print("Video generation is disabled (video_gen is False)")