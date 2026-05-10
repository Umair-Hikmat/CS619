import pandas as pd
import numpy as np
import tensorflow as tf
import joblib
import os

MODEL_PATH = 'heart_model.h5'
PREPROCESSOR_PATH = 'preprocessor.pkl'

def predict_heart_risk(input_data, threshold=0.45):
    """
    Predicts heart disease risk and returns category, percentage, and target.
    """
    if not os.path.exists(MODEL_PATH) or not os.path.exists(PREPROCESSOR_PATH):
        return None, 0.0, "N/A", "Model assets missing."

    try:
        # 1. Load assets
        model = tf.keras.models.load_model(MODEL_PATH)
        preprocessor = joblib.load(PREPROCESSOR_PATH)

        # 2. Preprocess
        df_input = pd.DataFrame([input_data])
        processed_data = preprocessor.transform(df_input)

        # 3. Generate Probability
        prob = float(model.predict(processed_data, verbose=0)[0][0])
        percentage = round(prob, 4)

        # 4. Determine Target based on clinical threshold
        target = 1 if prob >= threshold else 0

        # 5. Define Risk Category
        # These tiers help doctors prioritize patients
        if prob < 0.30:
            category = "Low Risk"
        elif prob < threshold:
            category = "Borderline / Moderate Risk"
        elif prob < 0.75:
            category = "High Risk"
        else:
            category = "Critical Risk"

        return target, percentage, category, "Success"

    except Exception as e:
        return None, 0.0, "Error", str(e)
