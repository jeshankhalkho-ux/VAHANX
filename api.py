import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = "TBEH-API-KEY-2024"
BASE_URL = "https://api.vehicleinfo.com/v1"

HEADERS = {
    "x-api-key": API_KEY,
    "Accept": "application/json"
}

# ===============================================
# ROUTES
# ===============================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "Vehicle RC Lookup API",
        "status": "online",
        "endpoint": "/api/rc?number=DL01AB1234"
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})

@app.route("/api/rc", methods=["GET"])
def vehicle_lookup():
    number = request.args.get("number", "").strip().upper()

    if not number:
        return jsonify({
            "error": "Missing parameter",
            "usage": "/api/rc?number=DL01AB1234"
        }), 400

    try:
        response = requests.get(
            f"{BASE_URL}/{number}",
            headers=HEADERS,
            timeout=10
        )
        data = response.json()
        return jsonify({
            "success": True,
            "data": data
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ===============================================
# RUN
# ===============================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
