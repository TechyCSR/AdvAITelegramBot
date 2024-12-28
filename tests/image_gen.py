import requests

def gen_url(long_url):
    api_key = "2e24fbb817a0375cc5e501a0779a1a28"
    endpoint = f"https://api.imgbb.com/1/upload?expiration=600&key={api_key}"
    response = requests.post(endpoint, files={"image": (None, long_url)})
    data = response.json()
    print(data)

print(gen_url("1735353475_fc731afc-b5da-45a6-8899-f117b5842ca9.jpg"))