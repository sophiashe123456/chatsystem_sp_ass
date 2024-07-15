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

def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("192.168.1.104", 9999))

    #
    # username = input("Enter your username: ")
    # client.send(username.encode())

    #
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
        else:
            client.send(message.encode())

    client.close()

if __name__ == "__main__":
    main()