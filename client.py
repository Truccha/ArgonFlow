import asyncio
import websockets
import msgspec
import time
import statistics

# Define the struct (Must match server exactly)
class FuturesTradeTick(msgspec.Struct):
    s: str
    p: str
    q: str
    T: int  # Exchange Timestamp (ms)

async def listen():
    uri = "ws://localhost:8765"
    decoder = msgspec.msgpack.Decoder(FuturesTradeTick)
    
    latencies = []
    count = 0
    
    print(f"Connecting to {uri}...")
    async with websockets.connect(uri) as ws:
        print("Connected! Measuring latency...\n")
        
        async for message in ws:
            # 1. Record exact arrival time (ns precision)
            arrival_ns = time.time_ns()
            
            # 2. Decode
            data = decoder.decode(message)
            
            # 3. Calculate Latency
            # data.T is from Binance in milliseconds. Convert to nanoseconds.
            exchange_time_ns = data.T * 1_000_000
            
            # Latency in milliseconds
            latency_ms = (arrival_ns - exchange_time_ns) / 1_000_000
            
            latencies.append(latency_ms)
            count += 1
            
            # Print every tick for the first 5, then summarize
            if count <= 5:
                print(f"[#{count}] Price: {data.p} | Latency: {latency_ms:.3f} ms")
            
            # Print stats every 50 ticks
            if count % 50 == 0:
                avg_lat = statistics.mean(latencies)
                min_lat = min(latencies)
                max_lat = max(latencies)
                p99_lat = sorted(latencies)[int(len(latencies)*0.99)] if len(latencies) > 1 else max_lat
                
                print("-" * 40)
                print(f"Stats (Last {len(latencies)} ticks):")
                print(f"  Avg:  {avg_lat:.3f} ms")
                print(f"  Min:  {min_lat:.3f} ms")
                print(f"  Max:  {max_lat:.3f} ms")
                print(f"  P99:  {p99_lat:.3f} ms (Tail latency)")
                print("-" * 40)
                
                # Reset list to keep memory low, but keep running avg if you prefer
                latencies = [] 

if __name__ == "__main__":
    try:
        import uvloop
        asyncio.run(listen(), loop_factory=uvloop.new_event_loop)
    except ImportError:
        asyncio.run(listen())