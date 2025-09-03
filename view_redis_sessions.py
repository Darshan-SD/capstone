# view_redis_sessions.py

import redis
import pickle
import msgpack 

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0)

# Get all session keys
keys = r.keys("session:*")
print(f"\n🔑 Found {len(keys)} session key(s):\n")

for key in keys:
    print(f"🧠 Key: {key.decode()}")

    raw_data = r.get(key)


    decoded = None

    try:
        decoded = pickle.loads(raw_data)
        print("✅ Decoded with pickle:", decoded)
    except Exception:
        try:
            decoded = msgpack.unpackb(raw_data, raw=False)
            print("✅ Decoded with msgpack:", decoded)
        except Exception as e:
            print("❌ Could not decode:", e)

    print("-" * 50)
