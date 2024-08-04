
# added new features :

# the generate/edit/quit feature
# max 3 image generation
# give the url of the images instead of saving them directly to save storage
# multiple cookies to remove any delay or restrictions (it chooses randomly)

# under load testing.................

import os
from g4f.client import Client
from g4f.Provider import BingCreateImages
from g4f.cookies import set_cookies
import random

COOKIES = [
    "1-7f5gYThNbKgdNojOXHHoXMJpxPY4jWyDaQ5aoKbUM5uZXWizWY0SuVABgNF4v9GgihUJwq99UQbVJV2X1U0LWvyRLYcF1NiXgCuuH6zQXV3lmHlA5HKlXSdK-KfjzMf1q_mckrehIhfgJ7tLxc1R1lVgHrnEHQmxBRUW8w8_fhgaAJKNjWRb11LKr3D2qmoL9Mp_TvaTcM04KNOTMrCdw",
    # Add more cookies here
]

def get_random_cookie():
    return random.choice(COOKIES)

 
message_prompts = {}

def generate_images(prompt, max_images=3):
    generated_images = 0
    total_attempts = 0
    max_attempts = len(COOKIES) * 2
    image_urls = []

    while generated_images < max_images and total_attempts < max_attempts:
        set_cookies(".bing.com", {
            "_U": get_random_cookie()
        })

        client = Client(image_provider=BingCreateImages)

        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                n=max_images - generated_images 
            )

            for image_data in response.data:
                image_urls.append(image_data.url)
                generated_images += 1
                
                if generated_images >= max_images:
                    break

        except Exception as e:
            print(f"Error with current cookie: {str(e)}")

        total_attempts += 1

    if generated_images < max_images:
        print(f"Warning: Only generated {generated_images} out of {max_images} requested images.")

    return image_urls

def edit_image(message_id, edit_prompt):
    if message_id in message_prompts:
        original_prompt = message_prompts[message_id]
        new_prompt = f"{original_prompt}. Edit: {edit_prompt}"
        return generate_images(new_prompt, max_images=1)[0]
    else:
        return "Message ID not found."

 
while True:
    command = input("Enter command (generate/edit/quit): ").lower()
    
    if command == 'generate':
        prompt = input("Your Prompt: ")
        urls = generate_images(prompt)
        message_id = random.randint(1000, 9999)  # Simulating a message ID
        message_prompts[message_id] = prompt
        print(f"Generated images (Message ID: {message_id}):")
        for url in urls:
            print(url)
    
    elif command == 'edit':
        message_id = int(input("Enter the Message ID of the image to edit: "))
        edit_prompt = input("Enter edit instructions: ")
        new_url = edit_image(message_id, edit_prompt)
        print(f"Edited image URL: {new_url}")
    
    elif command == 'quit':
        break
    
    else:
        print("Invalid command. Please use 'generate', 'edit', or 'quit'.")
