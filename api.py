import os
import pickle
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing for React frontend integrations

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FLOOD_MODEL_PATH = os.path.join(CURRENT_DIR, "flood_prediction.pkl")
HEATWAVE_MODEL_PATH = os.path.join(CURRENT_DIR, "heatwave_prediction.pkl")

# Load models at startup
models = {}

try:
    if os.path.exists(FLOOD_MODEL_PATH):
        with open(FLOOD_MODEL_PATH, "rb") as f:
            models["flood"] = pickle.load(f)
        print("✅ Flood model loaded successfully.")
    else:
        print("⚠️ Flood model file not found. Fallback heuristics will be used.")
except Exception as e:
    print(f"❌ Error loading flood model: {e}")

try:
    if os.path.exists(HEATWAVE_MODEL_PATH):
        with open(HEATWAVE_MODEL_PATH, "rb") as f:
            models["heatwave"] = pickle.load(f)
        print("✅ Heatwave model loaded successfully.")
    else:
        print("⚠️ Heatwave model file not found. Fallback heuristics will be used.")
except Exception as e:
    print(f"❌ Error loading heatwave model: {e}")

# Fallback prediction heuristics
def predict_flood_fallback(rainfall, river_level, humidity, temperature):
    score = (rainfall * 0.4) + (river_level * 1.5) + (humidity * 0.1) - (temperature * 0.05)
    pred = 1 if score >= 25 else 0
    distance = abs(score - 25)
    confidence = min(98.0, 50.0 + (distance / 20.0) * 48.0)
    return pred, confidence

def predict_heatwave_fallback(temperature, humidity, wind_speed, pressure):
    score = (temperature - 30) * 0.6 + (humidity - 65) * 0.1 - wind_speed * 0.05
    pred = 1 if score >= 3.5 else 0
    distance = abs(score - 3.5)
    confidence = min(98.0, 50.0 + (distance / 5.0) * 48.0)
    return pred, confidence

