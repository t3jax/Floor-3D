"""
ML Cost Estimation Model Training Script
Trains a RandomForestRegressor to predict construction costs based on material properties.
"""

import os
import pickle
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'construction_training_data_large.csv')
MODEL_DIR = os.path.join(BASE_DIR, 'ml_models')

def train_cost_model():
    """Train the cost estimation model and save artifacts."""
    
    print("=" * 60)
    print("FLOOR3D - ML Cost Estimation Model Training")
    print("=" * 60)
    
    # Create model directory if it doesn't exist
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Load training data
    print(f"\n[1/5] Loading training data from: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    print(f"      Loaded {len(df)} training samples")
    print(f"      Columns: {list(df.columns)}")
    
    # Check for required columns
    required_cols = ['material_type', 'grade', 'volume_m3', 'transport_distance_km', 
                     'labor_intensity_score', 'market_volatility', 'actual_total_cost_inr']
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Encode categorical variables
    print("\n[2/5] Encoding categorical variables...")
    le_material = LabelEncoder()
    le_grade = LabelEncoder()
    
    df['material_encoded'] = le_material.fit_transform(df['material_type'])
    df['grade_encoded'] = le_grade.fit_transform(df['grade'])
    
    print(f"      Material types: {list(le_material.classes_)}")
    print(f"      Grades: {list(le_grade.classes_)}")
    
    # Prepare features and target
    print("\n[3/5] Preparing features and target...")
    feature_cols = ['material_encoded', 'grade_encoded', 'volume_m3', 
                    'transport_distance_km', 'labor_intensity_score', 'market_volatility']
    
    X = df[feature_cols].values
    y = df['actual_total_cost_inr'].values
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"      Training samples: {len(X_train)}")
    print(f"      Test samples: {len(X_test)}")
    
    # Train model
    print("\n[4/5] Training RandomForestRegressor...")
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print(f"      Model Performance:")
    print(f"        - Mean Absolute Error: Rs. {mae:,.2f}")
    print(f"        - R-squared Score: {r2:.4f}")
    
    # Feature importance
    importance = dict(zip(feature_cols, model.feature_importances_))
    print(f"      Feature Importance:")
    for feat, imp in sorted(importance.items(), key=lambda x: -x[1]):
        print(f"        - {feat}: {imp:.4f}")
    
    # Save artifacts
    print("\n[5/5] Saving model artifacts...")
    
    model_path = os.path.join(MODEL_DIR, 'cost_model.pkl')
    le_material_path = os.path.join(MODEL_DIR, 'le_material.pkl')
    le_grade_path = os.path.join(MODEL_DIR, 'le_grade.pkl')
    metadata_path = os.path.join(MODEL_DIR, 'model_metadata.pkl')
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"      Saved model: {model_path}")
    
    with open(le_material_path, 'wb') as f:
        pickle.dump(le_material, f)
    print(f"      Saved encoder: {le_material_path}")
    
    with open(le_grade_path, 'wb') as f:
        pickle.dump(le_grade, f)
    print(f"      Saved encoder: {le_grade_path}")
    
    # Save metadata for reference
    metadata = {
        'feature_columns': feature_cols,
        'material_classes': list(le_material.classes_),
        'grade_classes': list(le_grade.classes_),
        'mae': mae,
        'r2_score': r2,
        'n_samples': len(df),
        'feature_importance': importance
    }
    with open(metadata_path, 'wb') as f:
        pickle.dump(metadata, f)
    print(f"      Saved metadata: {metadata_path}")
    
    print("\n" + "=" * 60)
    print("Training complete! Model is ready for predictions.")
    print("=" * 60)
    
    return model, le_material, le_grade


if __name__ == '__main__':
    train_cost_model()
