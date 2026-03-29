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
    
    # Fetch all data needed for comprehensive report
    c.execute("SELECT element_type, SUM(length_px) as total_len, COUNT(*) as count FROM Structural_Elements WHERE project_id=? GROUP BY element_type", (project_id,))
    elements = c.fetchall()
    
    c.execute("""
        SELECT r.element_id, m.id as material_id, m.name, r.score, r.llm_explanation, 
               m.cost_per_unit, m.strength, m.durability, m.unit, m.notes 
        FROM Recommendations r 
        JOIN Materials m ON r.material_id = m.id 
        WHERE r.project_id=? 
        ORDER BY r.score DESC
    """, (project_id,))
    recs = c.fetchall()
    
    # Fetch all materials for cost comparison
    c.execute("SELECT * FROM Materials")
    all_materials = c.fetchall()
    conn.close()
    
    # Calculate structural metrics
    total_length_px = sum(el['total_len'] for el in elements) if elements else 0
    total_wall_count = sum(el['count'] for el in elements) if elements else 0
    exterior_walls = next((el for el in elements if el['element_type'] == 'exterior'), None)
    interior_walls = next((el for el in elements if el['element_type'] == 'interior'), None)
    
    # Physical constants
    SCALE_FACTOR = 0.01  # 1px = 0.01m
    WALL_HEIGHT = 3.0    # meters
    WALL_THICKNESS = 0.23  # meters (9 inches standard)
    
    # Calculate dimensions
    total_length_m = total_length_px * SCALE_FACTOR
    total_area_m2 = total_length_m * WALL_HEIGHT
    total_volume_m3 = total_length_m * WALL_HEIGHT * WALL_THICKNESS
    
    # Separate exterior and interior metrics
    ext_len_m = (exterior_walls['total_len'] * SCALE_FACTOR) if exterior_walls else 0
    ext_area_m2 = ext_len_m * WALL_HEIGHT
    ext_volume_m3 = ext_len_m * WALL_HEIGHT * WALL_THICKNESS
    
    int_len_m = (interior_walls['total_len'] * SCALE_FACTOR) if interior_walls else 0
    int_area_m2 = int_len_m * WALL_HEIGHT
    int_volume_m3 = int_len_m * WALL_HEIGHT * WALL_THICKNESS
    
    # Initialize PDF with better margins
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 15, 15)
    
    # ============================================
    # PAGE 1: COVER PAGE & FLOOR PLAN
    # ============================================
    pdf.add_page()
    
    # Professional Header
    pdf.set_fill_color(37, 99, 235)  # Blue
    pdf.rect(0, 0, 210, 60, 'F')
    
    # Title
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 24)
    pdf.set_y(20)
    pdf.cell(0, 12, "FLOOR3D", align="C")
    
    pdf.set_font("helvetica", "", 16)
    pdf.set_y(35)
    pdf.cell(0, 10, "Structural Analysis & Cost Estimation Report", align="C")
    
    # Project info bar
    pdf.set_fill_color(30, 64, 175)
    pdf.rect(0, 60, 210, 12, 'F')
    pdf.set_font("helvetica", "", 9)
    pdf.set_y(63)
    pdf.cell(0, 6, f"Project ID: {project_id[:8]}  |  Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", align="C")
    
    # Reset colors
    pdf.set_text_color(0, 0, 0)
    pdf.set_y(80)
    
    # Executive Summary Box
    pdf.set_fill_color(239, 246, 255)
    pdf.set_draw_color(191, 219, 254)
    pdf.rect(15, 80, 180, 45, 'FD')
    
    pdf.set_font("helvetica", "B", 13)
    pdf.set_xy(20, 83)
    pdf.cell(0, 8, "EXECUTIVE SUMMARY")
    
    pdf.set_font("helvetica", "", 10)
    pdf.set_xy(20, 93)
    
    # Calculate recommended cost (using top material)
    recommended_cost = 0
    if recs:
        top_material_cost_per_unit = recs[0]['cost_per_unit']
        # Approximate conversion based on unit type
        if 'sqft' in recs[0]['unit'].lower():
            recommended_cost = total_area_m2 * 10.764 * top_material_cost_per_unit
        else:
            recommended_cost = total_volume_m3 * top_material_cost_per_unit * 50
    else:
        recommended_cost = total_volume_m3 * 5500
    
    summary_lines = [
        f"Total Walls Detected: {total_wall_count} segments ({exterior_walls['count'] if exterior_walls else 0} exterior, {interior_walls['count'] if interior_walls else 0} interior)",
        f"Total Wall Length: {total_length_m:.2f} meters ({ext_len_m:.2f}m exterior + {int_len_m:.2f}m interior)",
        f"Estimated Wall Volume: {total_volume_m3:.2f} cubic meters",
        f"Estimated Construction Cost: Rs. {recommended_cost:,.0f} (recommended materials)",
    ]
    
    y_pos = 93
    for line in summary_lines:
        pdf.set_xy(20, y_pos)
        pdf.multi_cell(160, 5, line)
        y_pos += 7
    
    pdf.set_y(135)
    
    # Floor Plan Image Section
    if payload.image_base64 and "," in payload.image_base64:
        pdf.set_font("helvetica", "B", 12)
        pdf.set_fill_color(249, 250, 251)
        pdf.rect(15, 135, 180, 8, 'F')
        pdf.set_xy(20, 136)
        pdf.cell(0, 6, "DETECTED FLOOR PLAN LAYOUT")
        
        pdf.ln(12)
        
        try:
            header, encoded = payload.image_base64.split(",", 1)
            img_data = base64.b64decode(encoded)
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_file.write(img_data)
                img_path = tmp_file.name
            
            # Center and size the image appropriately
            pdf.image(img_path, x=30, y=pdf.get_y(), w=150)
            os.remove(img_path)
        except Exception as e:
            pdf.set_font("helvetica", "I", 9)
            pdf.cell(0, 6, "[Floor plan image could not be embedded]", align="C")
    
    # ============================================
    # PAGE 2: DETAILED STRUCTURAL ANALYSIS
    # ============================================
    pdf.add_page()
    
    # Section header
    pdf.set_fill_color(37, 99, 235)
    pdf.rect(15, 15, 180, 10, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 12)
    pdf.set_xy(20, 17)
    pdf.cell(0, 6, "1. STRUCTURAL ANALYSIS")
    pdf.set_text_color(0, 0, 0)
    
    pdf.set_y(30)
    
    # Wall Breakdown Table
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 8, "Wall Type Breakdown", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    
    # Table header
    pdf.set_fill_color(51, 65, 85)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(45, 8, "Wall Type", 1, 0, 'C', True)
    pdf.cell(25, 8, "Count", 1, 0, 'C', True)
    pdf.cell(35, 8, "Length (m)", 1, 0, 'C', True)
    pdf.cell(35, 8, "Area (m2)", 1, 0, 'C', True)
    pdf.cell(35, 8, "Volume (m3)", 1, 1, 'C', True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "", 9)
    
    # Exterior walls row
    if exterior_walls:
        pdf.set_fill_color(254, 249, 195)
        pdf.cell(45, 7, "Exterior Walls", 1, 0, 'L', True)
        pdf.cell(25, 7, str(exterior_walls['count']), 1, 0, 'C', True)
        pdf.cell(35, 7, f"{ext_len_m:.2f}", 1, 0, 'C', True)
        pdf.cell(35, 7, f"{ext_area_m2:.2f}", 1, 0, 'C', True)
        pdf.cell(35, 7, f"{ext_volume_m3:.2f}", 1, 1, 'C', True)
    
    # Interior walls row
    if interior_walls:
        pdf.set_fill_color(224, 242, 254)
        pdf.cell(45, 7, "Interior Walls", 1, 0, 'L', True)
        pdf.cell(25, 7, str(interior_walls['count']), 1, 0, 'C', True)
        pdf.cell(35, 7, f"{int_len_m:.2f}", 1, 0, 'C', True)
        pdf.cell(35, 7, f"{int_area_m2:.2f}", 1, 0, 'C', True)
        pdf.cell(35, 7, f"{int_volume_m3:.2f}", 1, 1, 'C', True)
    
    # Total row
    pdf.set_fill_color(203, 213, 225)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(45, 7, "TOTAL", 1, 0, 'L', True)
    pdf.cell(25, 7, str(total_wall_count), 1, 0, 'C', True)
    pdf.cell(35, 7, f"{total_length_m:.2f}", 1, 0, 'C', True)
    pdf.cell(35, 7, f"{total_area_m2:.2f}", 1, 0, 'C', True)
    pdf.cell(35, 7, f"{total_volume_m3:.2f}", 1, 1, 'C', True)
    
    pdf.ln(10)
    
    # Technical Specifications
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 8, "Technical Specifications", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    
    pdf.set_font("helvetica", "", 9)
    specs = [
        ["Parameter", "Value", "Standard"],
        ["Wall Height", f"{WALL_HEIGHT} meters", "Residential standard"],
        ["Wall Thickness", f"{WALL_THICKNESS} meters (9 inches)", "Load-bearing standard"],
        ["Detection Scale", f"1 pixel = {SCALE_FACTOR} meters", "Calibrated from input"],
    ]
    
    for idx, row in enumerate(specs):
        if idx == 0:
            pdf.set_fill_color(51, 65, 85)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("helvetica", "B", 9)
        else:
            pdf.set_fill_color(248, 250, 252)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("helvetica", "", 9)
        
        pdf.cell(50, 7, row[0], 1, 0, 'L', True)
        pdf.cell(45, 7, row[1], 1, 0, 'C', True)
        pdf.cell(80, 7, row[2], 1, 1, 'L', True)
    
    # ============================================
    # PAGE 3: MATERIAL RECOMMENDATIONS
    # ============================================
    pdf.add_page()
    
    # Section header
    pdf.set_fill_color(37, 99, 235)
    pdf.rect(15, 15, 180, 10, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 12)
    pdf.set_xy(20, 17)
    pdf.cell(0, 6, "2. MATERIAL RECOMMENDATIONS")
    pdf.set_text_color(0, 0, 0)
    
    pdf.set_y(30)
    
    if recs:
        pdf.set_font("helvetica", "", 9)
        pdf.multi_cell(0, 5, "Our AI-powered material selection engine analyzes strength, durability, and cost factors to recommend the optimal materials for your construction project.")
        pdf.ln(3)
        
        # Recommended Materials Table
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 8, "Top Recommended Materials (Ranked by Performance Score)", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        
        # Table header
        pdf.set_fill_color(51, 65, 85)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("helvetica", "B", 8)
        pdf.cell(12, 8, "Rank", 1, 0, 'C', True)
        pdf.cell(50, 8, "Material Name", 1, 0, 'C', True)
        pdf.cell(22, 8, "Score", 1, 0, 'C', True)
        pdf.cell(24, 8, "Strength", 1, 0, 'C', True)
        pdf.cell(26, 8, "Durability", 1, 0, 'C', True)
        pdf.cell(41, 8, "Unit Cost", 1, 1, 'C', True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("helvetica", "", 8)
        
        seen_materials = set()
        rank = 1
        for rec in recs:
            if rec['name'] in seen_materials or rank > 6:
                continue
            seen_materials.add(rec['name'])
            
            # Color coding based on rank
            if rank == 1:
                pdf.set_fill_color(254, 249, 195)  # Gold
            elif rank == 2:
                pdf.set_fill_color(229, 231, 235)  # Silver
            elif rank == 3:
                pdf.set_fill_color(251, 207, 232)  # Bronze
            else:
                fill_color = 252 if rank % 2 == 0 else 247
                pdf.set_fill_color(fill_color, fill_color, fill_color)
            
            pdf.cell(12, 7, str(rank), 1, 0, 'C', True)
            pdf.cell(50, 7, rec['name'][:28], 1, 0, 'L', True)
            pdf.cell(22, 7, f"{rec['score']:.2f}", 1, 0, 'C', True)
            pdf.cell(24, 7, f"{rec['strength']:.0f}/100", 1, 0, 'C', True)
            pdf.cell(26, 7, f"{rec['durability']:.0f}/100", 1, 0, 'C', True)
            pdf.cell(41, 7, f"Rs.{rec['cost_per_unit']:.0f}/{rec['unit'][:6]}", 1, 1, 'C', True)
            
            rank += 1
        
        pdf.ln(5)
        
        # Material Notes
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(0, 6, "Material Selection Notes:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 8)
        
        for idx, rec in enumerate(list(recs)[:3]):
            if rec['name'] in list(seen_materials)[:3]:
                pdf.set_font("helvetica", "B", 8)
                pdf.cell(0, 5, f"{idx+1}. {rec['name']}", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("helvetica", "", 8)
                pdf.multi_cell(0, 4, f"   {rec['notes']}")
                pdf.ln(1)
    
    # ============================================
    # PAGE 4: DETAILED COST ANALYSIS
    # ============================================
    pdf.add_page()
    
    # Section header
    pdf.set_fill_color(37, 99, 235)
    pdf.rect(15, 15, 180, 10, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 12)
    pdf.set_xy(20, 17)
    pdf.cell(0, 6, "3. COST ESTIMATION & COMPARISON")
    pdf.set_text_color(0, 0, 0)
    
    pdf.set_y(30)
    
    pdf.set_font("helvetica", "", 9)
    pdf.multi_cell(0, 5, f"Cost estimates are calculated based on the total wall volume of {total_volume_m3:.2f} cubic meters. Prices are in Indian Rupees (INR) and reflect current market rates.")
    pdf.ln(3)
    
    # Comprehensive Cost Comparison Table
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 8, "Material Cost Comparison (All Options)", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    
    # Calculate costs for all materials
    material_cost_data = []
    for mat in all_materials:
        # Approximate cost calculation based on unit type
        if 'sqft' in mat['unit'].lower() or 'sq' in mat['unit'].lower():
            total_cost = total_area_m2 * 10.764 * mat['cost_per_unit']  # m2 to sqft
            unit_display = f"{mat['cost_per_unit']:.0f}/sqft"
        elif 'cum' in mat['unit'].lower() or 'm3' in mat['unit'].lower():
            total_cost = total_volume_m3 * mat['cost_per_unit']
            unit_display = f"{mat['cost_per_unit']:.0f}/m3"
        else:
            total_cost = total_volume_m3 * mat['cost_per_unit'] * 50  # Approximation
            unit_display = f"{mat['cost_per_unit']:.0f}/{mat['unit']}"
        
        material_cost_data.append({
            'name': mat['name'],
            'unit_cost': unit_display,
            'total_cost': total_cost,
            'strength': mat['strength'],
            'durability': mat['durability']
        })
    
    # Sort by total cost
    material_cost_data.sort(key=lambda x: x['total_cost'])
    
    # Table header
    pdf.set_fill_color(51, 65, 85)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 8)
    pdf.cell(55, 8, "Material", 1, 0, 'C', True)
    pdf.cell(35, 8, "Unit Cost", 1, 0, 'C', True)
    pdf.cell(45, 8, "Estimated Total", 1, 0, 'C', True)
    pdf.cell(40, 8, "Rating (S/D)", 1, 1, 'C', True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "", 8)
    
    # Find min and max costs for color coding
    min_cost = min(m['total_cost'] for m in material_cost_data)
    max_cost = max(m['total_cost'] for m in material_cost_data)
    
    for idx, mat_data in enumerate(material_cost_data):
        # Color code by cost (green = cheap, yellow = medium, red = expensive)
        cost_ratio = (mat_data['total_cost'] - min_cost) / (max_cost - min_cost) if max_cost > min_cost else 0
        
        if cost_ratio < 0.33:
            pdf.set_fill_color(220, 252, 231)  # Light green
        elif cost_ratio < 0.66:
            pdf.set_fill_color(254, 249, 195)  # Light yellow
        else:
            pdf.set_fill_color(254, 226, 226)  # Light red
        
        pdf.cell(55, 7, mat_data['name'][:30], 1, 0, 'L', True)
        pdf.cell(35, 7, f"Rs. {mat_data['unit_cost']}", 1, 0, 'C', True)
        pdf.cell(45, 7, f"Rs. {mat_data['total_cost']:,.0f}", 1, 0, 'R', True)
        pdf.cell(40, 7, f"{mat_data['strength']:.0f} / {mat_data['durability']:.0f}", 1, 1, 'C', True)
    
    pdf.ln(8)
    
    # Cost Summary Box
    pdf.set_fill_color(239, 246, 255)
    pdf.set_draw_color(191, 219, 254)
    pdf.rect(15, pdf.get_y(), 180, 30, 'FD')
    
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 8, "COST SUMMARY", new_x="LMARGIN", new_y="NEXT", align="C")
    
    pdf.set_font("helvetica", "", 9)
    min_mat = material_cost_data[0]
    max_mat = material_cost_data[-1]
    avg_cost = sum(m['total_cost'] for m in material_cost_data) / len(material_cost_data)
    
    pdf.cell(0, 5, f"Lowest Cost Option: {min_mat['name']} - Rs. {min_mat['total_cost']:,.0f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Highest Cost Option: {max_mat['name']} - Rs. {max_mat['total_cost']:,.0f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Average Estimated Cost: Rs. {avg_cost:,.0f}", new_x="LMARGIN", new_y="NEXT")
    
    # ============================================
    # PAGE 5: NOTES & DISCLAIMERS
    # ============================================
    pdf.add_page()
    
    # Section header
    pdf.set_fill_color(37, 99, 235)
    pdf.rect(15, 15, 180, 10, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 12)
    pdf.set_xy(20, 17)
    pdf.cell(0, 6, "4. IMPORTANT NOTES & DISCLAIMERS")
    pdf.set_text_color(0, 0, 0)
    
    pdf.set_y(30)
    
    # Calculation Methodology
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 8, "Calculation Methodology", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    
    pdf.set_font("helvetica", "", 9)
    methodology = [
        f"Wall Volume = Total Length ({total_length_m:.2f}m) x Height ({WALL_HEIGHT}m) x Thickness ({WALL_THICKNESS}m)",
        f"Material costs are calculated per cubic meter or square foot based on standard industry rates",
        f"Score = (Strength x 0.6 + Durability x 0.4) / Normalized Cost",
        f"Detection accuracy: Wall segments identified using OpenCV HoughLinesP algorithm"
    ]
    
    for line in methodology:
        pdf.cell(5, 5, "", 0)
        pdf.multi_cell(0, 5, f"• {line}")
    
    pdf.ln(5)
    
    # Important Disclaimers
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 8, "Important Disclaimers", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    
    pdf.set_font("helvetica", "", 9)
    disclaimers = [
        "Cost estimates are approximate and based on average market rates in India as of 2026",
        "Actual construction costs will vary based on location, labor rates, and material availability",
        "This report does not include costs for: foundation, roofing, doors, windows, electrical, plumbing, or finishing",
        "Material recommendations are based on general strength and durability ratings",
        "Structural load calculations must be verified by a licensed structural engineer",
        "Building codes and regulations vary by location - consult local authorities",
        "Foundation requirements depend on soil conditions and must be assessed separately",
        "This is an automated analysis tool - professional review is recommended for actual construction"
    ]
    
    for disclaimer in disclaimers:
        pdf.cell(5, 5, "", 0)
        pdf.multi_cell(0, 5, f"• {disclaimer}")
    
    pdf.ln(8)
    
    # Next Steps
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 8, "Recommended Next Steps", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    
    pdf.set_font("helvetica", "", 9)
    next_steps = [
        "Consult with a licensed structural engineer for detailed structural design",
        "Obtain soil testing report for foundation design",
        "Get detailed quotes from local material suppliers",
        "Review and comply with local building codes and zoning regulations",
        "Consider climate-specific requirements for material selection",
        "Plan for electrical, plumbing, and HVAC installations",
        "Obtain necessary permits before starting construction"
    ]
    
    for step in next_steps:
        pdf.cell(5, 5, "", 0)
        pdf.multi_cell(0, 5, f"• {step}")
    
    # Footer
    pdf.set_y(-30)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(3)
    
    pdf.set_font("helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 4, "Floor3D - AI-Powered Floor Plan Analysis & Cost Estimation", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 4, f"Report generated on {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 4, "For questions or support, contact: support@floor3d.com", new_x="LMARGIN", new_y="NEXT", align="C")
    
    pdf_bytes = pdf.output()
    
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Floor3D_Report_{project_id[:8]}.pdf"}
    )
