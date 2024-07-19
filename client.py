#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import asyncio
import websockets


async def send_message(websocket):
    while True:
        message = input("Enter message =====> : ")
        # if message.startswith("/file"):
        #     parts = message.split(' ', 3)
        #     filename = parts[2]
        #     with open(filename, "rb") as f:
        #         file_data = f.read().decode('latin1')
        #     message = f"/file {parts[1]} {filename} {file_data}"
        await websocket.send(message)
        if message == "/quit":
            break


async def receive_message(websocket):
    while True:
        try:
            response = await websocket.recv()
            print(f"\nReceived: {response}")
        except websockets.ConnectionClosed:
            print("Connection closed by server~~.")
            break


async def handle_user_input(websocket):
    while True:
        message = input("Enter your message (or quit to disconnect): ")
        await websocket.send(message)
        response = await websocket.recv()
        print(response)
        if message == "/quit":
            break

async def main():
    uri = "ws://localhost:8767"
    exit_flag = 0
    while True:
        username = input("Enter your username: ")
        async with websockets.connect(uri) as websocket:
            # while True:
            # username = input("Enter your username: ")
            await websocket.send(username)
            response = await websocket.recv()
            if response.startswith("ERROR"):
                print(response)
                continue
            elif response.startswith("SUCCESS"):
                print(response)
                # send_task = asyncio.create_task(send_message(websocket))
                # receive_task = asyncio.create_task(receive_message(websocket))
                #
                # await asyncio.gather(send_task, receive_task)
                # break
                # await handle_user_input(websocket)


                while True:
                    try:
                        # message = input()
                        message = input("Enter message to send (or 'quit' to quit): ")
                        if message == '/quit':
                            exit_flag = 1
                            break
                        await websocket.send(message)
                        response = await websocket.recv()
                        print(response)
                    except websockets.exceptions.ConnectionClosed:
                        exit_flag = 1
                        print("Connection closed by server.")
                        break

            if exit_flag:
                break

if __name__ == "__main__":
    asyncio.run(main())