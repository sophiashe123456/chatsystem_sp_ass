from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

# AES encryption
def aes_encrypt(plain_text: str, key:bytes) -> bytes:
    if type(plain_text) == str:
        plain_text = plain_text.encode()
    
    # Generate a random initialization vector (IV)
    iv = get_random_bytes(16)
    # Creating an AES Encryptor
    cipher = AES.new(key, AES.MODE_CBC, iv)
    # Padding the plaintext
    padded_text = pad(plain_text, AES.block_size)
    # encryption
    encrypted_text = cipher.encrypt(padded_text)
    # Returns IV and ciphertext
    return iv + encrypted_text

# AES Decryption
def aes_decrypt(encrypted_text:bytes, key:bytes) -> bytes:
    if type(encrypted_text) != bytes:
        print('aes_decrypt() function argument encrypted_text must have type bytes')
        exit(1)
    
    # Extrac IV
    iv = encrypted_text[:16]
    # Extract ciphertext
    cipher_text = encrypted_text[16:]
    # Creating an AES Decryptor
    cipher = AES.new(key, AES.MODE_CBC, iv)
    # Decrypt and remove padding
    decrypted_bytes = unpad(cipher.decrypt(cipher_text), AES.block_size)
    return decrypted_bytes

# Generrate AES key
def generate_aes_key():
    return get_random_bytes(16)


