import sqlite3
import json
import uuid
from pathlib import Path
from app.config import settings

DB_PATH = Path("structural_intelligence.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('DROP TABLE IF EXISTS Materials')
    # 1. Materials Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Materials (
            id TEXT PRIMARY KEY,
            name TEXT,
            strength REAL,
            durability REAL,
            cost_per_unit REAL,
            unit TEXT,
            notes TEXT
        )
    ''')
    
    # 2. Structural_Elements Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Structural_Elements (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            element_type TEXT,
            length_px REAL,
            has_second_floor BOOLEAN
        )
    ''')
    
    # 3. Recommendations Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Recommendations (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            element_id TEXT,
            material_id TEXT,
            score REAL,
            llm_explanation TEXT,
            total_cost REAL,
            volume_m3 REAL
        )
    ''')
    
    conn.commit()
    
    # Seed initial materials from JSON if table is empty
    c.execute('SELECT COUNT(*) FROM Materials')
    if c.fetchone()[0] == 0:
        json_path = settings.materials_path
        if json_path.exists():
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
                for m in data.get("materials", []):
                    c.execute('''
                        INSERT INTO Materials (
                            id, name, strength, durability, cost_per_unit, unit, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        m.get("id", str(uuid.uuid4())), 
                        m.get("name", "Unknown Material"), 
                        m.get("strength", 0.0), 
                        m.get("durability", 0.0), 
                        m.get("cost_per_unit", 0.0),
                        m.get("unit", ""),
                        m.get("notes", "")
                    ))
        conn.commit()

    conn.close()

# Run initialization immediately when imported
init_db()
