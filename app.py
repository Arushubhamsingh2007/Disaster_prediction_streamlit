import sys
import asyncio
import base64

# Fix asyncio WinError 10054 socket shutdown noise on Windows
if sys.platform == 'win32':
    try:
        # Silently discard ConnectionResetError (WinError 10054) on Proactor event loops
        from asyncio.proactor_events import _ProactorBasePipeTransport
        if not hasattr(_ProactorBasePipeTransport._call_connection_lost, '_patched'):
            _orig_call_connection_lost = _ProactorBasePipeTransport._call_connection_lost
            
            def _patched_call_connection_lost(self, exc):
                if isinstance(exc, ConnectionResetError):
                    return
                _orig_call_connection_lost(self, exc)
                
            _patched_call_connection_lost._patched = True
            _ProactorBasePipeTransport._call_connection_lost = _patched_call_connection_lost
        
        # Force WindowsSelectorEventLoopPolicy where supported
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
    layout="wide"
)

# Custom Premium Styling (Cloudy Weather Theme)
st.markdown("""
<div class="clouds-container">
    <div class="cloud cloud-1"></div>
    <div class="cloud cloud-2"></div>
    <div class="cloud cloud-3"></div>
</div>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    html, body, [class*="css"], .stApp {
        font-family: 'Outfit', 'Plus Jakarta Sans', sans-serif;
        color: #f8fafc !important;
    }
    
    /* Background with shifting stormy gradient */
    .stApp {
        background: radial-gradient(circle at top, #1e293b 0%, #0f172a 70%, #020617 100%) !important;
        background-attachment: fixed !important;
    }
    
    /* Clouds Overlay */
    .clouds-container {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        overflow: hidden;
        z-index: 0;
        pointer-events: none;
    }
    
    .cloud {
        position: absolute;
        background: radial-gradient(circle, rgba(148, 163, 184, 0.08) 0%, rgba(30, 41, 59, 0.01) 70%);
        border-radius: 50%;
        filter: blur(60px);
    }
    
    .cloud-1 {
        width: 700px;
        height: 350px;
        top: -10%;
        left: -15%;
        animation: drift 75s linear infinite alternate;
    }
    
    .cloud-2 {
        width: 900px;
        height: 450px;
        top: 30%;
        right: -25%;
        animation: drift-reverse 90s linear infinite alternate;
    }
    
    .cloud-3 {
        width: 600px;
        height: 300px;
        bottom: -10%;
        left: 15%;
        animation: drift 60s linear infinite alternate;
    }
    
    @keyframes drift {
        0% { transform: translate(0, 0) scale(1); }
        100% { transform: translate(150px, 80px) scale(1.15); }
    }
    
    @keyframes drift-reverse {
        0% { transform: translate(0, 0) scale(1); }
        100% { transform: translate(-200px, -60px) scale(1.2); }
    }
    
    /* Glassmorphic Parameter Frames (Containers with border) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(30, 41, 59, 0.35) !important;
        backdrop-filter: blur(16px) !important;
        border: 1px solid rgba(148, 163, 184, 0.12) !important;
        border-radius: 20px !important;
        padding: 24px 28px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
        margin-bottom: 25px !important;
        transition: border-color 0.3s ease, box-shadow 0.3s ease !important;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(14, 165, 233, 0.25) !important;
        box-shadow: 0 12px 35px rgba(14, 165, 233, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
    }
    
    /* Sidebar Overrides */
    section[data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.7) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button {
        background: rgba(30, 41, 59, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Input Fields (Numbers, Text, Selectboxes) */
    div[data-baseweb="input"] {
        background-color: rgba(15, 23, 42, 0.5) !important;
        border: 1px solid rgba(148, 163, 184, 0.2) !important;
        border-radius: 12px !important;
        color: #f8fafc !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    div[data-baseweb="input"]:focus-within {
        border-color: #38bdf8 !important;
        box-shadow: 0 0 12px rgba(56, 189, 248, 0.25) !important;
        background-color: rgba(15, 23, 42, 0.7) !important;
    }
    
    div[data-baseweb="select"] {
        background-color: rgba(15, 23, 42, 0.5) !important;
        border: 1px solid rgba(148, 163, 184, 0.2) !important;
        border-radius: 12px !important;
        color: #f8fafc !important;
    }
    
    div[data-baseweb="select"] > div {
        background-color: transparent !important;
        color: #f8fafc !important;
    }
    
    /* Buttons Customization */
    div.stButton > button {
        background: linear-gradient(135deg, #334155 0%, #1e293b 100%) !important;
        color: #f8fafc !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2) !important;
        width: 100% !important;
    }
    
    div.stButton > button:hover {
        background: linear-gradient(135deg, #475569 0%, #334155 100%) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
        box-shadow: 0 6px 20px rgba(148, 163, 184, 0.15) !important;
        transform: translateY(-2px) !important;
    }
    
    div.stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* Primary buttons with animated cloud-glowing gradients */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        box-shadow: 0 4px 20px rgba(14, 165, 233, 0.3) !important;
    }
    
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #38bdf8 0%, #3b82f6 100%) !important;
        box-shadow: 0 6px 25px rgba(56, 189, 248, 0.45) !important;
    }
    
    /* Radio elements */
    div[data-testid="stRadio"] label {
        color: #cbd5e1 !important;
        font-weight: 500 !important;
    }
    
    div[data-testid="stRadio"] label[data-baseweb="radio"] div {
        border-color: rgba(148, 163, 184, 0.4) !important;
    }
    
    /* Header and Subheader Customizations */
    .main-header {
        font-size: 3rem;
        background: linear-gradient(135deg, #e2e8f0 0%, #94a3b8 50%, #64748b 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        margin: 0;
        text-align: center;
        text-shadow: 0 10px 30px rgba(0,0,0,0.15);
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #f1f5f9 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 600 !important;
    }
    
    /* Alerts and custom containers */
    div[data-testid="stAlert"] {
        background: rgba(15, 23, 42, 0.6) !important;
        backdrop-filter: blur(12px) !important;
        border-radius: 14px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2) !important;
    }
    
    div[data-testid="stAlert"] [role="alert"] {
        background-color: transparent !important;
        color: #f1f5f9 !important;
    }
    
    /* Welcome Card */
    .welcome-card {
        background: rgba(30, 41, 59, 0.35) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(148, 163, 184, 0.15) !important;
        border-radius: 24px !important;
        padding: 40px 30px !important;
        text-align: center;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3) !important;
        margin: 30px auto !important;
        max-width: 600px;
        animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1);
    }
    
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .welcome-header {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
        margin-bottom: 20px;
    }
    
    .weather-icon {
        font-size: 4rem;
        animation: float 4s ease-in-out infinite;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-12px); }
    }
    
    .welcome-header h3 {
        font-size: 1.8rem;
        color: #f8fafc;
        margin: 0;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    .welcome-description {
        font-size: 1.05rem;
        color: #cbd5e1;
        line-height: 1.6;
        margin-bottom: 30px;
    }
    
    .feature-pills {
        display: flex;
        justify-content: center;
        gap: 10px;
        flex-wrap: wrap;
        margin-bottom: 10px;
    }
    
    .pill {
        background: rgba(148, 163, 184, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.05);
        color: #cbd5e1;
        padding: 8px 16px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 500;
        transition: background 0.3s ease;
    }
    
    .pill:hover {
        background: rgba(14, 165, 233, 0.15);
        border-color: rgba(14, 165, 233, 0.3);
    }
    
    /* Dialog / Modal Overrides */
    div[role="dialog"] {
        background-color: rgba(15, 23, 42, 0.95) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(148, 163, 184, 0.25) !important;
        border-radius: 24px !important;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6), 0 0 40px rgba(56, 189, 248, 0.15) !important;
        padding: 30px !important;
    }
    
    div[role="dialog"] h2 {
        color: #f8fafc !important;
        font-weight: 700 !important;
        border-bottom: 1px solid rgba(148, 163, 184, 0.15) !important;
        padding-bottom: 15px !important;
        margin-bottom: 20px !important;
    }
    
    .result-badge {
        padding: 8px 16px !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 8px !important;
    }
    
    .badge-low {
        background: rgba(16, 185, 129, 0.15) !important;
        border: 1px solid rgba(16, 185, 129, 0.4) !important;
        color: #a7f3d0 !important;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.2) !important;
    }
    
    .badge-moderate {
        background: rgba(249, 115, 22, 0.15) !important;
        border: 1px solid rgba(249, 115, 22, 0.4) !important;
        color: #fdba74 !important;
        box-shadow: 0 0 15px rgba(249, 115, 22, 0.2) !important;
    }
    
    .badge-high {
        background: rgba(239, 68, 68, 0.15) !important;
        border: 1px solid rgba(239, 68, 68, 0.4) !important;
        color: #fca5a5 !important;
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.2) !important;
    }
    
    .badge-severe {
        background: rgba(153, 27, 27, 0.25) !important;
        border: 1px solid rgba(239, 68, 68, 0.7) !important;
        color: #fee2e2 !important;
        box-shadow: 0 0 15px rgba(153, 27, 27, 0.3) !important;
    }

    .progress-container {
        width: 100%;
        background-color: rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        height: 10px !important;
        margin-bottom: 25px !important;
        overflow: hidden !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    
    .progress-bar {
        height: 100% !important;
        border-radius: 8px !important;
        transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    .confidence-container {
        background: rgba(148, 163, 184, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 14px !important;
        padding: 12px 18px !important;
        margin-bottom: 20px !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
    }
    
    .confidence-label {
        font-size: 0.95rem !important;
        color: #94a3b8 !important;
    }
    
    .confidence-value {
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        color: #38bdf8 !important;
    }
    
    .section-title {
        font-weight: 600 !important;
        font-size: 1rem !important;
        color: #f1f5f9 !important;
        margin-top: 15px !important;
        margin-bottom: 8px !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
    }
    
    .section-text {
        font-size: 0.95rem !important;
        line-height: 1.5 !important;
        color: #94a3b8 !important;
        margin-bottom: 15px !important;
    }
    
    /* Landing Page - Floating Brand Container */
    .brand-container {
        background: radial-gradient(circle at top left, rgba(30, 41, 59, 0.45), rgba(15, 23, 42, 0.65)) !important;
        border: 1px solid rgba(148, 163, 184, 0.18) !important;
        border-radius: 28px !important;
        padding: 50px 35px !important;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
        text-align: center;
        margin-top: 35px;
        animation: floatBrand 6s ease-in-out infinite;
    }
    
    @keyframes floatBrand {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
    
    .brand-chip {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.85) 0%, rgba(30, 41, 59, 0.85) 100%) !important;
        border: 1px solid rgba(56, 189, 248, 0.25) !important;
        border-radius: 20px !important;
        padding: 30px 20px !important;
        margin-bottom: 25px !important;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.35), 0 0 35px rgba(56, 189, 248, 0.12) !important;
    }
    
    .brand-title {
        font-size: 3.2rem !important;
        background: linear-gradient(135deg, #cbd5e1 0%, #94a3b8 50%, #38bdf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        margin: 15px 0 0 0 !important;
        font-family: 'Plus Jakarta Sans', 'Outfit', sans-serif !important;
        text-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
    }
    
    .brand-tagline {
        font-size: 0.95rem !important;
        color: #94a3b8 !important;
        font-weight: 700 !important;
        letter-spacing: 1.5px !important;
        text-transform: uppercase !important;
        margin-top: 15px !important;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.4);
    }
    
    /* Landing Page - Interactive Gateway */
    .gateway-container {
        padding: 40px 30px !important;
        margin-top: 40px;
        animation: fadeInUpGateway 0.8s cubic-bezier(0.16, 1, 0.3, 1);
    }
    
    @keyframes fadeInUpGateway {
        from { opacity: 0; transform: translateY(15px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .gateway-header {
        font-size: 1.8rem !important;
        color: #f8fafc !important;
        font-weight: 700 !important;
        margin-bottom: 20px !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    
    .gateway-description {
        font-size: 1.05rem !important;
        color: #cbd5e1 !important;
        line-height: 1.7 !important;
        margin-bottom: 30px !important;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to encode image as base64 string
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

# ----------------- Dialog Result Window -----------------
@st.dialog("Prediction Outcome")
def show_prediction_dialog(res):
    hazard = res.get("hazard", "heatwave")
    pred = res.get("pred", 0)
    raw_confidence = res.get("confidence", 50.0)
    
    # Calculate hazard confidence
    # If pred == 1, confidence of hazard is the model's confidence.
    # If pred == 0, confidence of hazard is 100 - confidence of safety.
    hazard_confidence = raw_confidence if pred == 1 else (100.0 - raw_confidence)
    hazard_confidence = max(0.0, min(100.0, hazard_confidence))
    
    # Define thresholds
    if hazard_confidence < 50.0:
        level_key = "low"
        risk_level = "Low Risk"
        badge_icon = "✅"
        badge_class = "badge-low"
        bar_color = "#10b981"  # Green
        status = f"No Significant {hazard.capitalize()} Risk Detected"
    elif hazard_confidence < 70.0:
        level_key = "moderate"
        risk_level = "Moderate Risk"
        badge_icon = "⚠️"
        badge_class = "badge-moderate"
        bar_color = "#f97316"  # Orange
        status = f"{hazard.capitalize()} Conditions Possible"
    elif hazard_confidence < 85.0:
        level_key = "high"
        risk_level = "High Risk"
        badge_icon = "🌊" if hazard == "flood" else "🔥"
        badge_class = "badge-high"
        bar_color = "#ef4444"  # Red
        status = f"High {hazard.capitalize()} Risk Detected"
    else:
        level_key = "severe"
        risk_level = "Severe Alert"
        badge_icon = "🚨"
        badge_class = "badge-severe"
        bar_color = "#b91c1c"  # Dark Red
        status = f"Danger: {hazard.capitalize()} Alert Active"

    # Dynamic reasons & recommendations
    content = {
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
    
    selected_content = content[hazard][level_key]
    reason = selected_content["reason"]
    cure = selected_content["cure"]
    
    st.markdown(
        f"""
        <div style="margin-bottom: 25px; margin-top: -10px;">
            <span class="result-badge {badge_class}">
                {badge_icon} {status}
            </span>
        </div>
        <div class="confidence-container">
            <span class="confidence-label">{hazard.capitalize()} Risk Level</span>
            <span class="confidence-value" style="color: {bar_color}; font-weight: 700;">{risk_level} ({hazard_confidence:.1f}%)</span>
        </div>
        <div class="progress-container">
            <div class="progress-bar" style="width: {hazard_confidence}%; background: {bar_color};"></div>
        </div>
        <div class="section-title">🔍 Analysis & Reason</div>
        <p class="section-text">{reason}</p>
        <div class="section-title">🛡️ Recommended Cure & Actions</div>
        <p class="section-text">{cure}</p>
        <div style="margin-bottom: 20px;"></div>
        """,
        unsafe_allow_html=True
    )
    if st.button("Close Prediction Window", type="primary", use_container_width=True):
        st.rerun()

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

if "page" not in st.session_state:
    st.session_state.page = "landing"

if "prediction_result" not in st.session_state:
    st.session_state.prediction_result = None

# If a prediction has been made, display the custom floating modal dialog
if st.session_state.prediction_result is not None:
    show_prediction_dialog(st.session_state.prediction_result)
    st.session_state.prediction_result = None

for prefix in ["flood", "heatwave"]:
    if f"{prefix}_lat_input" not in st.session_state:
        st.session_state[f"{prefix}_lat_input"] = 20.5937
    if f"{prefix}_lon_input" not in st.session_state:
        st.session_state[f"{prefix}_lon_input"] = 78.9629
    if f"{prefix}_prev_country" not in st.session_state:
        st.session_state[f"{prefix}_prev_country"] = "India"
    if f"{prefix}_prev_state" not in st.session_state:
        st.session_state[f"{prefix}_prev_state"] = "Andhra Pradesh"
    if f"{prefix}_prev_city" not in st.session_state:
        st.session_state[f"{prefix}_prev_city"] = "Visakhapatnam"
    if f"{prefix}_city_select" not in st.session_state:
        st.session_state[f"{prefix}_city_select"] = "Visakhapatnam"
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

# Hierarchical dictionary mapping Indian states to major cities and their coordinates
STATE_CITY_COORDINATES = {
    "Andhra Pradesh": {
        "Visakhapatnam": (17.6868, 83.2185),
        "Vijayawada": (16.5062, 80.6480),
        "Tirupati": (13.6288, 79.4192),
        "Guntur": (16.3067, 80.4365),
        "Nellore": (14.4426, 79.9865)
    },
    "Arunachal Pradesh": {
        "Itanagar": (27.0844, 93.6053),
        "Tawang": (27.5861, 91.8594),
        "Ziro": (27.6335, 93.8393),
        "Pasighat": (28.0619, 95.3265)
    },
    "Assam": {
        "Guwahati": (26.1445, 91.7362),
        "Dibrugarh": (27.4728, 94.9120),
        "Silchar": (24.8333, 92.7789),
        "Jorhat": (26.7509, 94.2037),
        "Tezpur": (26.6338, 92.7926)
    },
    "Bihar": {
        "Patna": (25.5941, 85.1376),
        "Gaya": (24.7964, 84.9994),
        "Bhagalpur": (25.2425, 87.0145),
        "Muzaffarpur": (26.1209, 85.3647),
        "Darbhanga": (26.1542, 85.8918)
    },
    "Chhattisgarh": {
        "Raipur": (21.2514, 81.6296),
        "Bhilai": (21.1938, 81.3509),
        "Bilaspur": (22.0790, 82.1391),
        "Korba": (22.3524, 82.7501)
    },
    "Delhi": {
        "New Delhi": (28.6139, 77.2090),
        "Dwarka": (28.5823, 77.0500),
        "Rohini": (28.7438, 77.1154),
        "Vasant Kunj": (28.5398, 77.1485)
    },
    "Goa": {
        "Panaji": (15.4909, 73.8278),
        "Margao": (15.2736, 73.9580),
        "Vasco da Gama": (15.3997, 73.8113),
        "Mapusa": (15.5937, 73.8143)
    },
    "Gujarat": {
        "Ahmedabad": (23.0225, 72.5714),
        "Surat": (21.1702, 72.8311),
        "Vadodara": (22.3072, 73.1812),
        "Rajkot": (22.3039, 70.8022),
        "Gandhinagar": (23.2156, 72.6369)
    },
    "Haryana": {
        "Gurugram": (28.4595, 77.0266),
        "Faridabad": (28.4089, 77.3178),
        "Panipat": (29.3909, 76.9635),
        "Ambala": (30.3782, 76.7767),
        "Rohtak": (28.8955, 76.6066)
    },
    "Himachal Pradesh": {
        "Shimla": (31.1048, 77.1734),
        "Dharamshala": (32.2190, 76.3234),
        "Manali": (32.2396, 77.1887),
        "Solan": (30.9045, 77.0967)
    },
    "Jammu & Kashmir": {
        "Srinagar": (34.0837, 74.7973),
        "Jammu": (32.7266, 74.8570),
        "Anantnag": (33.7311, 75.1481),
        "Gulmarg": (34.0484, 74.3805)
    },
    "Jharkhand": {
        "Ranchi": (23.3441, 85.3096),
        "Jamshedpur": (22.8046, 86.2029),
        "Dhanbad": (23.7957, 86.4304),
        "Bokaro": (23.6693, 86.1511)
    },
    "Karnataka": {
        "Bengaluru": (12.9716, 77.5946),
        "Mysuru": (12.2958, 76.6394),
        "Hubballi": (15.3647, 75.1240),
        "Mangaluru": (12.9141, 74.8560),
        "Belagavi": (15.8497, 74.4977)
    },
    "Kerala": {
        "Thiruvananthapuram": (8.5241, 76.9366),
        "Kochi": (9.9312, 76.2673),
        "Kozhikode": (11.2588, 75.7804),
        "Thrissur": (10.5276, 76.2144),
        "Alappuzha": (9.4981, 76.3388)
    },
    "Madhya Pradesh": {
        "Bhopal": (23.2599, 77.4126),
        "Indore": (22.7196, 75.8577),
        "Jabalpur": (23.1815, 79.9864),
        "Gwalior": (26.2183, 78.1828),
        "Ujjain": (23.1760, 75.7885)
    },
    "Maharashtra": {
        "Mumbai": (19.0760, 72.8777),
        "Pune": (18.5204, 73.8567),
        "Nagpur": (21.1458, 79.0882),
        "Nashik": (19.9975, 73.7898),
        "Aurangabad": (19.8762, 75.3433)
    },
    "Manipur": {
        "Imphal": (24.8170, 93.9368),
        "Thoubal": (24.6409, 94.0175),
        "Churachandpur": (24.3364, 93.6841)
    },
    "Meghalaya": {
        "Shillong": (25.5788, 91.8831),
        "Tura": (25.5144, 90.2201),
        "Cherrapunji": (25.2702, 91.7323)
    },
    "Mizoram": {
        "Aizawl": (23.7307, 92.7173),
        "Lunglei": (22.8671, 92.7306),
        "Champhai": (23.4566, 93.3282)
    },
    "Nagaland": {
        "Kohima": (25.6751, 94.1086),
        "Dimapur": (25.9080, 93.7275),
        "Mokokchung": (26.3262, 94.5165)
    },
    "Odisha": {
        "Bhubaneswar": (20.2961, 85.8245),
        "Cuttack": (20.4625, 85.8830),
        "Rourkela": (22.2604, 84.8536),
        "Puri": (19.8135, 85.8312)
    },
    "Punjab": {
        "Ludhiana": (30.9010, 75.8573),
        "Amritsar": (31.6340, 74.8723),
        "Jalandhar": (31.3260, 75.5762),
        "Patiala": (30.3398, 76.3869),
        "Bathinda": (30.2110, 74.9455)
    },
    "Rajasthan": {
        "Jaipur": (26.9124, 75.7873),
        "Jodhpur": (26.2389, 73.0243),
        "Udaipur": (24.5854, 73.7125),
        "Kota": (25.2138, 75.8648),
        "Ajmer": (26.4499, 74.6399)
    },
    "Sikkim": {
        "Gangtok": (27.3314, 88.6138),
        "Namchi": (27.1678, 88.3540),
        "Mangan": (27.5029, 88.5292)
    },
    "Tamil Nadu": {
        "Chennai": (13.0827, 80.2707),
        "Coimbatore": (11.0168, 76.9558),
        "Madurai": (9.9252, 78.1198),
        "Tiruchirappalli": (10.7905, 78.7047),
        "Salem": (11.6643, 78.1460)
    },
    "Telangana": {
        "Hyderabad": (17.3850, 78.4867),
        "Warangal": (17.9689, 79.5941),
        "Nizamabad": (18.6725, 78.0941),
        "Khammam": (17.2473, 80.1514)
    },
    "Tripura": {
        "Agartala": (23.8315, 91.2868),
        "Dharmanagar": (24.3667, 92.1667),
        "Udaipur (Tripura)": (23.5333, 91.4833)
    },
    "Uttar Pradesh": {
        "Lucknow": (26.8467, 80.9462),
        "Kanpur": (26.4499, 80.3319),
        "Varanasi": (25.3176, 82.9739),
        "Agra": (27.1767, 78.0081),
        "Noida": (28.5355, 77.3910),
        "Prayagraj": (25.4358, 81.8463)
    },
    "Uttarakhand": {
        "Dehradun": (30.3165, 78.0322),
        "Haridwar": (29.9457, 78.1642),
        "Rishikesh": (30.0869, 78.2676),
        "Nainital": (29.3803, 79.4636)
    },
    "West Bengal": {
        "Kolkata": (22.5726, 88.3639),
        "Howrah": (22.5769, 88.3186),
        "Darjeeling": (27.0410, 88.2627),
        "Siliguri": (26.7271, 88.3953),
        "Durgapur": (23.5204, 87.3119)
    }
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
    pred = 1 if score >= 25 else 0
    
    # Calculate confidence based on distance to threshold (25)
    # Scaled from 50% (at threshold) up to 98% (far from threshold)
    distance = abs(score - 25)
    confidence = min(98.0, 50.0 + (distance / 20.0) * 48.0)
    
    return pred, confidence

def predict_heatwave_fallback(inputs):
    # inputs array: [temperature, humidity, wind_speed, pressure]
    temperature = inputs[0, 0]
    humidity = inputs[0, 1]
    wind_speed = inputs[0, 2]
    pressure = inputs[0, 3]
    
    score = (temperature - 30) * 0.6 + (humidity - 65) * 0.1 - wind_speed * 0.05
    pred = 1 if score >= 3.5 else 0
    
    # Calculate confidence based on distance to threshold (3.5)
    # Scaled from 50% (at threshold) up to 98% (far from threshold)
    distance = abs(score - 3.5)
    confidence = min(98.0, 50.0 + (distance / 5.0) * 48.0)
    
    return pred, confidence

# ----------------- Interactive Page Routing -----------------

if st.session_state.page == "landing":
    # Split-screen landing layout
    col1, col2 = st.columns([1.2, 1], gap="large")
    
    with col1:
        # THE LEFT SIDE (The Floating Brand Space)
        logo_file = os.path.join(CURRENT_DIR, "nimbus_predict_logo.png")
        if os.path.exists(logo_file):
            img_b64 = get_base64_image(logo_file)
            logo_html = f'<img src="data:image/png;base64,{img_b64}" style="width: 85px; height: 85px; border-radius: 16px; box-shadow: 0 4px 15px rgba(56,189,248,0.2); margin-bottom: 20px;"/>'
        else:
            logo_html = '<span style="font-size: 4rem;">🌍</span>'
            
        st.markdown(
            f"""
            <div class="brand-container">
                <div class="brand-chip">
                    {logo_html}
                    <h1 class="brand-title">Nimbus Predict</h1>
                </div>
                <div class="brand-tagline">Advanced Climate Hazard Analytics Engine</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col2:
        # THE RIGHT SIDE (The Interactive Gateway)
        st.markdown(
            """
            <div class="gateway-container">
                <h3 class="gateway-header">Global Anomaly Portal</h3>
                <p class="gateway-description">
                    This advanced analytics platform dynamically evaluates complex meteorological and geographical factors. 
                    It establishes regional environmental safety thresholds and identifies extreme hydrologic and thermal anomalies simultaneously.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Launch Climate Predictor Console", type="primary", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()

else:
    # THE DASHBOARD MODULE CONSOLE
    col1, col2 = st.columns([1.1, 1.9], gap="large")

    with col1:
        logo_file = os.path.join(CURRENT_DIR, "nimbus_predict_logo.png")

        if os.path.exists(logo_file):
            img_b64 = get_base64_image(logo_file)
            st.markdown(
                f"""
                <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 25px; margin-top: 15px;">
                    <img src="data:image/png;base64,{img_b64}" style="width: 60px; height: 60px; border-radius: 12px; box-shadow: 0 4px 15px rgba(56,189,248,0.2);"/>
                    <h1 style="
                        font-size: 2.4rem;
                        background: linear-gradient(135deg, #cbd5e1 0%, #94a3b8 50%, #38bdf8 100%);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        font-weight: 800;
                        margin: 0;
                        font-family: 'Plus Jakarta Sans', 'Outfit', sans-serif;
                        text-shadow: 0 4px 20px rgba(56, 189, 248, 0.15);
                    ">Nimbus Predict</h1>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown("<h1 class='main-header' style='text-align: left; font-size: 2.4rem;'>Nimbus Predict</h1>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="margin-bottom: 25px;">
                <p style="color: #94a3b8; font-size: 0.95rem; line-height: 1.5; margin: 0;">
                    Select the active hazard prediction module. Fill out local variables on the right console frame to model risk outcomes.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        selected_hazard = st.selectbox(
            "Choose hazard prediction module:",
            ["Flood Prediction", "Heatwave Prediction"]
        )

        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

        if st.button("🏠 Return to Landing Page", use_container_width=True):
            st.session_state.page = "landing"
            st.rerun()

    with col2:
        # ----------------- Forms Panel -----------------
        if selected_hazard == "Flood Prediction":
            st.header("🌊 Flood Prediction")
            
            model, err = load_flood_model()
            if err:
                st.info("💡 Note: Running in fallback mode (using heuristic logic).")
            else:
                st.success("✅ Model loaded successfully from root folder.")

            with st.container(border=True):
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
                        selected_state = st.session_state.get("flood_state_select", "Andhra Pradesh")
                        if selected_state not in STATE_CITY_COORDINATES:
                            selected_state = "Andhra Pradesh"
                        selected_city = st.session_state.get("flood_city_select", "Visakhapatnam")
                        if selected_city not in STATE_CITY_COORDINATES[selected_state]:
                            selected_city = list(STATE_CITY_COORDINATES[selected_state].keys())[0]
                        st.session_state.flood_lat_input, st.session_state.flood_lon_input = STATE_CITY_COORDINATES[selected_state][selected_city]
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
                    col_state, col_city = st.columns(2)
                    with col_state:
                        state_option = st.selectbox("Select Indian State:", list(STATE_CITY_COORDINATES.keys()), key="flood_state_select")
                    
                    cities_list = list(STATE_CITY_COORDINATES[state_option].keys())
                    
                    if state_option != st.session_state.flood_prev_state:
                        st.session_state.flood_prev_state = state_option
                        default_city = cities_list[0]
                        st.session_state.flood_city_select = default_city
                        st.session_state.flood_prev_city = default_city
                        st.session_state.flood_lat_input, st.session_state.flood_lon_input = STATE_CITY_COORDINATES[state_option][default_city]
                    
                    with col_city:
                        current_city = st.session_state.get("flood_city_select", cities_list[0])
                        if current_city not in cities_list:
                            current_city = cities_list[0]
                        city_index = cities_list.index(current_city)
                        city_option = st.selectbox("Select City:", cities_list, index=city_index, key="flood_city_select")
                        
                    if city_option != st.session_state.get("flood_prev_city"):
                        st.session_state.flood_lat_input, st.session_state.flood_lon_input = STATE_CITY_COORDINATES[state_option][city_option]
                        st.session_state.flood_prev_city = city_option
                        
                    st.info(f"📍 Coordinates loaded: State: **{state_option}** | City: **{city_option}**")

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

            st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

            with st.container(border=True):
                st.subheader("Meteorological & Environmental Variables")
                rainfall = st.number_input("Rainfall (mm)", min_value=0.0, value=25.0)
                river_level = st.number_input("River Level (m)", min_value=0.0, value=2.1)
                humidity = st.number_input("Humidity (%)", min_value=0.0, max_value=100.0, value=65.0)
                temperature = st.number_input("Temperature (°C)", value=24.5)

            input_data = np.array([[rainfall, river_level, humidity, temperature]])

            if st.button("Predict Flood Risk", type="primary", use_container_width=True):
                pred = None
                confidence = 85.0
                if model is not None:
                    try:
                        pred = model.predict(input_data)[0]
                        if hasattr(model, "predict_proba"):
                            prob = model.predict_proba(input_data)[0]
                            confidence = float(prob[pred]) * 100
                    except Exception:
                        pred, confidence = predict_flood_fallback(input_data)
                else:
                    pred, confidence = predict_flood_fallback(input_data)
                    
                if pred is not None:
                    st.session_state.prediction_result = {
                        "hazard": "flood",
                        "pred": pred,
                        "confidence": confidence
                    }
                    st.rerun()

        elif selected_hazard == "Heatwave Prediction":
            st.header("🔥 Heatwave Prediction")
            
            model, err = load_heatwave_model()
            if err:
                st.info("💡 Note: Running in fallback mode (using heuristic logic).")
            else:
                st.success("✅ Model loaded successfully from root folder.")

            with st.container(border=True):
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
                        selected_state = st.session_state.get("heatwave_state_select", "Andhra Pradesh")
                        if selected_state not in STATE_CITY_COORDINATES:
                            selected_state = "Andhra Pradesh"
                        selected_city = st.session_state.get("heatwave_city_select", "Visakhapatnam")
                        if selected_city not in STATE_CITY_COORDINATES[selected_state]:
                            selected_city = list(STATE_CITY_COORDINATES[selected_state].keys())[0]
                        st.session_state.heatwave_lat_input, st.session_state.heatwave_lon_input = STATE_CITY_COORDINATES[selected_state][selected_city]
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
                    col_state, col_city = st.columns(2)
                    with col_state:
                        state_option = st.selectbox("Select Indian State:", list(STATE_CITY_COORDINATES.keys()), key="heatwave_state_select")
                    
                    cities_list = list(STATE_CITY_COORDINATES[state_option].keys())
                    
                    if state_option != st.session_state.heatwave_prev_state:
                        st.session_state.heatwave_prev_state = state_option
                        default_city = cities_list[0]
                        st.session_state.heatwave_city_select = default_city
                        st.session_state.heatwave_prev_city = default_city
                        st.session_state.heatwave_lat_input, st.session_state.heatwave_lon_input = STATE_CITY_COORDINATES[state_option][default_city]
                    
                    with col_city:
                        current_city = st.session_state.get("heatwave_city_select", cities_list[0])
                        if current_city not in cities_list:
                            current_city = cities_list[0]
                        city_index = cities_list.index(current_city)
                        city_option = st.selectbox("Select City:", cities_list, index=city_index, key="heatwave_city_select")
                        
                    if city_option != st.session_state.get("heatwave_prev_city"):
                        st.session_state.heatwave_lat_input, st.session_state.heatwave_lon_input = STATE_CITY_COORDINATES[state_option][city_option]
                        st.session_state.heatwave_prev_city = city_option
                        
                    st.info(f"📍 Coordinates loaded: State: **{state_option}** | City: **{city_option}**")

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

            st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

            with st.container(border=True):
                st.subheader("Meteorological Variables")
                temperature = st.number_input("Temperature (°C)", value=38.5)
                humidity = st.number_input("Humidity (%)", min_value=0.0, max_value=100.0, value=55.0)
                wind_speed = st.number_input("Wind Speed (km/h)", min_value=0.0, value=12.0)
                pressure = st.number_input("Pressure (hPa)", min_value=900.0, max_value=1100.0, value=1008.0)

            input_data = np.array([[temperature, humidity, wind_speed, pressure]])

            if st.button("Predict Heatwave Risk", type="primary", use_container_width=True):
                pred = None
                confidence = 85.0
                if model is not None:
                    try:
                        pred = model.predict(input_data)[0]
                        if hasattr(model, "predict_proba"):
                            prob = model.predict_proba(input_data)[0]
                            confidence = float(prob[pred]) * 100
                    except Exception:
                        pred, confidence = predict_heatwave_fallback(input_data)
                else:
                    pred, confidence = predict_heatwave_fallback(input_data)
                    
                if pred is not None:
                    st.session_state.prediction_result = {
                        "hazard": "heatwave",
                        "pred": pred,
                        "confidence": confidence
                    }
                    st.rerun()
