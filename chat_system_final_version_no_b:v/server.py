#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''=================================================
@Project -> File: chatsystem4 -> server.py
@IDE: PyCharm
@Author: YixinChen
@Date: 2024/7/18 09:45
@Desc: to be continued ...
=================================================='''
import asyncio
import websockets
import time
from collections import defaultdict
import argparse
from aes_tool import aes_decrypt, aes_encrypt
import rsa_tool


HEARTBEAT_INTERVAL = 10
HEARTBEAT_TIMEOUT = 30
MESSAGE_INTERVAL = 3
TMP_DIR = "/tmp"

pem_private_key, pem_public_key = rsa_tool.create_key_pairs()

#
clients = {}

# list: [websocket, aeskey, client name]
groups = defaultdict(list)
external_servers = set()


async def encrypt_and_send(websocket, message, client_aes_key):
    return await websocket.send(aes_encrypt(message, client_aes_key))

async def recv_and_decrypt(websocket, client_aes_key) -> str:
    response = await websocket.recv()
    response_decrypted = aes_decrypt(response, client_aes_key)
    return response_decrypted.decode('utf-8')

parser = argparse.ArgumentParser(description='Client arguments')
parser.add_argument('-port', type=int, default=8767, help='Server port, default 8767')
args = parser.parse_args()
server_port = args.port

def formatted_utc_time(timestamp):
    utc_time = time.gmtime(timestamp)
    formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", utc_time)
    return formatted_time


async def show_online_users(websocket, client_aes_key):
    user_list = []

    for username, values in clients.items():
        last_message_time = values['lasttime'] if values['lasttime'] is not None else "No messages sent yet"
        if isinstance(last_message_time, float):
            last_message_time = formatted_utc_time(last_message_time)
        user_list.append(f"***** {username:<30} - Last Message: {last_message_time} *****")

    # Adding a header and footer line of stars for better visual separation
    star_line = "*" * 100
    user_list_str = "\n".join(user_list)
    formatted_message = f"{star_line}\nOnline Users:\n{user_list_str}\n{star_line}"
    await encrypt_and_send(websocket, formatted_message, client_aes_key)


async def show_groups(websocket, client_aes_key):
    group_list = []

    for group, members in groups.items():
        group_list.append(f"***** Group: {group:<30} - Members: {len(members)} *****")

    if not group_list:
        group_list.append("No groups available.")

    star_line = "*" * 100
    group_list_str = "\n".join(group_list)
    formatted_message = f"{star_line}\nGroups:\n{group_list_str}\n{star_line}"
    await encrypt_and_send(websocket, formatted_message, client_aes_key)



async def list_group_memebers(websocket, client_aes_key, group_name:str):
    " List goroup members "
    if group_name not in groups:
        formatted_message = f"Error: Group {group_name} not exist"
        await encrypt_and_send(websocket, formatted_message, client_aes_key)
        return
    
    
    members = groups[group_name]
    member_name_list = [f"***** Group: {group_name:<30} - Members: {len(members)} *****"] + [f'{i+1}: {name[2]}' for i, name in enumerate(members)]
    response = "\n".join(member_name_list)

    star_line = "*" * 100
    formatted_message = f"{star_line}\nGroups:\n{response}\n{star_line}"
    await encrypt_and_send(websocket, formatted_message, client_aes_key)
    return



async def private_message(username, recipient_username, message):
    sender_socket = clients[username]['socket']
    sender_aes_key = clients[username]['aes']
    if recipient_username not in clients:
        await encrypt_and_send(sender_socket, f"ERROR: User '{recipient_username}' does not exist.", sender_aes_key)
        return
    if recipient_username == username:
        await encrypt_and_send(sender_socket, f"ERROR: You cannot send a private message to yourself.", sender_aes_key)
        return

    recipient_socket = clients[recipient_username]['socket']
    recipient_aes_key = clients[recipient_username]['aes']
    
    await encrypt_and_send(recipient_socket, f"Private message from USER [{username}]: {message}", recipient_aes_key)
    await encrypt_and_send(sender_socket, f"fPrivate message to {recipient_username}: {message}", sender_aes_key)
    


async def broadcast_message(username, message):
    sender_socket = clients[username]['socket']
    sender_aes_key = clients[username]['aes']
    
    broadcast_content = f"[Broadcast from {username}]: {message}"
    for client_username, values in clients.items():
        if client_username != username:
            client_socket = values['socket']
            client_aes_key = values['aes']
            await encrypt_and_send(client_socket, broadcast_content, client_aes_key)
            
    await encrypt_and_send(sender_socket, f"Broadcast message sent: {message}", sender_aes_key)


async def group_message(username, group, message):
    sender_socket = clients[username]['socket']
    sender_aes_key = clients[username]['aes']
    
    if group not in groups:
        await encrypt_and_send(sender_socket, f"ERROR: Group '{group}' does not exist.", sender_aes_key)
        return
    group_content = f"[Group {group} message from {username}]: {message}"
    for member_socket, member_aes_key, member_name in groups[group]:
        if member_socket != sender_socket:
            await encrypt_and_send(member_socket, group_content, member_aes_key)
            
    await encrypt_and_send(sender_socket, f"Group message to {group}: {message}", sender_aes_key)


# async def receive_file(websocket, aes_key, recipient_username, file_name):
#     file_path = os.path.join(TMP_DIR, recipient_username, "tmp", file_name)
#     os.makedirs(os.path.dirname(file_path), exist_ok=True)

#     with open(file_path, 'wb') as f:
#         while True:
#             chunk = await recv_and_decrypt(websocket, aes_key)
#             if chunk == b'EOF':
#                 break
#             if isinstance(chunk, str):
#                 chunk = chunk.encode('utf-8')
#             f.write(chunk)

#     return file_path


async def send_file(sender_username, recipient_username, file_name, file_data, isGroupfile = False):
    recipient_socket = clients[recipient_username]['socket']
    recipient_aes_key = clients[recipient_username]['aes']
    prefix = '/file'
    if isGroupfile:
        prefix = '/groupfile'
    await encrypt_and_send(recipient_socket, f"{prefix} {sender_username} {file_name} {file_data}", recipient_aes_key)

    # with open(file_path, 'rb') as f:
    #     while chunk := f.read(4096):
    #         await encrypt_and_send(recipient_socket, chunk, recipient_aes_key)
    # await encrypt_and_send(recipient_socket, b'EOF', recipient_aes_key)


# async def handle_challenge(challenge_name, user_input, websocket, aes_key):
#     if challenge_name == "/backdoor1":
#         return await backdoor_challenge_1(user_input, websocket, aes_key)
#     if challenge_name == "/backdoor2":
#         return await backdoor_challenge_2(user_input,websocket, aes_key)
#     if challenge_name == "/backdoor3":
#         return await backdoor_challenge_3(user_input,websocket, aes_key)
#     if challenge_name == "/backdoor4":
#         return await backdoor_challenge_4(user_input,websocket, aes_key)
#     if challenge_name == "/backdoor5":
#         return await backdoor_challenge_5(user_input,websocket, aes_key)


# async def backdoor_challenge_1(user_input, websocket, aes_key):
#     #
#     allowed_builtins = {
#         "str": str,
#         "int": int,
#         "print": print,
#     }
#     sandbox = {"__builtins__": allowed_builtins}

#     try:
#         # async for message in websocket:
#         exec(user_input, sandbox)
#     except Exception as e:
#         return f"Error: {e}"

#     # return "Executed successfully"

# async def backdoor_challenge_2(user_input, websocket, aes_key):

#     try:
#         if len(user_input) > 7:
#             await encrypt_and_send(websocket, "Oh hacker!", aes_key)
#             exit(0)

#         print('Answer: {}'.format(eval(user_input)))
#     except Exception as e:
#         return f"Error: {e}"

# async def backdoor_challenge_3(user_input, websocket, aes_key):

#     allowed_builtins = {'print': print}
#     try:
#         exec(user_input, {"__builtins__": allowed_builtins})
#     except Exception as e:
#         await encrypt_and_send(websocket, f"Error: {e}\n", aes_key)


# async def backdoor_challenge_4(user_input, websocket, aes_key):

#     restricted_globals = {'__builtins__': None}

#     try:
#         exec(user_input, restricted_globals)

#     except Exception as e:
#         await encrypt_and_send(websocket, f"Error: {e}\n", aes_key)
        


# async def backdoor_challenge_5(user_input, websocket, aes_key):
#     forbidden_patterns = ['import', 'os', 'system', 'subprocess', 'eval', 'exec', '.__', '.__class__',
#                           '.__subclasses__']
#     allowed_builtins = {'print': print, 'str': str, 'int': int}

#     for pattern in forbidden_patterns:
#         if pattern in user_input:
#             await encrypt_and_send(websocket, "Forbidden pattern detected!\n", aes_key)
            
#     try:
#         exec(user_input, {"__builtins__": allowed_builtins})

#     except Exception as e:
#         await encrypt_and_send(websocket, f"Error: {e}\n", aes_key)




def get_client_aes_key(client_hello_msg:bytes) -> bytes:
    global pem_private_key
    # decrypt aes key
    private_key = rsa_tool.load_private_key_from_bytes(pem_private_key)
    # try:
    client_aes_key = rsa_tool.decrypt_msg(private_key, client_hello_msg)
    return client_aes_key


async def echo(websocket, path):
    
    # username = input("Enter your username: ")
    # client_id = id(websocket)
    # clients[client_id] = {'ws': websocket, 'last_active': time.time()}
    
    # send public key
    await websocket.send(pem_public_key)

    # receive aes key
    received_aes_key = await websocket.recv()
    aes_key = get_client_aes_key(received_aes_key)
    if aes_key is None:
        print('Error getting client\'s aes key ')
        await websocket.close()
        return 
    
    # Finish handshake
    await encrypt_and_send(websocket, "Handshake Finished", aes_key)
        
    username = await recv_and_decrypt(websocket, aes_key)
    
    if username in clients:
        await encrypt_and_send(websocket, "ERROR: Username already taken. Please choose another one.", aes_key)
        await websocket.close()
        return
    
    
    clients[username] = {'socket': websocket, 'aes': aes_key, 'lasttime': None}
    await encrypt_and_send(websocket, "SUCCESS: Username registered.", aes_key)
    
    print(f"{username} connected")

    # challenge_mode = False
    # challenge_name = ""

    try:
        async for message in websocket:

            message = aes_decrypt(message, aes_key).decode()
            
            # if challenge_mode:
            #     result = await handle_challenge(challenge_name, message, websocket, aes_key)
            #     await encrypt_and_send(websocket, result, aes_key)
                
            #     if message == "quit":
            #         challenge_mode = False
            #         await encrypt_and_send(websocket, "Exited challenge mode. You can continue chatting.", aes_key)
            #     continue

            print(f"Received '{message}' from USER [{username}]")
            current_time = time.time()
            if clients[username]['lasttime'] is None:
                clients[username]['lasttime'] = current_time
            else:
                time_since_last_message = current_time - clients[username]['lasttime']
                if time_since_last_message < MESSAGE_INTERVAL:
                    await encrypt_and_send(
                        websocket,
                        f"Please wait {MESSAGE_INTERVAL - time_since_last_message:.1f} seconds before sending another message.",
                        aes_key)
                    continue
            clients[username]['lasttime'] = current_time
            if message == "/list":
                await show_online_users(websocket, aes_key)
            elif message == "/showgroups":
                await show_groups(websocket, aes_key)
            elif message .startswith("/showgroupmembers"):
                values = message.split(' ')
                if len(values) != 2:
                    await encrypt_and_send(websocket, "ERROR: Invalid listmemebers message format. Use /showgroupmembers <groupname>", aes_key)
                else:
                    await list_group_memebers(websocket, aes_key, values[1])

            elif message.startswith("/msg"):
                parts = message.split(" ", 2)
                if len(parts) < 3:
                    await encrypt_and_send(websocket, "ERROR: Invalid private message format. Use /msg <username> <message>", aes_key)
                else:
                    receiver_username = parts[1]
                    private_message_content = parts[2]
                    await private_message(username, receiver_username, private_message_content)
            elif message.startswith("/public"):
                public_message_content = message[len("/public "):]
                await broadcast_message(username, public_message_content)
            elif message.startswith("/create"):
                _, group_name = message.split(" ", 1)
                if group_name in groups:
                    await encrypt_and_send(websocket, f"ERROR: Group '{group_name}' already exists.", aes_key)
                else:
                    groups[group_name].append([websocket, aes_key, username])
                    await encrypt_and_send(websocket, f"SUCCESS: Group '{group_name}' created and joined.", aes_key)
            elif message.startswith("/join"):
                _, group_name = message.split(" ", 1)
                if group_name not in groups:
                    await encrypt_and_send(websocket, f"ERROR: Group '{group_name}' does not exist.", aes_key)
                else:
                    already_in_group = False
                    for values in groups[group_name]:
                        if values[2] == username:
                            already_in_group = True
                            break

                    if already_in_group:
                        await encrypt_and_send(websocket, f"ERROR: You are already in group '{group_name}'.", aes_key)
                    else:
                        groups[group_name].append([websocket, aes_key, username])
                        await encrypt_and_send(websocket, f"SUCCESS: Joined group '{group_name}'.", aes_key)
            elif message.startswith("/groupfile"):
                parts = message.split(" ", 3)
                if len(parts) != 4:
                    print(parts)
                    await encrypt_and_send(websocket, f"ERROR: Invalid file transfer format. Use /file <group_name> <file_name> <data>", aes_key)
                else:
                    receiver_group_name = parts[1]
                    file_name = parts[2]
                    file_data = parts[3]
                    if receiver_group_name not in groups:
                        await encrypt_and_send(websocket, f"ERROR: Group '{receiver_group_name}' does not exist.", aes_key)
                        continue
                    
                    user_in_group = False
                    for member in groups[receiver_group_name]:
                        if member[0] == websocket:
                            user_in_group = True
                            break
                    
                    if not user_in_group:
                        await encrypt_and_send(websocket, f"ERROR: You have not join group '{receiver_group_name}'.", aes_key)
                    else:
                        for member in groups[receiver_group_name]:
                            receiver_username = member[2]
                            await send_file(f"{receiver_group_name}_{username}", receiver_username, file_name, file_data, isGroupfile=True)
                            await encrypt_and_send(websocket, f"File '{file_name}' sent to group member: {receiver_username}.", aes_key)

                        await encrypt_and_send(websocket, f"File '{file_name}' sent to group {receiver_group_name} finished.", aes_key)
            elif message.startswith("/group"):
                parts = message.split(" ", 2)
                if len(parts) < 3:
                    await encrypt_and_send(websocket, f"ERROR: Invalid group message format. Use /group <group_name> <message>", aes_key)
                else:
                    group_name = parts[1]
                    group_message_content = parts[2]
                    await group_message(username, group_name, group_message_content)
            elif message.startswith("/file"):
                parts = message.split(" ", 3)
                if len(parts) != 4:
                    print(parts)
                    await encrypt_and_send(websocket, f"ERROR: Invalid file transfer format. Use /file <receiver_name> <file_name> <data>", aes_key)
                else:
                    receiver_username = parts[1]
                    file_name = parts[2]
                    file_data = parts[3]
                    if receiver_username not in clients:
                        await encrypt_and_send(websocket, f"ERROR: User '{receiver_username}' does not exist.", aes_key)
                    else:
                        # file_path = await receive_file(websocket, aes_key, receiver_username, file_name)
                        await send_file(username, receiver_username, file_name, file_data)
                        await encrypt_and_send(websocket, f"File '{file_name}' sent to {receiver_username}.", aes_key)

            # elif message.startswith("/backdoor"):
            #     challenge_name = message.split(" ")[0]
            #     challenge_mode = True
            #     await encrypt_and_send(websocket, f"Entered challenge mode: {challenge_name}. Type 'quit' to exit.", aes_key)
            elif message == "/quit":
                await encrypt_and_send(websocket, "SUCCESS: You have left the ChatSystem:)", aes_key)
                await websocket.close()
                return
            else:
                await broadcast_message(username, message)
    except websockets.exceptions.ConnectionClosed:
        print(f"USER {username} disconnected:(")
    finally:
        #
        del clients[username]

        for group in groups.values():
            for member in group:
                if member[0] == websocket:
                    group.remove(member)
        print(f"{username} disconnected and removed from all groups.")


async def connect_to_server(uri):
    async with websockets.connect(uri) as websocket:
        external_servers.add(websocket)
        print(f"Connected to external server at {uri}")
        try:
            while True:
                message = await websocket.recv()
                print(f"Received message from external server: {message}")
                #
        except websockets.exceptions.ConnectionClosed:
            print(f"Connection to external server at {uri} closed.")
        finally:
            external_servers.remove(websocket)




start_server = websockets.serve(echo, "0.0.0.0", server_port)

asyncio.get_event_loop().run_until_complete(start_server)
print("*" * 100)
print(f"WebSocket Server started and listening on ws://0.0.0.0:{server_port}")
print("*" * 100)
asyncio.get_event_loop().run_forever()
