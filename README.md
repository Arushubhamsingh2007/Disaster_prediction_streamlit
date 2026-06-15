# ClimaSafe Hazard Intelligence System (Flat Layout)

A basic, flat Streamlit-based machine learning web application. It uses two pre-trained models (`flood_prediction.pkl` and `heatwave_prediction.pkl`) placed in the same folder to perform classification.

---

## 📁 Directory Structure

```text
fdpp2/
├── .streamlit/
│   └── config.toml           # UI styling and dark theme configuration
├── flood_prediction.pkl       # Pre-trained Scikit-Learn Pipeline for flood risk
├── heatwave_prediction.pkl    # Pre-trained Random Forest for heatwave hazard
├── app.py                    # Consolidated Streamlit app containing UI and loader logic
├── requirements.txt          # Declared Python library versions
└── README.md                 # Setup guidelines
```

---

## 🚀 Installation & Local Run

### 1. Set Up a Virtual Environment
Create and activate a virtual environment:

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Streamlit Application
```bash
streamlit run app.py
```

---

## 📊 Model Details

* **Flood Model (`flood_prediction.pkl`)**: Loads a Scikit-Learn Pipeline model expecting 13 features (`lon`, `lat`, `jrc_perm_water`, `precip_1d`, `precip_3d`, `NDVI`, `NDWI`, etc.).
* **Heatwave Model (`heatwave_prediction.pkl`)**: Loads a RandomForestClassifier model expecting 16 features (`latitude`, `longitude`, `wind_speed`, `cloud_cover`, `uv_index`, `max_temperature`, `min_temperature`, etc.).
