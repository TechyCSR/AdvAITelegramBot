import time
import os
from google import genai
from google.genai.types import GenerateVideosConfig, Image
from google.cloud import storage

# Set up your environment variables before running this script
# os.environ["GOOGLE_CLOUD_PROJECT"] = "your-project-id"
# os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
# os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

client = genai.Client()

# Local image to use
local_image_path = "generated_images/1747214000_e807590f-a3cb-4d62-9eea-298c754853e7.jpg"  # Change as needed
bucket_name = "techycsr"
gcs_image_blob = "test_vdo_input/image.png"
output_gcs_uri = "gs://techycsr/test_vdo_output"

# Upload local image to GCS
def upload_image_to_gcs(local_path, bucket_name, blob_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(local_path)
    return f"gs://{bucket_name}/{blob_name}"

gcs_image_uri = upload_image_to_gcs(local_image_path, bucket_name, gcs_image_blob)

start_time = time.time()
operation = client.models.generate_videos(
    prompt="all studing naturally",
    model="veo-3.0-generate-preview",
    image=Image(
        gcs_uri=gcs_image_uri,
        mime_type="image/png",
    ),
    config=GenerateVideosConfig(
        aspect_ratio="16:9",
        output_gcs_uri=output_gcs_uri,
    ),
)

while not operation.done:
    time.sleep(15)
    operation = client.operations.get(operation)
    print(operation)

total_time = time.time() - start_time
print(f"Video generation took {total_time:.2f} seconds.")

if operation.response:
    video_uri = operation.result.generated_videos[0].video.uri
    print(video_uri)

    # Download the video from GCS and save locally
    import re
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