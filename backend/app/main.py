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
    conn = get_db()
    c = conn.cursor()
    
    # Fetch Recommendations & Structural Math
    c.execute("SELECT element_type, SUM(length_px) as total_len FROM Structural_Elements WHERE project_id=? GROUP BY element_type", (project_id,))
    elements = c.fetchall()
    
    c.execute("SELECT r.element_id, m.name, r.score, r.llm_explanation, m.cost_per_unit FROM Recommendations r JOIN Materials m ON r.material_id = m.id WHERE r.project_id=?", (project_id,))
    recs = c.fetchall()
    conn.close()
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "Autonomous Structural Intelligence: Report", new_x="LMARGIN", new_y="NEXT", align="C")
    
    # Process Header Image
    if payload.image_base64 and "," in payload.image_base64:
        header, encoded = payload.image_base64.split(",", 1)
        img_data = base64.b64decode(encoded)
        img_path = f"/tmp/{project_id}_canvas.png"
        os.makedirs(os.path.dirname(img_path), exist_ok=True)
        with open(img_path, "wb") as f:
            f.write(img_data)
        pdf.image(img_path, x=10, y=30, w=190)
        os.remove(img_path)
        pdf.set_y(150) # Move down below image
    else:
        pdf.set_y(30)
        
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Estimated Material Requirements & Cost Breakdown", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", size=10)
    
    for el in elements:
        pdf.cell(0, 8, f"Element Group: {el['element_type'].upper()} (Total Span: {round(el['total_len'], 2)} px)", new_x="LMARGIN", new_y="NEXT")
        for rec in recs:
            if rec['element_id'] == f"{el['element_type']}_walls" or rec['element_id'] == "general":
                # Volume = length_px * 0.1 * 3 meters (arbitrary proxy scalar for real-world)
                volume = (el['total_len'] / 100) * 0.3 * 3.0
                total_cost = volume * rec['cost_per_unit']
                pdf.cell(0, 6, f"   - Rec: {rec['name']} | Score: {rec['score']} | Est. Vol: {round(volume,2)}m3 | Est. Cost: ${round(total_cost,2)}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "AI Structural Analysis", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", size=10)
    
    if recs:
        explanation = recs[0]["llm_explanation"]
        pdf.multi_cell(0, 6, explanation.encode('latin-1', 'replace').decode('latin-1'))
        
    pdf_bytes = pdf.output()
    
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Structural_Report_{project_id}.pdf"}
    )
