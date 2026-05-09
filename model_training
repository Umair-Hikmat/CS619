import pandas as pd
import numpy as np
import tensorflow as tf
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.regularizers import l2
from tensorflow.keras.callbacks import EarlyStopping
from imblearn.over_sampling import SMOTE

def train_and_save_model(data_path):
    # 1. Load Data
    df = pd.read_csv(data_path)

    # Standardizing column names for the model pipeline
    df.columns = [
        "Age", "Gender", "ChestPainType", "RestingBloodPressure", "Cholesterol",
        "FastingBloodSugar", "RestECG", "MaxHeartRate", "ExerciseInducedAngina",
        "ST_Depression", "ST_Slope", "MajorVessels", "Thalassemia", "Target"
    ]

    X = df.drop('Target', axis=1)
    y = df['Target']

    # 2. Preprocessing Logic
    num_cols = X.select_dtypes(include=['int64', 'float64']).columns
    cat_cols = X.select_dtypes(include=['object']).columns

    preprocessor = ColumnTransformer([
        ('num', Pipeline([
            ('imputer', SimpleImputer(strategy='mean')),
            ('scaler', StandardScaler())
        ]), num_cols),
        ('cat', Pipeline([
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('encoder', OneHotEncoder(handle_unknown='ignore'))
        ]), cat_cols)
    ])

    # 3. Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # Fit preprocessor on training data
    X_train_proc = preprocessor.fit_transform(X_train)
    X_test_proc = preprocessor.transform(X_test)

    # 4. Handle Imbalance (SMOTE)
    sm = SMOTE(random_state=42)
    X_res, y_res = sm.fit_resample(X_train_proc, y_train)

    # 5. Build ANN Model
    model = Sequential([
        Dense(64, activation='relu', input_shape=(X_res.shape[1],)),
        Dropout(0.3),
        Dense(32, activation='relu', kernel_regularizer=l2(0.01)),
        Dropout(0.3),
        Dense(16, activation='relu', kernel_regularizer=l2(0.01)),
        Dense(1, activation='sigmoid')
    ])

    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

    # 6. Early Stopping (Monitoring Validation Loss)
    early_stop = EarlyStopping(
        monitor='val_loss',
        patience=5,
        restore_best_weights=True,
        verbose=1
    )

    # 7. Training
    model.fit(
        X_res, y_res,
        epochs=50,
        batch_size=16,
        validation_split=0.2,
        callbacks=[early_stop],
        verbose=1
    )

    # 8. Threshold Evaluation & Metrics
    y_pred_proba = model.predict(X_test_proc)
    print("\n" + "="*30)
    print("THRESHOLD EVALUATION")
    print("="*30)

    for threshold in [0.3, 0.4, 0.45, 0.5]:
        y_pred = (y_pred_proba > threshold).astype(int)
        print(f"\nResults for Threshold: {threshold}")
        print(classification_report(y_test, y_pred))
        print("Confusion Matrix:")
        print(confusion_matrix(y_test, y_pred))

    # 9. Save Assets
    model.save('heart_model.h5')
    joblib.dump(preprocessor, 'preprocessor.pkl')
    print("\nProcess Complete: 'heart_model.h5' and 'preprocessor.pkl' are ready for use.")

if __name__ == "__main__":
    # Ensure heart.csv is present in the Colab file section
    train_and_save_model('/content/drive/MyDrive/CS619/heart.csv')
