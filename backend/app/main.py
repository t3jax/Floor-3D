"""
Autonomous Structural Intelligence System — FastAPI entry.
"""

from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import base64
import os
import traceback
from fpdf import FPDF

from app.pipeline import process_fallback, process_image_bytes
from app.materials import load_materials, top_k_materials
from app.schemas import FallbackGraphInput, ProcessResult
from app.database import get_db
from app.ml_cost_estimator import get_cost_estimator, estimate_cost


class ExportReportRequest(BaseModel):
    image_base64: str = ""


class AIEstimationRequest(BaseModel):
    """Request body for AI cost estimation."""
    project_id: Optional[str] = None
    volume_m3: Optional[float] = 10.0
    transport_distance_km: Optional[float] = 30.0
    labor_intensity_score: Optional[float] = 5.0
    market_volatility: Optional[float] = 1.0


app = FastAPI(
    title="Autonomous Structural Intelligence System",
    version="0.1.0",
    description="Floor plan to graph to materials + LLM prompt template with AI Cost Estimation.",
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions gracefully."""
    error_msg = str(exc)
    print(f"UNHANDLED ERROR in {request.url.path}: {error_msg}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": f"Server error: {error_msg}",
            "detail": error_msg
        }
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ML Cost Estimator on startup
@app.on_event("startup")
async def startup_event():
    """Load ML model on application startup."""
    estimator = get_cost_estimator()
    if estimator.is_loaded:
        print("AI Cost Estimation Model: LOADED")
    else:
        print("AI Cost Estimation Model: FALLBACK MODE (model not found)")


@app.get("/health")
def health():
    """Health check endpoint."""
    estimator = get_cost_estimator()
    return {
        "status": "ok",
        "ai_model_loaded": estimator.is_loaded
    }


@app.post("/api/process-floorplan", response_model=ProcessResult)
async def process_floorplan(file: UploadFile = File(...)) -> ProcessResult:
    """Process uploaded floor plan image and return analysis result."""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Expected an image file (PNG, JPG, etc).")
        
        # Read file data
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Empty file received.")
        
        # Check file size (max 10MB)
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")
        
        print(f"Processing image: {file.filename}, size: {len(data)} bytes, type: {file.content_type}")
        
        # Process the image
        result = process_image_bytes(data)
        
        if not result.success:
            print(f"Processing failed: {result.message}")
        else:
            print(f"Processing successful: {len(result.graph.edges) if result.graph else 0} edges detected")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = f"Unexpected error processing image: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/api/process-fallback", response_model=ProcessResult)
def process_fallback_route(payload: FallbackGraphInput) -> ProcessResult:
    if not payload.nodes or not payload.edges:
        raise HTTPException(status_code=400, detail="nodes and edges are required.")
    return process_fallback(payload)


@app.get("/api/materials")
def list_materials() -> dict:
    materials = load_materials()
    return {"materials": [m.model_dump() for m in materials]}


@app.get("/api/materials/top")
def materials_top(k: int = 3) -> dict:
    materials = load_materials()
    return {"top": [r.model_dump() for r in top_k_materials(materials, k=k)[0]]}


@app.get("/api/materials/ai-costs")
def get_ai_material_costs(
    project_id: Optional[str] = None,
    volume_m3: float = 10.0,
    transport_distance_km: float = 30.0,
    labor_intensity_score: float = 5.0,
    market_volatility: float = 1.0
) -> dict:
    """
    Get AI-powered cost predictions for all materials.
    
    If project_id is provided, fetches volume from database.
    Otherwise uses provided volume_m3 parameter.
    """
    from app.database_sqlalchemy import SessionLocal, StructuralElement, ScaleMetadata, ProjectMetadata
    
    actual_volume = volume_m3
    project_data = None
    
    # Try to fetch data from database if project_id provided
    if project_id:
        db = SessionLocal()
        try:
            # Get structural elements for volume calculation
            elements = db.query(StructuralElement).filter(
                StructuralElement.project_id == project_id
            ).all()
            
            if elements:
                # Calculate total wall volume
                wall_height = 3.0  # meters
                total_volume = 0.0
                for el in elements:
                    length_m = el.real_world_length_m or 0
                    thickness_m = el.thickness_m or 0.115
                    total_volume += length_m * thickness_m * wall_height
                actual_volume = total_volume if total_volume > 0 else volume_m3
            
            # Try to get project metadata for additional params
            project_meta = db.query(ProjectMetadata).filter(
                ProjectMetadata.id == project_id
            ).first()
            
            if project_meta:
                project_data = {
                    'transport_distance_km': project_meta.transport_distance_km or transport_distance_km,
                    'labor_intensity_score': project_meta.labor_intensity_score or labor_intensity_score,
                    'market_volatility': project_meta.market_volatility or market_volatility
                }
                transport_distance_km = project_data['transport_distance_km']
                labor_intensity_score = project_data['labor_intensity_score']
                market_volatility = project_data['market_volatility']
                
        except Exception as e:
            print(f"Error fetching project data: {e}")
        finally:
            db.close()
    
    # Get cost estimates for all materials
    estimator = get_cost_estimator()
    all_estimates = estimator.estimate_all_materials(
        volume_m3=actual_volume,
        transport_distance_km=transport_distance_km,
        labor_intensity_score=labor_intensity_score,
        market_volatility=market_volatility
    )
    
    # Load base materials and enhance with AI predictions
    materials = load_materials()
    enhanced_materials = []
    
    for mat in materials:
        mat_dict = mat.model_dump()
        mat_name = mat.name
        
        # Find matching AI estimate
        ai_estimate = None
        for est_name, est_data in all_estimates.items():
            if est_name.lower().replace(' ', '_') == mat.id or est_name.lower() == mat_name.lower():
                ai_estimate = est_data
                break
        
        if ai_estimate:
            mat_dict['predicted_cost'] = ai_estimate.get('predicted_cost', 0)
            mat_dict['is_ai_generated'] = ai_estimate.get('is_ai_generated', False)
            mat_dict['ai_confidence'] = ai_estimate.get('confidence', 0)
            mat_dict['all_grades'] = ai_estimate.get('all_grades', {})
        else:
            # Fallback estimation
            fallback = estimator._fallback_estimate(mat_name, actual_volume)
            mat_dict['predicted_cost'] = fallback['predicted_cost']
            mat_dict['is_ai_generated'] = False
            mat_dict['ai_confidence'] = 0.5
        
        enhanced_materials.append(mat_dict)
    
    # Sort by predicted cost
    enhanced_materials.sort(key=lambda x: x.get('predicted_cost', 0))
    
    return {
        "materials": enhanced_materials,
        "estimation_params": {
            "volume_m3": round(actual_volume, 2),
            "transport_distance_km": transport_distance_km,
            "labor_intensity_score": labor_intensity_score,
            "market_volatility": market_volatility
        },
        "model_info": estimator.get_model_info(),
        "project_id": project_id
    }


@app.post("/api/estimate-cost")
def estimate_material_cost(request: AIEstimationRequest) -> dict:
    """
    Estimate cost for a specific configuration using AI model.
    """
    from app.database_sqlalchemy import SessionLocal, StructuralElement
    
    volume_m3 = request.volume_m3 or 10.0
    
    # Fetch volume from database if project_id provided
    if request.project_id:
        db = SessionLocal()
        try:
            elements = db.query(StructuralElement).filter(
                StructuralElement.project_id == request.project_id
            ).all()
            
            if elements:
                wall_height = 3.0
                total_volume = sum(
                    (el.real_world_length_m or 0) * (el.thickness_m or 0.115) * wall_height
                    for el in elements
                )
                volume_m3 = total_volume if total_volume > 0 else volume_m3
        except Exception as e:
            print(f"Error fetching project data: {e}")
        finally:
            db.close()
    
    estimator = get_cost_estimator()
    all_estimates = estimator.estimate_all_materials(
        volume_m3=volume_m3,
        transport_distance_km=request.transport_distance_km or 30.0,
        labor_intensity_score=request.labor_intensity_score or 5.0,
        market_volatility=request.market_volatility or 1.0
    )
    
    return {
        "success": True,
        "estimates": all_estimates,
        "volume_m3": round(volume_m3, 2),
        "is_ai_model_loaded": estimator.is_loaded
    }


@app.get("/api/ai-model/info")
def get_ai_model_info() -> dict:
    """Get information about the loaded AI model."""
    estimator = get_cost_estimator()
    return {
        "model_info": estimator.get_model_info(),
        "is_loaded": estimator.is_loaded
    }


@app.get("/api/database/stats")
def get_database_stats() -> dict:
    """Get database statistics - shows stored data for demonstration."""
    from app.database_sqlalchemy import SessionLocal, StructuralElement, ScaleMetadata, Material, ProjectMetadata
    
    db = SessionLocal()
    try:
        # Get counts
        materials_count = db.query(Material).count()
        elements_count = db.query(StructuralElement).count()
        projects_count = db.query(ScaleMetadata).count()
        
        # Get recent elements with details
        recent_elements = db.query(StructuralElement).order_by(StructuralElement.id.desc()).limit(20).all()
        elements_data = [{
            "id": el.id,
            "project_id": el.project_id[:8] + "..." if el.project_id and len(el.project_id) > 8 else el.project_id,
            "type": el.element_type,
            "length_px": round(el.length_px, 1) if el.length_px else 0,
            "real_world_length_m": round(el.real_world_length_m, 2) if el.real_world_length_m else 0,
            "thickness_m": el.thickness_m,
            "thickness_category": el.thickness_category,
            "coordinates": el.coordinates
        } for el in recent_elements]
        
        # Get scale metadata
        scale_records = db.query(ScaleMetadata).order_by(ScaleMetadata.created_at.desc()).limit(10).all()
        scale_data = [{
            "project_id": sm.project_id[:8] + "..." if sm.project_id and len(sm.project_id) > 8 else sm.project_id,
            "scale_factor": round(sm.scale_factor, 4) if sm.scale_factor else 0,
            "scaling_method": sm.scaling_method,
            "confidence": round(sm.confidence * 100, 1) if sm.confidence else 0,
            "created_at": sm.created_at.isoformat() if sm.created_at else None
        } for sm in scale_records]
        
        # Get all materials
        all_materials = db.query(Material).all()
        materials_data = [{
            "id": m.id,
            "name": m.name,
            "cost_per_unit": m.cost_per_unit,
            "unit": m.unit,
            "strength": m.strength,
            "durability": m.durability
        } for m in all_materials]
        
        return {
            "success": True,
            "stats": {
                "total_materials": materials_count,
                "total_structural_elements": elements_count,
                "total_projects_analyzed": projects_count
            },
            "recent_elements": elements_data,
            "scale_metadata": scale_data,
            "materials": materials_data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "stats": {
                "total_materials": 0,
                "total_structural_elements": 0,
                "total_projects_analyzed": 0
            },
            "recent_elements": [],
            "scale_metadata": [],
            "materials": []
        }
    finally:
        db.close()


@app.post("/api/export-report/{project_id}")
def export_report(project_id: str, payload: ExportReportRequest) -> Response:
    from datetime import datetime
    import tempfile
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Fetch data
        c.execute("SELECT element_type, SUM(length_px) as total_len, COUNT(*) as count FROM Structural_Elements WHERE project_id=? GROUP BY element_type", (project_id,))
        elements = c.fetchall()
        
        c.execute("""
            SELECT r.element_id, m.id as material_id, m.name, r.score, 
                   m.cost_per_unit, m.strength, m.durability, m.unit, m.notes 
            FROM Recommendations r 
            JOIN Materials m ON r.material_id = m.id 
            WHERE r.project_id=? 
            ORDER BY r.score DESC
        """, (project_id,))
        recs = c.fetchall()
        
        c.execute("SELECT * FROM Materials")
        all_materials = c.fetchall()
        conn.close()
        
        # Calculate metrics - handle empty data gracefully
        total_length_px = sum((el['total_len'] or 0) for el in elements) if elements else 0
        total_wall_count = sum((el['count'] or 0) for el in elements) if elements else 0
        exterior_walls = next((el for el in elements if el['element_type'] == 'exterior'), None)
        interior_walls = next((el for el in elements if el['element_type'] == 'interior'), None)
        
        SCALE_FACTOR = 0.01
        WALL_HEIGHT = 3.0
        WALL_THICKNESS = 0.23
        
        total_length_m = total_length_px * SCALE_FACTOR
        total_area_m2 = total_length_m * WALL_HEIGHT
        total_volume_m3 = total_length_m * WALL_HEIGHT * WALL_THICKNESS
        
        ext_len_m = ((exterior_walls['total_len'] or 0) * SCALE_FACTOR) if exterior_walls else 0
        int_len_m = ((interior_walls['total_len'] or 0) * SCALE_FACTOR) if interior_walls else 0
        
        # Calculate material costs
        material_costs = []
        for mat in all_materials:
            try:
                unit = mat['unit'] or ''
                cost_per_unit = mat['cost_per_unit'] or 0
                if 'sqft' in unit.lower():
                    cost = total_area_m2 * 10.764 * cost_per_unit
                elif 'cum' in unit.lower() or 'm3' in unit.lower():
                    cost = total_volume_m3 * cost_per_unit
                else:
                    cost = total_volume_m3 * cost_per_unit * 50
                material_costs.append({
                    'name': mat['name'] or 'Unknown', 
                    'cost': cost, 
                    'strength': mat['strength'] or 0, 
                    'durability': mat['durability'] or 0
                })
            except Exception:
                continue
        material_costs.sort(key=lambda x: x['cost'])
        
        # Initialize PDF
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_margins(20, 20, 20)
        
        # ===== PAGE 1: COVER =====
        pdf.add_page()
        
        # Header
        pdf.set_fill_color(15, 23, 42)
        pdf.rect(0, 0, 210, 50, 'F')
        
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("helvetica", "B", 28)
        pdf.set_y(15)
        pdf.cell(0, 12, "FLOOR3D", align="C")
        
        pdf.set_font("helvetica", "", 12)
        pdf.set_y(30)
        pdf.cell(0, 8, "Construction Cost Analysis Report", align="C")
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_y(60)
        
        # Project Info Box
        pdf.set_fill_color(241, 245, 249)
        pdf.rect(20, 55, 170, 25, 'F')
        pdf.set_font("helvetica", "", 10)
        pdf.set_xy(25, 60)
        pdf.cell(80, 6, f"Project ID: {project_id[:8]}")
        pdf.set_xy(105, 60)
        pdf.cell(80, 6, f"Date: {datetime.now().strftime('%d %B %Y')}")
        pdf.set_xy(25, 68)
        pdf.cell(80, 6, f"Walls Detected: {total_wall_count}")
        pdf.set_xy(105, 68)
        pdf.cell(80, 6, f"Total Length: {total_length_m:.1f} meters")
        
        # Floor Plan Image
        if payload.image_base64 and "," in payload.image_base64:
            pdf.set_y(90)
            pdf.set_font("helvetica", "B", 11)
            pdf.cell(0, 8, "Floor Plan Layout")
            pdf.ln(10)
            
            try:
                header, encoded = payload.image_base64.split(",", 1)
                img_data = base64.b64decode(encoded)
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    tmp.write(img_data)
                    img_path = tmp.name
                pdf.image(img_path, x=35, y=pdf.get_y(), w=140)
                os.remove(img_path)
            except:
                pass
        
        # ===== PAGE 2: COST SUMMARY =====
        pdf.add_page()
        
        pdf.set_font("helvetica", "B", 16)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 10, "Cost Estimation Summary")
        pdf.ln(15)
        
        # Key Metrics
        pdf.set_font("helvetica", "B", 10)
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(85, 8, "Parameter", 1, 0, 'C', True)
        pdf.cell(85, 8, "Value", 1, 1, 'C', True)
        
        pdf.set_font("helvetica", "", 10)
        metrics = [
            ("Total Wall Length", f"{total_length_m:.2f} meters"),
            ("Wall Height", f"{WALL_HEIGHT} meters"),
            ("Wall Thickness", f"{WALL_THICKNESS} meters (9 inches)"),
            ("Total Wall Area", f"{total_area_m2:.2f} sq.m"),
            ("Total Wall Volume", f"{total_volume_m3:.2f} cubic meters"),
            ("Exterior Walls", f"{ext_len_m:.2f} m ({exterior_walls['count'] if exterior_walls else 0} segments)"),
            ("Interior Walls", f"{int_len_m:.2f} m ({interior_walls['count'] if interior_walls else 0} segments)"),
        ]
        
        for label, value in metrics:
            pdf.cell(85, 7, label, 1, 0, 'L')
            pdf.cell(85, 7, value, 1, 1, 'C')
        
        pdf.ln(10)
        
        # Cost Comparison Table
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 10, "Material Cost Comparison")
        pdf.ln(12)
        
        pdf.set_font("helvetica", "B", 9)
        pdf.set_fill_color(15, 23, 42)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(70, 8, "Material", 1, 0, 'C', True)
        pdf.cell(50, 8, "Estimated Cost (Rs.)", 1, 0, 'C', True)
        pdf.cell(25, 8, "Strength", 1, 0, 'C', True)
        pdf.cell(25, 8, "Durability", 1, 1, 'C', True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("helvetica", "", 9)
        
        for idx, mat in enumerate(material_costs):
            if idx == 0:
                pdf.set_fill_color(220, 252, 231)
            elif idx == len(material_costs) - 1:
                pdf.set_fill_color(254, 226, 226)
            else:
                pdf.set_fill_color(255, 255, 255)
            
            pdf.cell(70, 7, mat['name'][:35], 1, 0, 'L', True)
            pdf.cell(50, 7, f"{mat['cost']:,.0f}", 1, 0, 'R', True)
            pdf.cell(25, 7, f"{mat['strength']}/100", 1, 0, 'C', True)
            pdf.cell(25, 7, f"{mat['durability']}/100", 1, 1, 'C', True)
        
        pdf.ln(10)
        
        # Cost Range Box
        if material_costs:
            min_cost = material_costs[0]['cost']
            max_cost = material_costs[-1]['cost']
            avg_cost = sum(m['cost'] for m in material_costs) / len(material_costs)
            
            pdf.set_fill_color(241, 245, 249)
            pdf.rect(20, pdf.get_y(), 170, 30, 'F')
            
            pdf.set_font("helvetica", "B", 11)
            pdf.set_xy(25, pdf.get_y() + 3)
            pdf.cell(0, 7, "Estimated Cost Range")
            
            pdf.set_font("helvetica", "", 10)
            pdf.set_xy(25, pdf.get_y() + 10)
            pdf.cell(55, 6, f"Minimum: Rs. {min_cost:,.0f}")
            pdf.cell(55, 6, f"Average: Rs. {avg_cost:,.0f}")
            pdf.cell(55, 6, f"Maximum: Rs. {max_cost:,.0f}")
        
        # ===== PAGE 3: RECOMMENDATIONS =====
        pdf.add_page()
        
        pdf.set_font("helvetica", "B", 16)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 10, "Recommended Materials")
        pdf.ln(15)
        
        if recs:
            seen = set()
            rank = 1
            for rec in recs[:5]:
                if rec['name'] in seen:
                    continue
                seen.add(rec['name'])
                
                pdf.set_fill_color(241, 245, 249)
                pdf.rect(20, pdf.get_y(), 170, 22, 'F')
                
                pdf.set_font("helvetica", "B", 11)
                pdf.set_xy(25, pdf.get_y() + 3)
                pdf.cell(0, 6, f"{rank}. {rec['name']}")
                
                pdf.set_font("helvetica", "", 9)
                pdf.set_xy(25, pdf.get_y() + 9)
                pdf.cell(50, 5, f"Score: {rec['score']:.2f}")
                pdf.cell(50, 5, f"Strength: {rec['strength']}/100")
                pdf.cell(50, 5, f"Durability: {rec['durability']}/100")
                
                pdf.ln(25)
                rank += 1
        
        pdf.ln(5)
        
        # Notes
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 8, "Important Notes")
        pdf.ln(8)
        
        pdf.set_font("helvetica", "", 9)
        notes = [
            "Cost estimates are based on current market rates in India (2026).",
            "Actual costs will vary based on location, labor rates, and availability.",
            "This estimate covers walls only - foundation, roofing, doors, windows, and finishing are excluded.",
            "Consult a licensed structural engineer before construction.",
            "Prices are approximate and should be verified with local suppliers."
        ]
        
        for note in notes:
            pdf.cell(5, 5, "")
            pdf.multi_cell(160, 5, f"- {note}")
            pdf.ln(1)
        
        # Footer
        pdf.set_y(-25)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(3)
        pdf.set_font("helvetica", "I", 8)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 4, f"Floor3D Report | Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}", align="C")
        
        pdf_bytes = pdf.output()
        
        return Response(
            content=bytes(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Floor3D_Report_{project_id[:8]}.pdf"}
        )
    except Exception as e:
        import traceback
        print(f"ERROR in export_report: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
