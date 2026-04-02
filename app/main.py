import asyncio
import uvloop
import websockets
from app.engine.scout import ArgonScout
from app.engine.broadcaster import Broadcaster

async def main():
    print(">>> ARGON FLOW HFT SERVICE STARTING <<<")
    
    # 1. Shared Queue (The bridge between Ingest and Broadcast)
    queue = asyncio.Queue(maxsize=5000)
    
    # 2. Initialize Components
    scout = ArgonScout(symbol="BTCUSDT", data_queue=queue, use_testnet=False)
    
    broadcaster = Broadcaster()
    
    # 3. Define WebSocket Handler for Users
    async def handler(websocket):
        # TODO: Add Authentication Here (Phase 4)
        await broadcaster.register(websocket)

    # 4. Start Tasks
    ingest_task = asyncio.create_task(scout.connect())
    
    broadcast_task = asyncio.create_task(broadcaster.run_broadcast_loop(queue))
    
    server = await websockets.serve(
        handler, 
        "0.0.0.0", # Listen on all interfaces
        8765,      # Port
        compression=None, # Disable compression for speed
        ping_interval=20,
        ping_timeout=10
    )
    
    print(f"[*] Server listening on ws://0.0.0.0:8765")
    print("[*] Press Ctrl+C to stop")
    
    await server.wait_closed()
    
    scout.stop()
    broadcast_task.cancel()
    ingest_task.cancel()

if __name__ == "__main__":
    try:
        import uvloop
        print("[*] Using uvloop for maximum performance")
        asyncio.run(main(), loop_factory=uvloop.new_event_loop)
    except ImportError:
        print("[*] uvloop not found, using default loop")
        asyncio.run(main())