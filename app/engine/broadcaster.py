# app/engine/broadcaster.py
import asyncio
import websockets
import msgspec
from typing import Set, Any

class Broadcaster:
    def __init__(self):
        self.subscribers: Set[websockets.WebSocketServerProtocol] = set()
        
        # Pre-compile the MessagePack Encoder
        self.encoder = msgspec.msgpack.Encoder()
        
        print("[*] Broadcaster: Initialized")

    async def register(self, websocket: websockets.WebSocketServerProtocol):
        """Add a new user to the broadcast list"""
        self.subscribers.add(websocket)
        print(f"[+] User connected. Total subscribers: {len(self.subscribers)}")
        try:
            # Wait until the user disconnects
            await websocket.wait_closed()
        finally:
            self.subscribers.discard(websocket)
            print(f"[-] User disconnected. Total subscribers: {len(self.subscribers)}")

    async def run_broadcast_loop(self, data_queue: asyncio.Queue):
        """
        The Distribution Loop:
        1. Waits for a new tick from the Scout's queue.
        2. Encodes it to MsgPack.
        3. Sends it to ALL connected subscribers concurrently.
        """
        print("[*] Broadcaster: Listening for data...")
        
        while True:
            # Wait for new data from Scout
            tick = await data_queue.get()
            
            if not self.subscribers:
                continue # No one to send to, skip encoding/sending

            try:
                # Encode Struct -> Binary MsgPack (Very Fast)
                packet = self.encoder.encode(tick)
                
                # Create tasks to send to all users simultaneously
                # We use return_exceptions=True so one slow user doesn't crash the loop
                await asyncio.gather(
                    *[ws.send(packet) for ws in self.subscribers],
                    return_exceptions=True
                )
            except Exception as e:
                # Log but don't crash the broadcast loop
                print(f"[!] Broadcast error: {e}")

    def get_subscriber_count(self) -> int:
        return len(self.subscribers)