# Dynamic Content and Recommendations Maps
CONTENT = {
    "heatwave": {
        "low": {
            "reason": "Meteorological factors indicate ambient temperatures and air pressure are well within normal ranges. No immediate risk of heatwave conditions.",
            "cure": "No special actions required. Continue regular weather monitoring. Stay hydrated and enjoy the day."
        },
        "moderate": {
            "reason": "Slight elevations in temperature and humidity suggest a possibility of heat stress. Atmospheric patterns show potential for warming.",
            "cure": "Limit prolonged outdoor activities in peak afternoon hours. Drink adequate fluids. Ensure domestic cooling systems are functional."
        },
        "high": {
            "reason": "Substantial warming trend detected with rising temperatures and stagnant air movement. Thermal indexes are reaching warning levels.",
            "cure": "Stay indoors during peak solar hours. Avoid strenuous physical labor. Drink plenty of water and electrolytes. Keep indoor areas shaded."
        },
        "severe": {
            "reason": "Critical thermal emergency. Extreme atmospheric temperatures coupled with dry or humid air currents have triggered dangerous conditions.",
            "cure": "Stay indoors in air-conditioned spaces. Avoid all direct sun exposure. Keep emergency cooling packs ready. Check on elderly neighbors and pets immediately."
        }
    },
    "flood": {
        "low": {
            "reason": "Current precipitation and river gauges are well within safe operating thresholds. Natural soil absorption and drainage channels are fully functional.",
            "cure": "No immediate threat. Perform standard clearing of localized rain gutters. Keep updated with routine meteorological bulletins."
        },
        "moderate": {
            "reason": "Elevated precipitation levels or high upstream runoff is beginning to saturate local catchments. River basins are filling up.",
            "cure": "Monitor local water levels. Secure ground-level inventory. Ensure emergency emergency kits are accessible."
        },
        "high": {
            "reason": "Heavy rainfall combined with saturated soil conditions is overwhelming local drainage networks. Stream and river levels are approaching danger marks.",
            "cure": "Prepare to evacuate low-lying structures. Move valuable belongings to upper floors. Block doorways with sandbags if available."
        },
        "severe": {
            "reason": "Extreme hydrologic event. Critical rainfall totals and overflowing water bodies have exceeded all drainage and flood-defense capacities.",
            "cure": "Evacuate low-lying areas immediately. Do not attempt to walk or drive through flowing water. Move to high ground and await official rescue instructions."
        }
    }
}

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400

    hazard = data.get("hazard", "").lower()
    if hazard not in ["flood", "heatwave"]:
        return jsonify({"error": "Invalid or missing hazard type. Must be 'flood' or 'heatwave'"}), 400

    # Run predictions based on hazard type
    if hazard == "flood":
        # Extract inputs with defaults
        rainfall = float(data.get("rainfall", 25.0))
        river_level = float(data.get("river_level", 2.1))
        humidity = float(data.get("humidity", 65.0))
        temperature = float(data.get("temperature", 24.5))
        
        input_array = np.array([[rainfall, river_level, humidity, temperature]])
        
        model = models.get("flood")
        pred = None
        confidence = 85.0
        
        if model is not None:
            try:
                pred = int(model.predict(input_array)[0])
                if hasattr(model, "predict_proba"):
                    prob = model.predict_proba(input_array)[0]
                    confidence = float(prob[pred]) * 100
            except Exception as e:
                print(f"Fallback run due to model prediction error: {e}")
                pred, confidence = predict_flood_fallback(rainfall, river_level, humidity, temperature)
        else:
            pred, confidence = predict_flood_fallback(rainfall, river_level, humidity, temperature)
            
    else:  # heatwave
        # Extract inputs with defaults
        temperature = float(data.get("temperature", 38.5))
        humidity = float(data.get("humidity", 55.0))
        wind_speed = float(data.get("wind_speed", 12.0))
        pressure = float(data.get("pressure", 1008.0))
        
        input_array = np.array([[temperature, humidity, wind_speed, pressure]])
        
        model = models.get("heatwave")
        pred = None
        confidence = 85.0
        
        if model is not None:
            try:
                pred = int(model.predict(input_array)[0])
                if hasattr(model, "predict_proba"):
                    prob = model.predict_proba(input_array)[0]
                    confidence = float(prob[pred]) * 100
            except Exception as e:
                print(f"Fallback run due to model prediction error: {e}")
                pred, confidence = predict_heatwave_fallback(temperature, humidity, wind_speed, pressure)
        else:
            pred, confidence = predict_heatwave_fallback(temperature, humidity, wind_speed, pressure)

    # Compute risk level and visual indicators based on confidence thresholds
    # If pred is 1 (hazard), danger confidence matches confidence.
    # If pred is 0 (safe), danger confidence is 100 - confidence.
    hazard_confidence = confidence if pred == 1 else (100.0 - confidence)
    hazard_confidence = max(0.0, min(100.0, hazard_confidence))

    if hazard_confidence < 50.0:
        level_key = "low"
        risk_level = "Low Risk"
        color = "#10b981"  # Emerald Green
        icon = "✅"
        status_message = f"No Significant {hazard.capitalize()} Risk Detected"
    elif hazard_confidence < 70.0:
        level_key = "moderate"
        risk_level = "Moderate Risk"
        color = "#f97316"  # Orange
        icon = "⚠️"
        status_message = f"{hazard.capitalize()} Conditions Possible"
    elif hazard_confidence < 85.0:
        level_key = "high"
        risk_level = "High Risk"
        color = "#ef4444"  # Red
        icon = "🌊" if hazard == "flood" else "🔥"
        status_message = f"High {hazard.capitalize()} Risk Detected"
    else:
        level_key = "severe"
        risk_level = "Severe Alert"
        color = "#b91c1c"  # Dark Red / Crimson
        icon = "🚨"
        status_message = f"Danger: {hazard.capitalize()} Alert Active"

    # Fetch corresponding analysis and recommendations from content maps
    hazard_content = CONTENT.get(hazard, {}).get(level_key, {"reason": "", "cure": ""})
    analysis = hazard_content["reason"]
    recommendations = hazard_content["cure"]

    response = {
        "prediction": pred,
        "probability": round(hazard_confidence, 1),
        "risk_level": risk_level,
        "color": color,
        "icon": icon,
        "status_message": status_message,
        "analysis": analysis,
        "recommendations": recommendations
    }

    return jsonify(response)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "flood_model_loaded": "flood" in models, "heatwave_model_loaded": "heatwave" in models})

if __name__ == "__main__":
    # Run server locally on port 5000
    app.run(host="0.0.0.0", port=5000, debug=True)
