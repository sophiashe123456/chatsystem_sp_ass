import socket
import threading
import uuid


other_servers = [
    ("192.168.1.127", 9999),
    ("192.168.1.128", 9999),
]

clients = {}
lock = threading.Lock()
buffer_size = 1024
processed_messages = set()

def generate_message_id():
    return str(uuid.uuid4())

def send_to_server(server_address, message):
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect(server_address)
        server_socket.send(message.encode())
        server_socket.close()
    except Exception as e:
        print(f"Failed to send message to {server_address}: {e}")

def broadcast_to_other_servers(message, origin_server):
    for server_address in other_servers:
        if server_address != origin_server:
            send_to_server(server_address, message)

def handle_client(client_socket, username):
    welcome_message = f"Welcome {username}!"
    client_socket.send(welcome_message.encode())
    try:
        while True:
            message = client_socket.recv(buffer_size)
            if not message:
                break
            decoded_message = message.decode()
            message_id = generate_message_id()
            if decoded_message.startswith("/msg"):
                recipient, msg = decoded_message.split(' ', 2)[1:]
                if recipient in clients:
                    clients[recipient].send(msg.encode())
                else:
                    for server_address in other_servers:
                        send_to_server(server_address, f"{message_id} {decoded_message}")
            else:
                broadcast(f"{message_id} {decoded_message}", client_socket)
                broadcast_to_other_servers(f"{message_id} {decoded_message}", None)
    finally:
        with lock:
            del clients[username]
        client_socket.close()

def handle_server_connection(server_socket):
    try:
        while True:
            message = server_socket.recv(buffer_size)
            if not message:
                break
            decoded_message = message.decode()
            message_id, actual_message = decoded_message.split(' ', 1)
            if message_id in processed_messages:
                continue
            processed_messages.add(message_id)
            if actual_message.startswith("/msg"):
                recipient, msg = actual_message.split(' ', 2)[1:]
                if recipient in clients:
                    clients[recipient].send(msg.encode())
            else:
                broadcast(actual_message, None)
                broadcast_to_other_servers(decoded_message, None)
    finally:
        server_socket.close()

def broadcast(message, sender_socket):
    with lock:
        for client_socket in clients.values():
            if client_socket != sender_socket:
                try:
                    client_socket.send(message.encode())
                except:
                    client_socket.close()

def main(server_ip, server_port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((server_ip, server_port))
    server.listen(5)
    print(f"Server started on {server_ip}:{server_port}")

    while True:
        client_socket, addr = server.accept()
        username = client_socket.recv(buffer_size).decode()
        with lock:
            clients[username] = client_socket
        print(f"{username} connected.")
        threading.Thread(target=handle_client, args=(client_socket, username)).start()

        server_socket, _ = server.accept()
        threading.Thread(target=handle_server_connection, args=(server_socket,)).start()

if __name__ == "__main__":
    main("192.168.1.104", 9999)

