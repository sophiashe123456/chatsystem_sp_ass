#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''=================================================
@Project -> File ：chatsystem -> client
@IDE ：PyCharm
@Author ：Yixin Chen
@Date ：2024/7/1 20:23
@Desc ：to be continued ...
=================================================='''

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

def print_help():
    help_text = """
    Available commands:
    /msg [username] [message] - Send a private message to a user
    /file [username] [filename] - Send a file to a user
    /list - List all connected users
    /help - Show this help message
    /quit - Disconnect from the server
    """
    print(help_text)

def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("192.168.1.104", 9999))

    username = input("Enter your username: ")
    client.send(username.encode())

    threading.Thread(target=receive_messages, args=(client,)).start()

    while True:
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
        elif message == "/help":
            print_help()
        elif message.startswith("/msg"):
            if len(message.split()) < 3:
                print("Usage: /msg [username] [message]")
            else:
                client.send(message.encode())
        elif message == "/list":
            client.send(message.encode())
        else:
            print("Unknown command. Type /help for a list of commands.")

    client.close()

if __name__ == "__main__":
    main()
