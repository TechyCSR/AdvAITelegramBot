from cryptography.fernet import Fernet
import os


def generate_key():
    key = Fernet.generate_key()
    os.environ['SECRET_KEY'] = key.decode()  
def load_key():
    key = os.environ.get('SECRET_KEY')
    if key is None:
        raise ValueError("No key found in environment variables")
    return key.encode()
def encrypt_message(message):
    key = load_key()
    f = Fernet(key)
    encrypted_message = f.encrypt(message.encode())
    return encrypted_message
def decrypt_message(encrypted_message):
    key = load_key()
    f = Fernet(key)
    decrypted_message = f.decrypt(encrypted_message).decode()
    return decrypted_message
if 'SECRET_KEY' not in os.environ:
    generate_key()
