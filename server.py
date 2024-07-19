#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import asyncio
import websockets
import time
from collections import defaultdict
import os

HEARTBEAT_INTERVAL = 10
HEARTBEAT_TIMEOUT = 30
MESSAGE_INTERVAL = 3
TMP_DIR = "/tmp"
#
clients = {}
groups = defaultdict(set)
external_servers = set()


def formatted_utc_time(timestamp):
    utc_time = time.gmtime(timestamp)
    formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", utc_time)
    return formatted_time


async def show_online_users(websocket):
    user_list = []

    for username, values in clients.items():
        last_message_time = values[-1] if len(values) > 1 else "No messages sent yet"
        if isinstance(last_message_time, float):
            last_message_time = formatted_utc_time(last_message_time)
        user_list.append(f"***** {username:<30} - Last Message: {last_message_time} *****")

    # Adding a header and footer line of stars for better visual separation
    star_line = "*" * 100
    user_list_str = "\n".join(user_list)
    formatted_message = f"{star_line}\nOnline Users:\n{user_list_str}\n{star_line}"
    await websocket.send(formatted_message)


async def show_groups(websocket):
    group_list = []

    for group, members in groups.items():
        group_list.append(f"***** Group: {group:<30} - Members: {len(members)} *****")

    if not group_list:
        group_list.append("No groups available.")

    star_line = "*" * 100
    group_list_str = "\n".join(group_list)
    formatted_message = f"{star_line}\nGroups:\n{group_list_str}\n{star_line}"
    await websocket.send(formatted_message)


async def private_message(username, recipient_username, message):
    sender_socket = clients[username][0]
    if recipient_username not in clients:
        await sender_socket.send(f"ERROR: User '{recipient_username}' does not exist.")
        return
    if recipient_username == username:
        await sender_socket.send("ERROR: You cannot send a private message to yourself.")
        return

    recipient_socket = clients[recipient_username][0]
    await recipient_socket.send(f"Private message from USER [{username}]: {message}")
    await sender_socket.send(f"Private message to {recipient_username}: {message}")


async def broadcast_message(username, message):
    sender_socket = clients[username][0]
    broadcast_content = f"[Broadcast from {username}]: {message}"
    for client_username, values in clients.items():
        if client_username != username:
            client_socket = values[0]
            await client_socket.send(broadcast_content)
    await sender_socket.send(f"Broadcast message sent: {message}")


async def group_message(username, group, message):
    sender_socket = clients[username][0]
    if group not in groups:
        await sender_socket.send(f"ERROR: Group '{group}' does not exist.")
        return
    group_content = f"[Group {group} message from {username}]: {message}"
    for member_socket in groups[group]:
        if member_socket != sender_socket:
            await member_socket.send(group_content)
    await sender_socket.send(f"Group message to {group}: {message}")


async def receive_file(websocket, recipient_username, file_name):
    file_path = os.path.join(TMP_DIR, recipient_username, "tmp", file_name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, 'wb') as f:
        while True:
            chunk = await websocket.recv()
            if chunk == b'EOF':
                break
            if isinstance(chunk, str):
                chunk = chunk.encode('utf-8')
            f.write(chunk)

    return file_path


async def send_file(sender_username, recipient_username, file_name, file_path):
    recipient_socket = clients[recipient_username][0]
    await recipient_socket.send(f"/file {sender_username} {file_name}")

    with open(file_path, 'rb') as f:
        while chunk := f.read(4096):
            await recipient_socket.send(chunk)
    await recipient_socket.send(b'EOF')


async def handle_challenge(challenge_name, user_input, websocket):
    if challenge_name == "/backdoor1":
        return await backdoor_challenge_1(user_input, websocket)
    if challenge_name == "/backdoor2":
        return await backdoor_challenge_2(user_input,websocket)
    if challenge_name == "/backdoor3":
        return await backdoor_challenge_3(user_input,websocket)
    if challenge_name == "/backdoor4":
        return await backdoor_challenge_4(user_input,websocket)
    if challenge_name == "/backdoor5":
        return await backdoor_challenge_5(user_input,websocket)


async def backdoor_challenge_1(user_input, websocket):
    #
    allowed_builtins = {
        "str": str,
        "int": int,
        "print": print,
    }
    sandbox = {"__builtins__": allowed_builtins}

    try:
        # async for message in websocket:
        exec(user_input, sandbox)
    except Exception as e:
        return f"Error: {e}"

    # return "Executed successfully"

async def backdoor_challenge_2(user_input, websocket):

    try:
        if len(user_input) > 7:
            await websocket.send("Oh hacker!")
            exit(0)

        print('Answer: {}'.format(eval(user_input)))
    except Exception as e:
        return f"Error: {e}"

async def backdoor_challenge_3(user_input, websocket):

    allowed_builtins = {'print': print}
    try:
        exec(user_input, {"__builtins__": allowed_builtins})
    except Exception as e:
        websocket.send(f"Error: {e}\n".encode())


