import sys
import asyncio
import base64

# Fix asyncio WinError 10054 socket shutdown noise on Windows
if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

import streamlit as st
import numpy as np
import pickle
import os

# Set up simple page configuration
st.set_page_config(
    page_title="Nimbus Predict",
    page_icon="🌍",
    layout="centered"
)

# Custom Premium Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    .card {
        background-color: rgba(30, 41, 59, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 25px !important;
        margin-bottom: 20px !important;
        backdrop-filter: blur(12px) !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.25) !important;
    }
    .main-header {
        font-size: 2.8rem;
        background: linear-gradient(135deg, #00F2FE 0%, #4FACFE 50%, #00C6FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        margin: 0;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to encode image as base64 string
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

# Renders the Logo and "Nimbus Predict" text side-by-side at the very top of the app
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
logo_file = os.path.join(CURRENT_DIR, "nimbus_predict_logo.png")

if os.path.exists(logo_file):
    img_b64 = get_base64_image(logo_file)
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; justify-content: center; gap: 20px; margin-bottom: 25px; margin-top: 15px;">
            <img src="data:image/png;base64,{img_b64}" style="width: 75px; height: 75px; border-radius: 14px; box-shadow: 0 4px 15px rgba(0,242,254,0.3);"/>
            <h1 style="
                font-size: 3rem;
                background: linear-gradient(135deg, #00F2FE 0%, #4FACFE 50%, #00C6FF 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-weight: 700;
                margin: 0;
                font-family: 'Outfit', sans-serif;
            ">Nimbus Predict</h1>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown("<h1 class='main-header'>Nimbus Predict</h1>", unsafe_allow_html=True)

st.markdown("---")

# Initialize Session State values
if "started" not in st.session_state:
    st.session_state.started = False

for prefix in ["flood", "heatwave"]:
    if f"{prefix}_lat_input" not in st.session_state:
        st.session_state[f"{prefix}_lat_input"] = 20.5937
    if f"{prefix}_lon_input" not in st.session_state:
        st.session_state[f"{prefix}_lon_input"] = 78.9629
    if f"{prefix}_prev_country" not in st.session_state:
        st.session_state[f"{prefix}_prev_country"] = "India"
    if f"{prefix}_prev_state" not in st.session_state:
        st.session_state[f"{prefix}_prev_state"] = "Andhra Pradesh"
    if f"{prefix}_prev_geo_method" not in st.session_state:
        st.session_state[f"{prefix}_prev_geo_method"] = "By Country"

# Dictionary of major countries mapped to representative (Latitude, Longitude) coordinates
COUNTRY_COORDINATES = {
    "India": (20.5937, 78.9629),
    "United States": (37.0902, -95.7129),
    "Brazil": (-14.2350, -51.9253),
    "Australia": (-25.2744, 133.7751),
    "United Kingdom": (55.3781, -3.4360),
    "Canada": (56.1304, -106.3468),
    "Japan": (36.2048, 138.2529),
    "Germany": (51.1657, 10.4515),
    "South Africa": (-30.5595, 22.9375),
    "Russia": (61.5240, 105.3188),
    "China": (35.8617, 104.1954),
    "Egypt": (26.8206, 30.8025),
    "France": (46.2276, 2.2137),
    "Italy": (41.8719, 12.5674),
    "Mexico": (23.6345, -102.5528)
}

# Dictionary of Indian states mapped to representative (Latitude, Longitude) coordinates
STATE_COORDINATES = {
    "Andhra Pradesh": (15.97, 79.74),
    "Arunachal Pradesh": (28.21, 94.72),
    "Assam": (26.20, 92.93),
    "Bihar": (25.09, 85.31),
    "Chhattisgarh": (21.27, 81.86),
    "Delhi": (28.70, 77.20),
    "Goa": (15.29, 74.12),
    "Gujarat": (22.25, 71.19),
    "Haryana": (29.05, 76.08),
    "Himachal Pradesh": (31.10, 77.17),
    "Jammu & Kashmir": (33.77, 76.57),
    "Jharkhand": (23.61, 85.56),
    "Karnataka": (15.31, 75.71),
    "Kerala": (10.85, 76.27),
    "Madhya Pradesh": (22.97, 78.65),
    "Maharashtra": (19.75, 75.71),
    "Manipur": (24.66, 93.90),
    "Meghalaya": (25.46, 91.36),
    "Mizoram": (23.16, 92.93),
    "Nagaland": (26.15, 94.56),
    "Odisha": (20.95, 83.38),
    "Punjab": (31.14, 75.34),
    "Rajasthan": (27.02, 74.21),
    "Sikkim": (27.53, 88.51),
    "Tamil Nadu": (11.12, 78.65),
    "Telangana": (18.11, 79.01),
    "Tripura": (23.94, 91.98),
    "Uttar Pradesh": (26.84, 80.88),
    "Uttarakhand": (30.06, 79.01),
    "West Bengal": (22.98, 87.85)
}

def get_closest_country(lat, lon):
    """Calculate the closest Country based on coordinate proximity."""
    closest_country = None
    min_dist = float('inf')
    for country, coords in COUNTRY_COORDINATES.items():
        dist = np.sqrt((lat - coords[0])**2 + (lon - coords[1])**2)
        if dist < min_dist:
            min_dist = dist
            closest_country = country
    return closest_country

def get_closest_state(lat, lon):
    """Calculate the closest Indian state based on coordinate proximity."""
    closest_state = None
    min_dist = float('inf')
    for state, coords in STATE_COORDINATES.items():
        dist = np.sqrt((lat - coords[0])**2 + (lon - coords[1])**2)
        if dist < min_dist:
            min_dist = dist
            closest_state = state
    return closest_state

# ----------------- Model Loader Functions -----------------

FLOOD_MODEL_PATH = os.path.join(CURRENT_DIR, "flood_prediction.pkl")
HEATWAVE_MODEL_PATH = os.path.join(CURRENT_DIR, "heatwave_prediction.pkl")

@st.cache_resource
def load_flood_model():
    """Loads the pre-trained flood model from disk using pickle."""
    if not os.path.exists(FLOOD_MODEL_PATH):
        return None, f"Model file not found: {FLOOD_MODEL_PATH}"
    try:
        with open(FLOOD_MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        return model, None
    except Exception as e:
        return None, str(e)

@st.cache_resource
def load_heatwave_model():
    """Loads the pre-trained heatwave model from disk using pickle."""
    if not os.path.exists(HEATWAVE_MODEL_PATH):
        return None, f"Model file not found: {HEATWAVE_MODEL_PATH}"
    try:
        with open(HEATWAVE_MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        return model, None
    except Exception as e:
        return None, str(e)

# ----------------- Fallback Predictor Logic -----------------

def predict_flood_fallback(inputs):
    # inputs array: [rainfall, river_level, humidity, temperature]
    rainfall = inputs[0, 0]
    river_level = inputs[0, 1]
    humidity = inputs[0, 2]
    temperature = inputs[0, 3]
    
    score = (rainfall * 0.4) + (river_level * 1.5) + (humidity * 0.1) - (temperature * 0.05)
    return 1 if score >= 25 else 0

def predict_heatwave_fallback(inputs):
    # inputs array: [temperature, humidity, wind_speed, pressure]
    temperature = inputs[0, 0]
    humidity = inputs[0, 1]
    wind_speed = inputs[0, 2]
    pressure = inputs[0, 3]
    
    score = (temperature - 30) * 0.6 + (humidity - 65) * 0.1 - wind_speed * 0.05
    return 1 if score >= 3.5 else 0

# ----------------- Page Flow Routing -----------------

if not st.session_state.started:
    # Welcome landing screen (Frameless, clean background)
    st.markdown("<div style='text-align: center; margin-top: 30px;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='color: #F8FAFC;'>Hazard Assessment Suite</h3>", unsafe_allow_html=True)
    st.write(
        "Evaluate localized environmental vulnerabilities using pre-trained machine learning classifiers. "
        "Click the button below to initialize the system and configure inputs."
    )
    
    if st.button("Start Prediction", type="primary", width='stretch'):
        st.session_state.started = True
        st.rerun()
        
    st.markdown("</div>", unsafe_allow_html=True)

else:
    st.sidebar.markdown("<h3 style='color:#00F2FE;'>Options</h3>", unsafe_allow_html=True)
    if st.sidebar.button("🏠 Back to Home", width='stretch'):
        st.session_state.started = False
        st.rerun()

    # Dropdown selector
    selected_hazard = st.selectbox(
        "Choose hazard prediction module:",
        ["Flood Prediction", "Heatwave Prediction"]
    )

    st.markdown("---")

    # ----------------- Forms -----------------

    if selected_hazard == "Flood Prediction":
        st.header("🌊 Flood Prediction")
        
        model, err = load_flood_model()
        if err:
            st.info("💡 Note: Running in fallback mode (using heuristic logic).")
        else:
            st.success("✅ Model loaded successfully from root folder.")

        st.subheader("Geographical Settings")
        
        geo_method = st.radio(
            "Coordinate Entry Method:",
            ["By Country", "By Indian State", "Custom Coordinate Entry"],
            horizontal=True,
            key="flood_geo_method"
        )

        # Update session states directly if the entry method changes
        if geo_method != st.session_state.flood_prev_geo_method:
            st.session_state.flood_prev_geo_method = geo_method
            if geo_method == "By Country":
                st.session_state.flood_lat_input, st.session_state.flood_lon_input = COUNTRY_COORDINATES[st.session_state.get("flood_country_select", "India")]
            elif geo_method == "By Indian State":
                st.session_state.flood_lat_input, st.session_state.flood_lon_input = STATE_COORDINATES[st.session_state.get("flood_state_select", "Andhra Pradesh")]
            else:
                st.session_state.flood_lat_input = 22.0
                st.session_state.flood_lon_input = 80.0

        if geo_method == "By Country":
            country_option = st.selectbox("Select Country:", list(COUNTRY_COORDINATES.keys()), key="flood_country_select")
            if country_option != st.session_state.flood_prev_country:
                st.session_state.flood_lat_input, st.session_state.flood_lon_input = COUNTRY_COORDINATES[country_option]
                st.session_state.flood_prev_country = country_option
            st.info(f"📍 Coordinates loaded for Country: **{country_option}**")
            
        elif geo_method == "By Indian State":
            state_option = st.selectbox("Select Indian State:", list(STATE_COORDINATES.keys()), key="flood_state_select")
            if state_option != st.session_state.flood_prev_state:
                st.session_state.flood_lat_input, st.session_state.flood_lon_input = STATE_COORDINATES[state_option]
                st.session_state.flood_prev_state = state_option
            st.info(f"📍 Coordinates loaded for State: **{state_option}**")

        # Bind the number_inputs directly to the session state keys
        lat = st.number_input(
            "Latitude (°N/°S)", 
            min_value=-90.0, 
            max_value=90.0, 
            step=0.1, 
            key="flood_lat_input"
        )
        lon = st.number_input(
            "Longitude (°E/°W)", 
            min_value=-180.0, 
            max_value=180.0, 
            step=0.1, 
            key="flood_lon_input"
        )

        if geo_method == "Custom Coordinate Entry":
            closest_country = get_closest_country(lat, lon)
            closest_state = get_closest_state(lat, lon)
            st.info(f"📍 Proximity: Closest Country is **{closest_country}** | Closest Indian State is **{closest_state}**")

        st.markdown("---")
        st.subheader("Meteorological & Environmental Variables")
        rainfall = st.number_input("Rainfall (mm)", min_value=0.0, value=25.0)
        river_level = st.number_input("River Level (m)", min_value=0.0, value=2.1)
        humidity = st.number_input("Humidity (%)", min_value=0.0, max_value=100.0, value=65.0)
        temperature = st.number_input("Temperature (°C)", value=24.5)

        input_data = np.array([[rainfall, river_level, humidity, temperature]])

        if st.button("Predict Flood Risk", type="primary", width='stretch'):
            pred = None
            if model is not None:
                try:
                    pred = model.predict(input_data)[0]
                except Exception:
                    pred = predict_flood_fallback(input_data)
            else:
                pred = predict_flood_fallback(input_data)
                
            if pred == 1:
                st.error("🚨 Danger: Flood Risk Detected!")
            else:
                st.success("🟢 Safe: No Flood Risk Detected.")

    elif selected_hazard == "Heatwave Prediction":
        st.header("🔥 Heatwave Prediction")
        
        model, err = load_heatwave_model()
        if err:
            st.info("💡 Note: Running in fallback mode (using heuristic logic).")
        else:
            st.success("✅ Model loaded successfully from root folder.")

        st.subheader("Geographical Settings")
        
        geo_method = st.radio(
            "Coordinate Entry Method:",
            ["By Country", "By Indian State", "Custom Coordinate Entry"],
            horizontal=True,
            key="heatwave_geo_method"
        )

        if geo_method != st.session_state.heatwave_prev_geo_method:
            st.session_state.heatwave_prev_geo_method = geo_method
            if geo_method == "By Country":
                st.session_state.heatwave_lat_input, st.session_state.heatwave_lon_input = COUNTRY_COORDINATES[st.session_state.get("heatwave_country_select", "India")]
            elif geo_method == "By Indian State":
                st.session_state.heatwave_lat_input, st.session_state.heatwave_lon_input = STATE_COORDINATES[st.session_state.get("heatwave_state_select", "Andhra Pradesh")]
            else:
                st.session_state.heatwave_lat_input = 22.0
                st.session_state.heatwave_lon_input = 80.0

        if geo_method == "By Country":
            country_option = st.selectbox("Select Country:", list(COUNTRY_COORDINATES.keys()), key="heatwave_country_select")
            if country_option != st.session_state.heatwave_prev_country:
                st.session_state.heatwave_lat_input, st.session_state.heatwave_lon_input = COUNTRY_COORDINATES[country_option]
                st.session_state.heatwave_prev_country = country_option
            st.info(f"📍 Coordinates loaded for Country: **{country_option}**")
            
        elif geo_method == "By Indian State":
            state_option = st.selectbox("Select Indian State:", list(STATE_COORDINATES.keys()), key="heatwave_state_select")
            if state_option != st.session_state.heatwave_prev_state:
                st.session_state.heatwave_lat_input, st.session_state.heatwave_lon_input = STATE_COORDINATES[state_option]
                st.session_state.heatwave_prev_state = state_option
            st.info(f"📍 Coordinates loaded for State: **{state_option}**")

        # Bind the number_inputs directly to the session state keys
        lat = st.number_input(
            "Latitude (°N/°S)", 
            min_value=-90.0, 
            max_value=90.0, 
            step=0.1, 
            key="heatwave_lat_input"
        )
        lon = st.number_input(
            "Longitude (°E/°W)", 
            min_value=-180.0, 
            max_value=180.0, 
            step=0.1, 
            key="heatwave_lon_input"
        )

        if geo_method == "Custom Coordinate Entry":
            closest_country = get_closest_country(lat, lon)
            closest_state = get_closest_state(lat, lon)
            st.info(f"📍 Proximity: Closest Country is **{closest_country}** | Closest Indian State is **{closest_state}**")

        st.markdown("---")
        st.subheader("Meteorological Variables")
        temperature = st.number_input("Temperature (°C)", value=38.5)
        humidity = st.number_input("Humidity (%)", min_value=0.0, max_value=100.0, value=55.0)
        wind_speed = st.number_input("Wind Speed (km/h)", min_value=0.0, value=12.0)
        pressure = st.number_input("Pressure (hPa)", min_value=900.0, max_value=1100.0, value=1008.0)

        input_data = np.array([[temperature, humidity, wind_speed, pressure]])

        if st.button("Predict Heatwave Risk", type="primary", width='stretch'):
            pred = None
            if model is not None:
                try:
                    pred = model.predict(input_data)[0]
                except Exception:
                    pred = predict_heatwave_fallback(input_data)
            else:
                pred = predict_heatwave_fallback(input_data)
                
            if pred == 1:
                st.error("🚨 Danger: Heatwave Alert Active!")
            else:
                st.success("🟢 Safe: Normal Temperatures.")
