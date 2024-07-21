from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
import os

def create_key_pairs(public_key_file:str='public.pem', private_key_file:str='private.pem'):
    # Generate an RSA key pair
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    public_key = private_key.public_key()

    # Serialize the private key to PEM format
    pem_private_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Serialize the public key into PEM format
    pem_public_key = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # Write the key to file
    with open(private_key_file, 'wb') as f:
        f.write(pem_private_key)
    with open(public_key_file, 'wb') as f:
        f.write(pem_public_key)

    print(f"Private key saved to {private_key_file}")
    print(f"Public key saved to {public_key_file}")
    return

def load_public_key(public_key_file: str):
    with open(public_key_file, 'rb') as f:
        public_key = serialization.load_pem_public_key(f.read())
    return public_key

def load_private_key(private_key_file: str):
    with open(private_key_file, 'rb') as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    return private_key

def encrypt_msg(public_key, message: str) -> bytes:
    if type(message) == str:
        message = message.encode()
        
    # Encrypting Data
    ciphertext = public_key.encrypt(
        message,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    # print(f"Ciphertext: {ciphertext}")
    return ciphertext

def decrypt_msg(private_key, ciphertext: bytes):
    if type(ciphertext) != bytes:
        print("rsa_tool.decrypt_msg() ciphertext mustbe type bytes")
        return None
    
    # Decrypting Data
    decrypted_message = private_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    # print(f"Decrypted message: {decrypted_message}")
    return decrypted_message

if __name__ == '__main__':
    create_new_keys = input("Do you want to create new key pairs? (yes/no): ").strip().lower()
    if create_new_keys == 'yes':
        public_key_file = input("Enter the file path to save the public key (default: public.pem): ").strip() or 'public.pem'
        private_key_file = input("Enter the file path to save the private key (default: private.pem): ").strip() or 'private.pem'
        create_key_pairs(public_key_file, private_key_file)
    else:
        exit(0)
        
    # public_key = load_public_key(public_key_file)
    # private_key = load_private_key(private_key_file)
    # message = "Hello, this is a secret message!"
    # ciphertext = encrypt_msg(public_key, message)
    # decrypted_message = decrypt_msg(private_key, ciphertext)
