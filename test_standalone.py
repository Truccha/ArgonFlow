import asyncio
import time
import websockets
import msgspec

# --- 1. DEFINE THE LEAN STRUCT ---
class FuturesTradeTick(msgspec.Struct):
    s: str
    p: str
    q: str
    T: int

# --- 2. DEFINE THE SCOUT LOGIC ---
class ArgonScout:
    def __init__(self, symbol: str, data_queue: asyncio.Queue, use_testnet: bool = False):
        self.symbol = symbol.upper()
        self.queue = data_queue
        self.is_running = True
        self.use_testnet = use_testnet
        
        host = "testnet.binancefuture.com" if use_testnet else "fstream.binance.com"
        self.url = f"wss://{host}/ws/{self.symbol.lower()}@aggTrade"
        
        print(f"[*] INIT: Targeting {self.url} (Mainnet Live Data)")
        
        self.decoder = msgspec.json.Decoder(FuturesTradeTick)
        self.count_rx = 0

    async def connect(self):
        print("[*] CONNECT: Attempting connection...")
        try:
            async with websockets.connect(
                self.url,
                ping_interval=20,
                ping_timeout=10,
                compression=None,
                max_size=2**20
            ) as ws:
                print(f"[*] SUCCESS: Linked to {self.symbol}!")
                await self._listen(ws)
        except Exception as e:
            print(f"[!] ERROR: {e}")
            import traceback
            traceback.print_exc()

    async def _listen(self, ws):
        async for message in ws:
            try:
                tick = self.decoder.decode(message)
                self.count_rx += 1
                
                if self.queue.full():
                    self.queue.get_nowait()
                
                self.queue.put_nowait(tick)
                
                if self.count_rx % 10 == 0:
                    print(f"   -> Received {self.count_rx} ticks (Price: {tick.p})")
            except Exception as e:
                print(f"[!] Decode Error: {e}")

    def stop(self):
        self.is_running = False
        print("[*] Scout stopped.")

# --- 3. RUNNER ---
async def consumer(queue, duration=10):
    print(f"[*] Consumer: Waiting for data for {duration}s...")
    start = time.time()
    count = 0
    while time.time() - start < duration:
        try:
            tick = await asyncio.wait_for(queue.get(), timeout=1.0)
            count += 1
        except asyncio.TimeoutError:
            continue
    print(f"[*] DONE: Processed {count} ticks total.")

async def main():
    print(">>> STARTING STANDALONE HFT TEST (MAINNET) <<<")
    queue = asyncio.Queue(maxsize=5000)
    scout = ArgonScout("BTCUSDT", queue, use_testnet=False)
    
    await asyncio.gather(
        scout.connect(),
        consumer(queue, duration=15)
    )
    scout.stop()

if __name__ == "__main__":
    # --- PYTHON 3.14+ COMPATIBLE UVLOOP ACTIVATION ---
    try:
        import uvloop
        print("[*] uvloop found. Activating via loop_factory...")
        # NEW WAY: Pass loop_factory to asyncio.run()
        asyncio.run(main(), loop_factory=uvloop.new_event_loop)
    except ImportError:
        print("[*] uvloop not found. Using default asyncio loop.")
        # Default way without uvloop
        asyncio.run(main())
    except Exception as e:
        print(f"FATAL CRASH: {e}")
        import traceback
        traceback.print_exc()