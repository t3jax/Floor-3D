"""
Autonomous Structural Intelligence System — FastAPI entry.
"""

from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import os
from fpdf import FPDF

from app.pipeline import process_fallback, process_image_bytes
from app.materials import load_materials, top_k_materials
from app.schemas import FallbackGraphInput, ProcessResult
from app.database import get_db

class ExportReportRequest(BaseModel):
    image_base64: str = ""

app = FastAPI(
    title="Autonomous Structural Intelligence System",
    version="0.1.0",
    description="Floor plan → graph → materials + LLM prompt template.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/process-floorplan", response_model=ProcessResult)
async def process_floorplan(file: UploadFile = File(...)) -> ProcessResult:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Expected an image file.")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    return process_image_bytes(data)


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


@app.post("/api/export-report/{project_id}")
def export_report(project_id: str, payload: ExportReportRequest) -> Response:
    from datetime import datetime
    import tempfile
    
    conn = get_db()
    c = conn.cursor()
    
    # Fetch Recommendations & Structural Data
    c.execute("SELECT element_type, SUM(length_px) as total_len, COUNT(*) as count FROM Structural_Elements WHERE project_id=? GROUP BY element_type", (project_id,))
    elements = c.fetchall()
    
    c.execute("SELECT r.element_id, m.name, r.score, r.llm_explanation, m.cost_per_unit, m.strength, m.durability FROM Recommendations r JOIN Materials m ON r.material_id = m.id WHERE r.project_id=? ORDER BY r.score DESC", (project_id,))
    recs = c.fetchall()
    conn.close()
    
    # Calculate totals
    total_length_px = sum(el['total_len'] for el in elements) if elements else 0
    total_wall_count = sum(el['count'] for el in elements) if elements else 0
    exterior_walls = next((el for el in elements if el['element_type'] == 'exterior'), None)
    interior_walls = next((el for el in elements if el['element_type'] == 'interior'), None)
    
    # Scale: 1px = 0.01m, wall height = 3m, wall thickness = 0.23m
    scale_factor = 0.01
    wall_height = 3.0
    wall_thickness = 0.23
    total_length_m = total_length_px * scale_factor
    total_volume_m3 = total_length_m * wall_height * wall_thickness
    
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- PAGE 1: Title & Executive Summary ---
    pdf.add_page()
    
    # Header
    pdf.set_fill_color(45, 55, 72)  # Dark slate
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 20)
    pdf.set_y(10)
    pdf.cell(0, 10, "Floor3D Structural Analysis Report", align="C")
    pdf.set_font("helvetica", "", 10)
    pdf.set_y(22)
    pdf.cell(0, 6, f"Project ID: {project_id}  |  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C")
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_y(45)
    
    # Executive Summary Box
    pdf.set_fill_color(248, 250, 252)
    pdf.rect(10, 45, 190, 35, 'F')
    pdf.set_font("helvetica", "B", 12)
    pdf.set_xy(15, 48)
    pdf.cell(0, 8, "Executive Summary")
    pdf.set_font("helvetica", "", 10)
    pdf.set_xy(15, 58)
    
    # Calculate estimated cost
    base_cost_per_m3 = 5500  # INR per cubic meter (average)
    estimated_cost = total_volume_m3 * base_cost_per_m3
    
    summary_text = (
        f"This report analyzes the floor plan structure with {total_wall_count} wall segments "
        f"totaling {total_length_m:.1f} meters in length. Estimated wall volume: {total_volume_m3:.2f} m3. "
        f"Approximate construction cost: Rs.{estimated_cost:,.0f} (based on standard materials)."
    )
    pdf.multi_cell(180, 5, summary_text)
    
    pdf.set_y(90)
    
    # Floor Plan Image (if provided)
    if payload.image_base64 and "," in payload.image_base64:
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 8, "Floor Plan Layout", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        
        header, encoded = payload.image_base64.split(",", 1)
        img_data = base64.b64decode(encoded)
        
        # Use tempfile for cross-platform compatibility
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            tmp_file.write(img_data)
            img_path = tmp_file.name
        
        try:
            pdf.image(img_path, x=25, w=160)
        except:
            pass
        finally:
            try:
                os.remove(img_path)
            except:
                pass
        
        pdf.ln(5)
    
    # --- PAGE 2: Structural Analysis ---
    pdf.add_page()
    
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "Structural Analysis", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    
    # Wall Statistics Table
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 8, "Wall Statistics", new_x="LMARGIN", new_y="NEXT")
    
    # Table header
    pdf.set_fill_color(45, 55, 72)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(50, 8, "Wall Type", 1, 0, 'C', True)
    pdf.cell(35, 8, "Count", 1, 0, 'C', True)
    pdf.cell(45, 8, "Length (m)", 1, 0, 'C', True)
    pdf.cell(45, 8, "Volume (m3)", 1, 1, 'C', True)
    
    # Table rows
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "", 9)
    
    if exterior_walls:
        ext_len = exterior_walls['total_len'] * scale_factor
        ext_vol = ext_len * wall_height * wall_thickness
        pdf.set_fill_color(252, 252, 252)
        pdf.cell(50, 7, "Exterior Walls", 1, 0, 'L', True)
        pdf.cell(35, 7, str(exterior_walls['count']), 1, 0, 'C', True)
        pdf.cell(45, 7, f"{ext_len:.2f}", 1, 0, 'C', True)
        pdf.cell(45, 7, f"{ext_vol:.2f}", 1, 1, 'C', True)
    
    if interior_walls:
        int_len = interior_walls['total_len'] * scale_factor
        int_vol = int_len * wall_height * wall_thickness
        pdf.set_fill_color(248, 248, 248)
        pdf.cell(50, 7, "Interior Walls", 1, 0, 'L', True)
        pdf.cell(35, 7, str(interior_walls['count']), 1, 0, 'C', True)
        pdf.cell(45, 7, f"{int_len:.2f}", 1, 0, 'C', True)
        pdf.cell(45, 7, f"{int_vol:.2f}", 1, 1, 'C', True)
    
    # Total row
    pdf.set_fill_color(226, 232, 240)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(50, 7, "TOTAL", 1, 0, 'L', True)
    pdf.cell(35, 7, str(total_wall_count), 1, 0, 'C', True)
    pdf.cell(45, 7, f"{total_length_m:.2f}", 1, 0, 'C', True)
    pdf.cell(45, 7, f"{total_volume_m3:.2f}", 1, 1, 'C', True)
    
    pdf.ln(8)
    
    # --- Material Recommendations ---
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "Material Recommendations", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    
    if recs:
        # Table header
        pdf.set_fill_color(45, 55, 72)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(45, 8, "Material", 1, 0, 'C', True)
        pdf.cell(25, 8, "Score", 1, 0, 'C', True)
        pdf.cell(30, 8, "Strength", 1, 0, 'C', True)
        pdf.cell(30, 8, "Durability", 1, 0, 'C', True)
        pdf.cell(45, 8, "Cost (Rs./m3)", 1, 1, 'C', True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("helvetica", "", 9)
        
        seen_materials = set()
        for idx, rec in enumerate(recs):
            if rec['name'] in seen_materials:
                continue
            seen_materials.add(rec['name'])
            
            fill = 252 if idx % 2 == 0 else 248
            pdf.set_fill_color(fill, fill, fill)
            
            pdf.cell(45, 7, rec['name'], 1, 0, 'L', True)
            pdf.cell(25, 7, f"{rec['score']:.2f}", 1, 0, 'C', True)
            pdf.cell(30, 7, f"{rec['strength'] or 0}/10", 1, 0, 'C', True)
            pdf.cell(30, 7, f"{rec['durability'] or 0}/10", 1, 0, 'C', True)
            pdf.cell(45, 7, f"Rs.{rec['cost_per_unit']:,.0f}", 1, 1, 'C', True)
            
            if len(seen_materials) >= 5:
                break
    
    pdf.ln(8)
    
    # --- Cost Estimation ---
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "Cost Estimation", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    
    # Cost comparison table
    material_costs = [
        ("Red Brick (Traditional)", 4500, "Budget-friendly, widely available"),
        ("AAC Blocks", 5500, "Lightweight, good insulation"),
        ("Fly Ash Bricks", 5000, "Eco-friendly, economical"),
        ("RCC (Reinforced Concrete)", 7500, "High strength, load-bearing"),
        ("Precast Concrete", 8500, "Fast construction, quality finish"),
    ]
    
    pdf.set_fill_color(45, 55, 72)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(55, 8, "Material Option", 1, 0, 'C', True)
    pdf.cell(35, 8, "Cost/m3", 1, 0, 'C', True)
    pdf.cell(45, 8, "Estimated Total", 1, 0, 'C', True)
    pdf.cell(40, 8, "Notes", 1, 1, 'C', True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "", 9)
    
    for idx, (mat_name, cost_per_m3, note) in enumerate(material_costs):
        total_mat_cost = total_volume_m3 * cost_per_m3
        fill = 252 if idx % 2 == 0 else 248
        pdf.set_fill_color(fill, fill, fill)
        
        pdf.cell(55, 7, mat_name, 1, 0, 'L', True)
        pdf.cell(35, 7, f"Rs.{cost_per_m3:,}", 1, 0, 'C', True)
        pdf.cell(45, 7, f"Rs.{total_mat_cost:,.0f}", 1, 0, 'C', True)
        pdf.cell(40, 7, note[:20], 1, 1, 'L', True)
    
    pdf.ln(8)
    
    # Key Notes
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 8, "Important Notes", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 9)
    
    notes = [
        "1. Costs are estimates based on standard market rates and may vary by location.",
        "2. Wall specifications: Height = 3.0m, Thickness = 0.23m (standard).",
        "3. Actual construction costs may include labor, finishing, and fixtures.",
        "4. Consult a structural engineer for load-bearing wall specifications.",
        "5. Material selection should consider local climate and building codes.",
    ]
    
    for note in notes:
        pdf.cell(0, 5, note, new_x="LMARGIN", new_y="NEXT")
    
    # Footer
    pdf.set_y(-25)
    pdf.set_font("helvetica", "I", 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 5, "This report is auto-generated by Floor3D Structural Analysis System.", align="C")
    pdf.ln(4)
    pdf.cell(0, 5, "For professional construction, please consult with licensed engineers and architects.", align="C")
    
    pdf_bytes = pdf.output()
    
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Floor3D_Report_{project_id}.pdf"}
    )
