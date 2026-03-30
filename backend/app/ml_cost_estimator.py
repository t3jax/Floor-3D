"""
ML-based Cost Estimation Engine
Provides AI-powered cost predictions for construction materials.
"""

import os
import pickle
import numpy as np
from typing import Optional, Dict, Any, Tuple

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, 'ml_models')


class CostEstimator:
    """
    AI-powered cost estimation using trained RandomForest model.
    Falls back to simple calculation if model is unavailable.
    """
    
    def __init__(self):
        self.model = None
        self.le_material = None
        self.le_grade = None
        self.metadata = None
        self.is_loaded = False
        self.load_model()
    
    def load_model(self) -> bool:
        """Load the trained model and encoders."""
        try:
            model_path = os.path.join(MODEL_DIR, 'cost_model.pkl')
            le_material_path = os.path.join(MODEL_DIR, 'le_material.pkl')
            le_grade_path = os.path.join(MODEL_DIR, 'le_grade.pkl')
            metadata_path = os.path.join(MODEL_DIR, 'model_metadata.pkl')
            
            # Check if all files exist
            if not all(os.path.exists(p) for p in [model_path, le_material_path, le_grade_path]):
                print("WARNING: ML model files not found. Using fallback estimation.")
                return False
            
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            
            with open(le_material_path, 'rb') as f:
                self.le_material = pickle.load(f)
            
            with open(le_grade_path, 'rb') as f:
                self.le_grade = pickle.load(f)
            
            if os.path.exists(metadata_path):
                with open(metadata_path, 'rb') as f:
                    self.metadata = pickle.load(f)
            
            self.is_loaded = True
            print("ML Cost Estimation Model loaded successfully")
            return True
            
        except Exception as e:
            print(f"WARNING: Failed to load ML model: {e}")
            self.is_loaded = False
            return False
    
    def _normalize_material_name(self, material: str) -> str:
        """Normalize material name to match training data."""
        # Map from materials.json names to training data names
        material_map = {
            'aac_blocks': 'AAC Block',
            'aac blocks': 'AAC Block',
            'aac block': 'AAC Block',
            'red_brick': 'Red Brick',
            'red brick': 'Red Brick',
            'rcc': 'RCC',
            'rcc (reinforced cement concrete)': 'RCC',
            'steel_frame': 'Steel Frame',
            'steel frame': 'Steel Frame',
            'hollow_concrete_block': 'Hollow Concrete',
            'hollow concrete block': 'Hollow Concrete',
            'hollow concrete': 'Hollow Concrete',
            'fly_ash_brick': 'Fly Ash Brick',
            'fly ash brick': 'Fly Ash Brick',
            'precast_concrete_panel': 'RCC',  # Map to closest available
            'precast concrete panel': 'RCC',
        }
        
        normalized = material_map.get(material.lower(), material)
        return normalized
    
    def estimate_cost(
        self,
        material: str,
        grade: str = 'Standard',
        volume_m3: float = 10.0,
        transport_distance_km: float = 30.0,
        labor_intensity_score: float = 5.0,
        market_volatility: float = 1.0
    ) -> Dict[str, Any]:
        """
        Estimate construction cost using AI model.
        
        Args:
            material: Material type (e.g., 'Red Brick', 'Fly Ash Brick')
            grade: Quality grade ('Standard', 'Premium', 'Industrial')
            volume_m3: Volume in cubic meters
            transport_distance_km: Distance from supplier
            labor_intensity_score: Labor difficulty (1-10)
            market_volatility: Market price factor (0.8-1.2)
        
        Returns:
            Dict with predicted_cost, is_ai_generated, confidence, etc.
        """
        
        # Normalize material name
        material_normalized = self._normalize_material_name(material)
        
        # Check if model is available
        if not self.is_loaded or self.model is None:
            return self._fallback_estimate(material_normalized, volume_m3)
        
        try:
            # Check if material exists in encoder
            if material_normalized not in self.le_material.classes_:
                # Try to find closest match
                print(f"WARNING: Material '{material_normalized}' not in training data")
                return self._fallback_estimate(material_normalized, volume_m3)
            
            # Check if grade exists
            if grade not in self.le_grade.classes_:
                grade = 'Standard'  # Default grade
            
            # Encode inputs
            material_encoded = self.le_material.transform([material_normalized])[0]
            grade_encoded = self.le_grade.transform([grade])[0]
            
            # Prepare feature vector
            features = np.array([[
                material_encoded,
                grade_encoded,
                volume_m3,
                transport_distance_km,
                labor_intensity_score,
                market_volatility
            ]])
            
            # Make prediction
            predicted_cost = float(self.model.predict(features)[0])
            
            # Calculate confidence based on model R2 score
            confidence = self.metadata.get('r2_score', 0.85) if self.metadata else 0.85
            
            return {
                'predicted_cost': round(predicted_cost, 2),
                'is_ai_generated': True,
                'confidence': round(confidence, 2),
                'model_mae': self.metadata.get('mae', 0) if self.metadata else 0,
                'input_params': {
                    'material': material_normalized,
                    'grade': grade,
                    'volume_m3': volume_m3,
                    'transport_distance_km': transport_distance_km,
                    'labor_intensity_score': labor_intensity_score,
                    'market_volatility': market_volatility
                }
            }
            
        except Exception as e:
            print(f"WARNING: ML prediction failed: {e}")
            return self._fallback_estimate(material_normalized, volume_m3)
    
    def _fallback_estimate(self, material: str, volume_m3: float) -> Dict[str, Any]:
        """Fallback estimation using simple price * volume calculation."""
        
        # Base prices per cubic meter (approximate)
        base_prices = {
            'AAC Blocks': 2800,
            'Red Brick': 3500,
            'RCC': 8500,
            'Steel Frame': 45000,
            'Hollow Concrete Block': 3200,
            'Fly Ash Brick': 2500,
            'Precast Concrete Panel': 6500,
        }
        
        base_price = base_prices.get(material, 4000)  # Default price
        estimated_cost = base_price * volume_m3
        
        return {
            'predicted_cost': round(estimated_cost, 2),
            'is_ai_generated': False,
            'confidence': 0.5,  # Lower confidence for fallback
            'model_mae': 0,
            'fallback_reason': 'ML model unavailable or material not in training data',
            'input_params': {
                'material': material,
                'volume_m3': volume_m3
            }
        }
    
    def estimate_all_materials(
        self,
        volume_m3: float,
        transport_distance_km: float = 30.0,
        labor_intensity_score: float = 5.0,
        market_volatility: float = 1.0
    ) -> Dict[str, Dict[str, Any]]:
        """
        Estimate costs for all available materials.
        
        Returns:
            Dict mapping material names to their cost estimates
        """
        
        materials = [
            'AAC Blocks', 'Red Brick', 'RCC', 'Steel Frame',
            'Hollow Concrete Block', 'Fly Ash Brick', 'Precast Concrete Panel'
        ]
        
        grades = ['Standard', 'Premium', 'Industrial']
        
        results = {}
        for material in materials:
            material_results = {}
            for grade in grades:
                estimate = self.estimate_cost(
                    material=material,
                    grade=grade,
                    volume_m3=volume_m3,
                    transport_distance_km=transport_distance_km,
                    labor_intensity_score=labor_intensity_score,
                    market_volatility=market_volatility
                )
                material_results[grade] = estimate
            
            # Use Standard grade as default and create a copy to avoid circular refs
            default_estimate = material_results.get('Standard', material_results.get('Premium', {}))
            results[material] = {**default_estimate}  # Create a shallow copy
            results[material]['all_grades'] = material_results
        
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        if not self.is_loaded:
            return {
                'loaded': False,
                'reason': 'Model not loaded'
            }
        
        return {
            'loaded': True,
            'r2_score': self.metadata.get('r2_score') if self.metadata else None,
            'mae': self.metadata.get('mae') if self.metadata else None,
            'n_samples': self.metadata.get('n_samples') if self.metadata else None,
            'material_classes': list(self.le_material.classes_) if self.le_material else [],
            'grade_classes': list(self.le_grade.classes_) if self.le_grade else [],
            'feature_importance': self.metadata.get('feature_importance') if self.metadata else {}
        }


# Global instance for use across the application
_cost_estimator: Optional[CostEstimator] = None


def get_cost_estimator() -> CostEstimator:
    """Get or create the global cost estimator instance."""
    global _cost_estimator
    if _cost_estimator is None:
        _cost_estimator = CostEstimator()
    return _cost_estimator


def estimate_cost(
    material: str,
    grade: str = 'Standard',
    volume_m3: float = 10.0,
    transport_distance_km: float = 30.0,
    labor_intensity_score: float = 5.0,
    market_volatility: float = 1.0
) -> Dict[str, Any]:
    """
    Convenience function for cost estimation.
    
    Returns dict with predicted_cost and is_ai_generated flag.
    """
    estimator = get_cost_estimator()
    return estimator.estimate_cost(
        material=material,
        grade=grade,
        volume_m3=volume_m3,
        transport_distance_km=transport_distance_km,
        labor_intensity_score=labor_intensity_score,
        market_volatility=market_volatility
    )
