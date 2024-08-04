
# added new features :

# the generate/edit/quit feature
# max 3 image generation
# give the url of the images instead of saving them directly to save storage
# multiple cookies to remove any delay or restrictions (it chooses randomly)

# under load testing.................


import os
import random
from g4f.client import Client
from g4f.Provider import BingCreateImages
from g4f.cookies import set_cookies
from config import BING_COOKIE, MAX_EDITS, MAX_IMAGES

 
message_data = {}

def generate_images(prompt, max_images=MAX_IMAGES):
    generated_images = 0
    total_attempts = 0
    max_attempts = 2  
    image_urls = []

    while generated_images < max_images and total_attempts < max_attempts:
        set_cookies(".bing.com", {
            "_U": BING_COOKIE
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
            print(f"Error generating image: {str(e)}")

        total_attempts += 1

    if generated_images < max_images:
        print(f"Warning: Only generated {generated_images} out of {max_images} requested images.")

    return image_urls

def edit_image(message_id, edit_prompt):
    if message_id in message_data:
        original_prompt, edit_count = message_data[message_id]
        if edit_count >= MAX_EDITS:
            return f"Edit limit reached. You cannot edit this image more than {MAX_EDITS} times."
        
        new_prompt = f"{original_prompt}. Edit: {edit_prompt}"
        edited_url = generate_images(new_prompt, max_images=1)[0]
        
        message_data[message_id] = (new_prompt, edit_count + 1)
        return edited_url
    else:
        return "Message ID not found."

 
while True:
    command = input("Enter command (generate/edit/quit): ").lower()
    
    if command == 'generate':
        prompt = input("Your Prompt: ")
        urls = generate_images(prompt)
        message_id = random.randint(1000, 9999)   
        message_data[message_id] = (prompt, 0)   
        print(f"Generated images (Message ID: {message_id}):")
        for url in urls:
            print(url)
    
    elif command == 'edit':
        message_id = int(input("Enter the Message ID of the image to edit: "))
        edit_prompt = input("Enter edit instructions: ")
        result = edit_image(message_id, edit_prompt)
        if result.startswith("http"):
            print(f"Edited image URL: {result}")
        else:
            print(result)
    
    elif command == 'quit':
        break
    
    else:
        print("Invalid command. Please use 'generate', 'edit', or 'quit'.")
