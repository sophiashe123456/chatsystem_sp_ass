#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''=================================================
@Project -> File: chatsystem4 -> client
@IDE: PyCharm
@Author: YixinChen
@Date: 2024/7/18 09:46
@Desc: to be continued ...
=================================================='''
import asyncio
import websockets
import argparse
import rsa_tool
from aes_tool import generate_aes_key, aes_decrypt, aes_encrypt
import aioconsole
import os


client_aes_key = generate_aes_key()
username = None

async def encrypt_and_send(websocket, message):
    return await websocket.send(aes_encrypt(message, client_aes_key))

async def recv_and_decrypt(websocket):
    response = await websocket.recv()
    response_decrypted = aes_decrypt(response, client_aes_key)
    return response_decrypted.decode('utf-8')

async def send_message(websocket):
    global client_running
    while True:
        message = await aioconsole.ainput("")
        if message.startswith("/file"):
            try:
                parts = message.split(' ', 3)
                if len(parts) != 3:
                    print('Usage: /file <receiver_name> <file_name>')
                    print("Enter message to send (or 'quit' to quit): ", end='', flush=True)
                    continue
                receiver_name = parts[1]
                filename = parts[2]
                with open(filename, "rb") as f:
                    file_data = f.read().decode('latin1')
                message = f"/file {receiver_name} {filename} {file_data}"
            except Exception as e:
                print('Error', e)
                continue

        elif message.startswith("/groupfile"):
            try:
                parts = message.split(' ', 3)
                if len(parts) != 3:
                    print('Usage: /groupfile <group_name> <file_name>')
                    print("Enter message to send (or 'quit' to quit): ", end='', flush=True)
                    continue
                group_name = parts[1]
                filename = parts[2]
                with open(filename, "rb") as f:
                    file_data = f.read().decode('latin1')
                message = f"/groupfile {group_name} {filename} {file_data}"
            except Exception as e:
                print('Error', e)
                continue

        await encrypt_and_send(websocket, message)
        if message == "/quit":
            break


async def receive_message(websocket):
    print("Enter message to send (or 'quit' to quit): ", end='', flush=True)

    while True:
        try:
            response = await recv_and_decrypt(websocket)
            if response.startswith('/file'):
                values = response.split(' ', 3)
                sender_name = values[1]
                file_name = values[2]
                file_data = values[3]
                receive_file_path = os.path.join('./tmp', username, 'file_recv', f'user_{sender_name}', file_name)
                os.makedirs(os.path.dirname(receive_file_path), exist_ok=True)

                with open(receive_file_path, 'wb') as f:
                    f.write(file_data.encode('latin1'))
                print()
                print(f"You received file '{file_name}' from {sender_name}")
                print("Enter message to send (or 'quit' to quit): ", end='', flush=True)
            elif response.startswith('/groupfile'):
                values = response.split(' ', 3)
                sender_name = values[1]
                file_name = values[2]
                file_data = values[3]
                receive_file_path = os.path.join('./tmp', username, 'file_recv', f'group_{sender_name}', file_name)
                os.makedirs(os.path.dirname(receive_file_path), exist_ok=True)

                with open(receive_file_path, 'wb') as f:
                    f.write(file_data.encode('latin1'))
                print()
                print(f"You received file '{file_name}' from Group {sender_name}")
                print("Enter message to send (or 'quit' to quit): ", end='', flush=True)
            else:
                print()
                print(response)
                print()
                print("Enter message to send (or 'quit' to quit): ", end='', flush=True)
        except websockets.ConnectionClosed:
            print("Connection closed by server~~.")
            break


# async def handle_user_input(websocket):
#     while True:
#         message = input("Enter your message (or quit to disconnect): ")
#         await encrypt_and_send(websocket, message)
#         response = await recv_and_decrypt(websocket)
#         print(response)
#         if message == "/quit":
#             break


# step 1. Client: Use the server's public key to encrypt the client's AES key and send it to the server
# step 2. The server uses the private key to decrypt the client's AES key, and uses this AES key to encrypt 'Finished' and send it to the client
# step 3. The client tests the decrypted message. If Finished is received, it means that the handshake message is completed and encrypted communication begins
async def initialize_secure_connection(websocket:websockets.WebSocketClientProtocol):
    # receive rsa public key
    public_key_data = await websocket.recv()
    public_key = rsa_tool.load_public_key_from_bytes(public_key_data)
    print('Received RSA public key from server!')

    # encrypt aes key
    encrypted_aes_key = rsa_tool.encrypt_msg(public_key, client_aes_key)
    
    # send to server
    await websocket.send(encrypted_aes_key)
    
    # read server responsee
    aes_encrypted_response = await websocket.recv()
    
    # test response
    try:
        plaintext_response = aes_decrypt(aes_encrypted_response, key=client_aes_key).decode()
        if plaintext_response == 'Handshake Finished':
            print('Handshake Finished. Start AES encrypted transmission')
        else:
            print('Handshake Error.')
            print(f'Receive {plaintext_response}')
            exit(1)
    except Exception as e:
            print('Handshake Error. at initialize_secure_connection()')
            print(e)
            exit(1)
    return


# keep connection
async def ping_pong(websocket):
    while True:
        try:
            await websocket.ping()  # send ping message
            await asyncio.sleep(3)  # send every 3 second
        except websockets.ConnectionClosed:
            print("Connection closed by server~~.")
            break

async def main(server_address, port):
    global username
    uri = f"ws://{server_address}:{port}"
    print(f'Connecting to {uri}')
    
    exit_flag = 0
    while True:
        username = input("Enter your username: ")
        async with websockets.connect(uri) as websocket:
            await initialize_secure_connection(websocket)
            # while True:
            # username = input("Enter your username: ")
            await encrypt_and_send(websocket, username)
            response = await recv_and_decrypt(websocket)
            if response.startswith("ERROR"):
                print(response)
                continue
            elif response.startswith("SUCCESS"):
                print(response)
                
                await asyncio.gather(
                    receive_message(websocket),
                    send_message(websocket),
                    ping_pong(websocket),
                )
                
                
                #
                # await asyncio.gather(send_task, receive_task)
                # break
                # await handle_user_input(websocket)

                
                
                # await asyncio.create_task(ping_pong(websocket))
                
                # while True:
                #     try:
                #         # message = input()
                #         message = input("Enter message to send (or 'quit' to quit): ")
                #         if message == '/quit':
                #             exit_flag = 1
                #             break
                #         await encrypt_and_send(websocket, message)
                        
                #         response = await recv_and_decrypt(websocket)
                #         print(response)
                #     except websockets.exceptions.ConnectionClosed:
                #         exit_flag = 1
                #         print("Connection closed by server.")
                #         break

            if exit_flag:
                break



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Client arguments')
    parser.add_argument('server_address', type=str, help='Server IP address')
    parser.add_argument('-port', type=int, default=8767, help='Server port, default 8767')
    args = parser.parse_args()
    asyncio.run(main(
        server_address=args.server_address, 
        port=args.port
    ))