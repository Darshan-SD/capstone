import redis

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0)

# Find session keys
session_keys = r.keys("session:*")

if session_keys:
    r.delete(*session_keys)
    print(f"✅ Deleted {len(session_keys)} session key(s).")
else:
    print("ℹ️ No session keys found.")
