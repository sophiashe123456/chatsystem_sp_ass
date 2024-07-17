import socket
import threading
import os

def receive_messages(client_socket):
    while True:
        try:
            message = client_socket.recv(1024)
            if not message:
                break
            print(message.decode())
        except:
            break

def send_file(client_socket, filename, recipient):
    if not os.path.isfile(filename):
        print(f"File '{filename}' does not exist.")
        return

    with open(filename, "rb") as file:
        client_socket.send(f"/file {recipient} {filename}".encode())
        data = file.read()
        client_socket.send(data)

def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_ip = input("Enter the server IP address: ")
    server_port = int(input("Enter the server port: "))
    client.connect((server_ip, server_port))

    username = input("Enter your username: ")
    client.send(username.encode())

    threading.Thread(target=receive_messages, args=(client,)).start()

    while True:
        try:
            message = input()
            if message.startswith("/file"):
                parts = message.split(maxsplit=2)
                if len(parts) < 3:
                    print("Usage: /file [recipient] [filename]")
                    continue
                _, recipient, filename = parts
                send_file(client, filename, recipient)
            elif message == "/quit":
                client.send(message.encode())
                print("You have left the chat.")
                break
            else:
                client.send(message.encode())
        except BrokenPipeError:
            print("Connection to the server was lost.")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            break

    client.close()

if __name__ == "__main__":
    main()
