#!/usr/bin/env python3
from flask import Flask, request
import subprocess
import sys

app = Flask(__name__)

@app.route("/<path:subpath>")
def proxy(subpath):
    user_agent = request.headers.get("User-Agent", "")
    result = subprocess.run(
        ["/opt/remna-sub-injector/inject-proxy.sh", f"/{subpath}", user_agent],
        capture_output=True,
        text=True
    )
    return result.stdout, 200, {"Content-Type": "text/plain"}

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=3020)
