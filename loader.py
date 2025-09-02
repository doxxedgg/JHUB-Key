from flask import Flask, request, Response
import json
from datetime import datetime
import os

app = Flask(__name__)
KEY_FILE = "keys.json"

def load_keys():
    if not os.path.exists(KEY_FILE):
        return {}
    with open(KEY_FILE, "r") as f:
        return json.load(f)

@app.route('/')
def home():
    return "✅ Lua Script Loader is online."

@app.route('/script.lua')
def serve_script():
    key = request.args.get("key")
    if not key:
        return Response("Missing key", status=400)

    key = key.upper()
    keys = load_keys()

    if key not in keys:
        return Response("-- ❌ Invalid key", mimetype='text/plain', status=403)

    data = keys[key]
    if data["redeemed_by"] is None:
        return Response("-- ❌ Key not redeemed", mimetype='text/plain', status=403)

    expires = datetime.fromisoformat(data["expires_at"])
    if datetime.utcnow() > expires:
        return Response("-- ❌ Key expired", mimetype='text/plain', status=403)

    user_id = data["redeemed_by"]

    lua_code = f"""
-- ✅ Authorized Lua script
print("Welcome user ID: {user_id}")
-- Your actual script starts here
print("This is a protected Lua script.")
"""

    return Response(lua_code, mimetype='text/plain')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