async def backdoor_challenge_4(user_input, websocket):

    restricted_globals = {'__builtins__': None}

    try:
        exec(user_input, restricted_globals)

    except Exception as e:
        websocket.send(f"Error: {e}\n".encode())


async def backdoor_challenge_5(user_input, websocket):
    forbidden_patterns = ['import', 'os', 'system', 'subprocess', 'eval', 'exec', '.__', '.__class__',
                          '.__subclasses__']
    allowed_builtins = {'print': print, 'str': str, 'int': int}

    for pattern in forbidden_patterns:
        if pattern in user_input:
            websocket.send("Forbidden pattern detected!\n".encode())
    try:
        exec(user_input, {"__builtins__": allowed_builtins})

    except Exception as e:
        websocket.send(f"Error: {e}\n".encode())

async def echo(websocket, path):
    # username = input("Enter your username: ")
    # client_id = id(websocket)
    # clients[client_id] = {'ws': websocket, 'last_active': time.time()}
    username = await websocket.recv()
    if username in clients:
        await websocket.send("ERROR: Username already taken. Please choose another one.")
        await websocket.close()
        return
    clients[username] = [websocket]
    await websocket.send("SUCCESS: Username registered.")
    print(f"{username} connected")

    challenge_mode = False
    challenge_name = ""

    try:
        async for message in websocket:

            if challenge_mode:
                result = await handle_challenge(challenge_name, message, websocket)
                await websocket.send(result)
                if message == "quit":
                    challenge_mode = False
                    await websocket.send("Exited challenge mode. You can continue chatting.")
                continue

            print(f"Received '{message}' from USER [{username}]")
            current_time = time.time()
            if len(clients[username]) < 2:
                clients[username].append(current_time)
            else:
                time_since_last_message = current_time - clients[username][-1]
                if time_since_last_message < MESSAGE_INTERVAL:
                    await websocket.send(
                        f"Please wait {MESSAGE_INTERVAL - time_since_last_message:.1f} seconds before sending another message.")
                    continue
            clients[username][-1] = current_time
            if message == "/list":
                await show_online_users(websocket)
            elif message == "/showgroups":
                await show_groups(websocket)
            elif message.startswith("/msg"):
                parts = message.split(" ", 2)
                if len(parts) < 3:
                    await websocket.send("ERROR: Invalid private message format. Use /msg <username> <message>")
                else:
                    recipient_username = parts[1]
                    private_message_content = parts[2]
                    await private_message(username, recipient_username, private_message_content)
            elif message.startswith("/public"):
                public_message_content = message[len("/public "):]
                await broadcast_message(username, public_message_content)
            elif message.startswith("/create"):
                _, group_name = message.split(" ", 1)
                if group_name in groups:
                    await websocket.send(f"ERROR: Group '{group_name}' already exists.")
                else:
                    groups[group_name].add(websocket)
                    await websocket.send(f"SUCCESS: Group '{group_name}' created and joined.")
            elif message.startswith("/join"):
                _, group_name = message.split(" ", 1)
                if group_name not in groups:
                    await websocket.send(f"ERROR: Group '{group_name}' does not exist.")
                else:
                    if websocket in groups[group_name]:
                        await websocket.send(f"ERROR: You are already in group '{group_name}'.")
                    else:
                        groups[group_name].add(websocket)
                        await websocket.send(f"SUCCESS: Joined group '{group_name}'.")
            elif message.startswith("/group"):
                parts = message.split(" ", 2)
                if len(parts) < 3:
                    await websocket.send("ERROR: Invalid group message format. Use /group <group_name> <message>")
                else:
                    group_name = parts[1]
                    group_message_content = parts[2]
                    await group_message(username, group_name, group_message_content)
            elif message.startswith("/file"):
                parts = message.split(" ", 3)
                if len(parts) < 3:
                    await websocket.send("ERROR: Invalid file transfer format. Use /file <username> <file_name>")
                else:
                    recipient_username = parts[1]
                    file_name = parts[2]
                    if recipient_username not in clients:
                        await websocket.send(f"ERROR: User '{recipient_username}' does not exist.")
                    else:
                        file_path = await receive_file(websocket, recipient_username, file_name)
                        await send_file(username, recipient_username, file_name, file_path)
                        await websocket.send(f"File '{file_name}' sent to {recipient_username}.")
            elif message.startswith("/backdoor"):
                challenge_name = message.split(" ")[0]
                challenge_mode = True
                await websocket.send(f"Entered challenge mode: {challenge_name}. Type 'quit' to exit.")
            elif message == "/quit":
                await websocket.send("SUCCESS: You have left the ChatSystem:)")
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
            group.discard(websocket)
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


start_server = websockets.serve(echo, "localhost", 8767)

asyncio.get_event_loop().run_until_complete(start_server)
print("*" * 100)
print("WebSocket Server started and listening on ws://localhost:8767")
print("*" * 100)
asyncio.get_event_loop().run_forever()

# external_server_uri = "ws://external-server-host:port"  # URI
# asyncio.get_event_loop().run_until_complete(connect_to_server(external_server_uri))
#
# asyncio.get_event_loop().run_forever()
