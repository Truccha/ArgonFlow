# app/engine/scout.py
import asyncio
import websockets
import msgspec

# --- THE LEAN STRUCT ---
# Only the data your users' bots actually need to trade.
# msgspec will automatically ignore 'e', 'E', 'a', 'f', 'l', 'm' from the JSON stream.
class FuturesTradeTick(msgspec.Struct):
    s: str  # Symbol (Needed to identify stream if multiplexing)
    p: str  # Price (The most critical field)
    q: str  # Quantity (Volume)
    T: int  # Trade Time (Exchange timestamp for ordering)

class ArgonScout:
    def __init__(self, symbol: str, data_queue: asyncio.Queue, use_testnet: bool = False):
        self.symbol = symbol.upper()
        self.queue = data_queue
        self.is_running = True
        
        host = "testnet.binancefuture.com" if use_testnet else "fstream.binance.com"
        self.url = f"wss://{host}/ws/{self.symbol.lower()}@aggTrade"
        
        # Decoder configured to ignore unknown fields (default behavior)
        # It maps JSON keys 's', 'p', 'q', 'T' to our struct and drops the rest.
        self.decoder = msgspec.json.Decoder(FuturesTradeTick)
        
        self.count_rx = 0
        self.count_drop = 0

    async def connect(self):
        retry_delay = 1.0
        while self.is_running:
            try:
                async with websockets.connect(
                    self.url,
                    ping_interval=20,
                    ping_timeout=10,
                    compression=None, 
                    max_size=2**20
                ) as ws:
                    print(f"[*] Scout: LINKED (Lean Mode) -> {self.symbol}")
                    retry_delay = 1.0
                    await self._listen(ws)
            except Exception as e:
                print(f"[!] Scout: Drop ({e}). Retry in {retry_delay}s")
                if self.is_running:
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 60)

    async def _listen(self, ws):
        async for message in ws:
            try:
                # FASTEST PATH: 
                # 1. Reads JSON.
                # 2. Extracts ONLY s, p, q, T.
                # 3. Discards 'a', 'f', 'l', 'm', 'e', 'E' immediately at C-level.
                tick = self.decoder.decode(message)
                self.count_rx += 1

                if self.queue.full():
                    try:
                        self.queue.get_nowait()
                        self.count_drop += 1
                    except asyncio.QueueEmpty:
                        pass
                
                self.queue.put_nowait(tick)

            except msgspec.DecodeError:
                continue
            except Exception:
                # Catch any other unexpected error to keep loop alive
                continue

    def stop(self):
        self.is_running = False