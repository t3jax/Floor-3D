"""
Test script to verify measurement storage in SQLite database
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database_sqlalchemy import SessionLocal, StructuralElement, ScaleMetadata, ProjectMetadata, Material

def test_database_ready():
    """Test that database is ready to store measurements"""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("SQLite Database Test - Measurement Storage")
        print("=" * 60)
        print()
        
        # Check materials
        materials_count = db.query(Material).count()
        print(f"✅ Materials loaded: {materials_count}")
        
        if materials_count > 0:
            sample = db.query(Material).first()
            print(f"   Example: {sample.name} @ ${sample.cost_per_unit}/{sample.unit}")
        
        print()
        
        # Check if tables can store data (try inserting test record)
        test_project_id = "test_measurement_storage"
        
        # Clean up any existing test data
        db.query(StructuralElement).filter_by(project_id=test_project_id).delete()
        db.query(ScaleMetadata).filter_by(project_id=test_project_id).delete()
        db.query(ProjectMetadata).filter_by(id=test_project_id).delete()
        db.commit()
        
        # Test ScaleMetadata storage
        print("🔄 Testing ScaleMetadata storage...")
        scale_meta = ScaleMetadata(
            project_id=test_project_id,
            scale_factor=0.05,  # 1 pixel = 0.05 meters
            scaling_method="OCR",
            confidence=0.85,
            aspect_ratio=1.5
        )
        db.add(scale_meta)
        db.commit()
        print("✅ ScaleMetadata stored successfully")
        print(f"   Scale: 1px = {scale_meta.scale_factor}m")
        print(f"   Method: {scale_meta.scaling_method}")
        print(f"   Confidence: {scale_meta.confidence}")
        print()
        
        # Test StructuralElement storage
        print("🔄 Testing StructuralElement storage...")
        wall = StructuralElement(
            project_id=test_project_id,
            element_type="wall",
            length_px=200,
            real_world_length_m=10.0,  # 200px * 0.05 = 10m
            thickness_category="major",
            thickness_m=0.23,
            coordinates='{"x1": 100, "y1": 200, "x2": 300, "y2": 200}'
        )
        db.add(wall)
        db.commit()
        print("✅ StructuralElement stored successfully")
        print(f"   Type: {wall.element_type}")
        print(f"   Length: {wall.length_px}px = {wall.real_world_length_m}m")
        print(f"   Thickness: {wall.thickness_m}m ({wall.thickness_category})")
        print(f"   Coordinates: {wall.coordinates}")
        print()
        
        # Test ProjectMetadata storage
        print("🔄 Testing ProjectMetadata storage...")
        project = ProjectMetadata(
            id=test_project_id,
            project_name="test_floorplan.jpg",
            has_second_floor=False
        )
        db.add(project)
        db.commit()
        print("✅ ProjectMetadata stored successfully")
        print(f"   Project name: {project.project_name}")
        print()
        
        # Verify retrieval
        print("🔄 Testing data retrieval...")
        retrieved_scale = db.query(ScaleMetadata).filter_by(project_id=test_project_id).first()
        retrieved_wall = db.query(StructuralElement).filter_by(project_id=test_project_id).first()
        retrieved_project = db.query(ProjectMetadata).filter_by(id=test_project_id).first()
        
        assert retrieved_scale is not None, "Scale metadata not found"
        assert retrieved_wall is not None, "Structural element not found"
        assert retrieved_project is not None, "Project metadata not found"
        
        assert retrieved_scale.scale_factor == 0.05
        assert retrieved_wall.real_world_length_m == 10.0
        assert retrieved_project.project_name == "test_floorplan.jpg"
        
        print("✅ All data retrieved correctly")
        print()
        
        # Clean up test data
        db.query(StructuralElement).filter_by(project_id=test_project_id).delete()
        db.query(ScaleMetadata).filter_by(project_id=test_project_id).delete()
        db.query(ProjectMetadata).filter_by(id=test_project_id).delete()
        db.commit()
        print("🗑️ Test data cleaned up")
        print()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("The database is ready to store measurements from floor plans:")
        print("  • Scale factors (from OCR/heuristic/default)")
        print("  • Structural elements (walls, doors, windows)")
        print("  • Real-world dimensions (meters)")
        print("  • Wall thickness and coordinates")
        print("  • Project metadata")
        print()
        print("When you upload a floor plan, all measurements will be")
        print("automatically stored in: structural_intelligence.db")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()


if __name__ == "__main__":
    success = test_database_ready()
    sys.exit(0 if success else 1)
