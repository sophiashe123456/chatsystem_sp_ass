import socket
import threading
import time
import websockets
import asyncio

clients = {}
groups = {}
lock = threading.Lock()
buffer_size = 1024
message_interval = 2  # minimum interval between messages in seconds
user_last_message_time = {}  # key: username, value: last message timestamp

# WebSocket server-client communication settings
connected_servers = set()
websocket_uris = [
    "ws://192.168.1.104:5551",
    "ws://192.168.1.127:5552",

]

async def broadcast_via_websockets(message):
    if connected_servers:
        await asyncio.wait([server.send(message) for server in connected_servers])

async def ws_handler(websocket, path):
    print(f"WebSocket connection established on path: {path}")
    connected_servers.add(websocket)
    try:
        async for message in websocket:
            print(f"Received from WebSocket server: {message}")
            broadcast(message, None)  # Broadcast to local clients
    except websockets.ConnectionClosed:
        print("WebSocket connection closed")
    finally:
        connected_servers.remove(websocket)

async def start_ws_server(port):
    async with websockets.serve(ws_handler, "192.168.1.104", port):
        print(f"WebSocket Server started and listening on ws://192.168.1.104:{port}")
        await asyncio.Future()  # Run forever

async def connect_to_ws_servers():
    for uri in websocket_uris:
        try:
            websocket = await websockets.connect(uri)
            connected_servers.add(websocket)
            print(f"Connected to WebSocket server: {uri}")
        except Exception as e:
            print(f"Failed to connect to WebSocket server: {uri}, error: {e}")

def broadcast(message, sender_socket):
    with lock:
        for client_socket in clients.values():
            if client_socket != sender_socket:
                try:
                    client_socket.send(message.encode())
                except:
                    client_socket.close()
        asyncio.run(broadcast_via_websockets(message))

def handle_client(client_socket, username):
    welcome_message = f"Welcome {username}!"
    client_socket.send(welcome_message.encode())
    try:
        while True:
            message = client_socket.recv(buffer_size)
            if not message:
                break

            current_time = time.time()
            if username in user_last_message_time:
                time_since_last_message = current_time - user_last_message_time[username]
                if time_since_last_message < message_interval:
                    client_socket.send(
                        f"Please wait {message_interval - time_since_last_message:.1f} seconds before sending another message.".encode())
                    continue

            user_last_message_time[username] = current_time

            decoded_message = message.decode()
            if decoded_message.startswith("/list"):
                with lock:
                    client_list = "\n".join([username for username in clients.keys()])
                client_socket.send(f"Online users:\n{client_list}".encode())
            elif decoded_message == "/groups":
                list_groups(client_socket)
            elif decoded_message.startswith("/group"):
                handle_group_command(client_socket, username, message)
            elif decoded_message.startswith("/msg"):
                parts = decoded_message.split(maxsplit=2)
                if len(parts) < 3:
                    client_socket.send("Usage: /msg [recipient] [message]".encode())
                    continue

                _, recipient, msg = parts
                with lock:
                    recipient_socket = None
                    for target_username, client in clients.items():
                        if target_username == recipient:
                            recipient_socket = client
                            break
                    if recipient_socket:
                        if recipient_socket == client_socket:
                            client_socket.send("You cannot send private messages to yourself.".encode())
                        else:
                            recipient_socket.send(f"Private message from [{username}]: {msg}".encode())
                    else:
                        client_socket.send(f"User '{username}' not found.".encode())
            elif decoded_message.startswith("/file"):
                parts = decoded_message.split(maxsplit=2)
                if len(parts) < 3:
                    client_socket.send("Usage: /file [recipient] [filename]".encode())
                    continue

                _, recipient, filename = parts
                with lock:
                    recipient_socket = None
                    for client, user in clients.items():
                        if user == recipient:
                            recipient_socket = client
                            break
                    if recipient_socket:
                        recipient_socket.send(f"/file {filename}".encode())
                        file_data = client_socket.recv(buffer_size)
                        recipient_socket.send(file_data)
                    else:
                        client_socket.send(f"User '{recipient}' not found.".encode())
            elif decoded_message == "/quit":
                client_socket.send("You have left the chat.".encode())
                break
            else:
                broadcast_message = f"[{username}]: {decoded_message}"
                broadcast(broadcast_message, client_socket)
    finally:
        with lock:
            username = clients.pop(client_socket, None)
        if username:
            broadcast(f"{username} has left the chat.".encode())
        client_socket.close()

def handle_group_command(client_socket, username, message):
    decoded_message = message.decode()
    parts = decoded_message.split(maxsplit=2)
    command = parts[0]
    groupname = parts[1] if len(parts) > 1 else None
    payload = parts[2] if len(parts) > 2 else None

    if command == "/groupcreate":
        if groupname in groups:
            client_socket.send(f"Group {groupname} already exists.".encode())
        else:
            groups[groupname] = [username]
            client_socket.send(f"Group {groupname} created.".encode())
    elif command == "/groupjoin":
        if groupname in groups:
            groups[groupname].append(username)
            client_socket.send(f"You joined the group {groupname}.".encode())
        else:
            client_socket.send(f"Group {groupname} does not exist.".encode())
    elif command == "/groupsend":
        if groupname in groups and username in groups[groupname]:
            group_message = f"[{groupname}] [{username}]: {payload}"
            for member in groups[groupname]:
                if member in clients and member != username:
                    clients[member].send(group_message.encode())
            asyncio.run(broadcast_via_websockets(group_message))
        else:
            client_socket.send(f"You are not part of the group {groupname} or the group does not exist.".encode())
    else:
        client_socket.send("Invalid group command.".encode())

def list_groups(client_socket):
    if not groups:
        client_socket.send("No groups available.".encode())
    else:
        group_list = "Groups:\n"
        for groupname, members in groups.items():
            group_list += f"{groupname} ({len(members)} members)\n"
        client_socket.send(group_list.encode())

def main(port, websocket_uri):
    global websocket_uris
    websocket_uris.remove(websocket_uri)  # Remove the current server's WebSocket URI from the list

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", port))
    server.listen(5)
    print(f"Server started on port {port}.")

    # Start WebSocket server
    threading.Thread(target=asyncio.run, args=(start_ws_server(port),)).start()

    # Connect to other WebSocket servers
    threading.Thread(target=asyncio.run, args=(connect_to_ws_servers(),)).start()

    while True:
        client_socket, addr = server.accept()
        print(f"Connection from {addr}.")
        threading.Thread(target=authenticate, args=(client_socket,)).start()

def authenticate(client_socket):
    while True:
        client_socket.send("Enter your username: ".encode())
        username = client_socket.recv(buffer_size).decode().strip()

        if username in clients:
            client_socket.send("Username already taken. Try another.".encode())
        else:
            with lock:
                clients[username] = client_socket
            print(f"{username} connected.")
            threading.Thread(target=handle_client, args=(client_socket, username)).start()
            break

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python server.py <port> <websocket_uri>")
        sys.exit(1)
    port = int(sys.argv[1])
    websocket_uri = sys.argv[2]
    main(port, websocket_uri)
