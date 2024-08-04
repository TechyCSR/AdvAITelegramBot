
# making new  features for it  :

import os
import requests
from g4f.client import Client
from g4f.Provider import BingCreateImages
from g4f.cookies import set_cookies
import random


COOKIES = [
    "1-7f5gYThNbKgdNojOXHHoXMJpxPY4jWyDaQ5aoKbUM5uZXWizWY0SuVABgNF4v9GgihUJwq99UQbVJV2X1U0LWvyRLYcF1NiXgCuuH6zQXV3lmHlA5HKlXSdK-KfjzMf1q_mckrehIhfgJ7tLxc1R1lVgHrnEHQmxBRUW8w8_fhgaAJKNjWRb11LKr3D2qmoL9Mp_TvaTcM04KNOTMrCdw",
    # " ",
    # " ",
    # " ",
    # "  ",
    #add more cookies here
     
]

def get_random_cookie():
    return random.choice(COOKIES)

def generate_and_save_images(prompt, download_folder, max_images=3):
    generated_images = 0
    total_attempts = 0
    max_attempts = len(COOKIES) * 2   #it will generate 2 images form 1 cookie , change it to 3 if necessary 

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

             
            if not os.path.exists(download_folder):
                os.makedirs(download_folder)

         
            for i, image_data in enumerate(response.data):
                image_url = image_data.url
                image_response = requests.get(image_url)
                
                if image_response.status_code == 200:
                    image_path = os.path.join(download_folder, f"image_{generated_images + 1}.jpg")
                    with open(image_path, "wb") as file:
                        file.write(image_response.content)
                    print(f"Image saved to {image_path}")
                    generated_images += 1
                    
                    if generated_images >= max_images:
                        break
                else:
                    print(f"Failed to download image {generated_images + 1}")

        except Exception as e:
            print(f"Error with current cookie: {str(e)}")

        total_attempts += 1

    if generated_images < max_images:
        print(f"Warning: Only generated {generated_images} out of {max_images} requested images.")

 
while True:
    try:
        download_folder = os.path.expanduser("~/Downloads")   
        generate_and_save_images(input("Your Prompt: "), download_folder)
    except Exception as e:
        print("Error:", str(e))
