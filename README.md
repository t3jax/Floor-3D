# Autonomous Structural Intelligence System (ASIS)

A comprehensive web application that analyzes 2D floor plans and generates 3D models with intelligent material recommendations.

## 🏗️ System Overview

ASIS transforms architectural floor plans into intelligent structural analysis by:
- **Computer Vision**: Uses OpenCV to detect walls, rooms, and openings from 2D images
- **Geometric Processing**: Converts detected lines into structured graphs with coordinate snapping
- **3D Visualization**: Extrudes 2D geometry into interactive 3D models using Three.js
- **Material Intelligence**: Recommends optimal materials based on cost-strength-durability tradeoffs
- **AI Analysis**: Generates explanatory prompts for structural engineering insights

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Start the FastAPI server:
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install Node.js dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

The frontend will be available at `http://localhost:3000`

## 📋 Core Features

### 🔍 OpenCV Detection Engine
- **Canny Edge Detection**: Identifies wall boundaries
- **HoughLinesP**: Detects straight wall segments
- **Contour Analysis**: Finds enclosed room regions
- **Coordinate Snapping**: Ensures wall junctions align perfectly (10px tolerance)

### 📐 Geometric Processing
- **Graph Construction**: Converts segments to node-edge graphs
- **Room Detection**: Uses Shapely for polygon identification
- **Wall Classification**: Distinguishes exterior (load-bearing) from interior walls
- **Geometry Integrity**: Epsilon-based snapping prevents floating elements

### 🏗️ 3D Visualization
- **Interactive Models**: Mouse-controlled camera movement
- **Wall Rendering**: Different colors for exterior (brown) vs interior (gray) walls
- **Floor Generation**: Automatic floor plane creation from room polygons
- **Real-time Rendering**: Smooth Three.js visualization

### 🧱 Material Intelligence
- **Cost-Strength Tradeoff**: Score = (Strength × 0.6 + Durability × 0.4) / Cost
- **Context-Aware Recommendations**: Different materials for exterior vs interior walls
- **Material Database**: AAC, Red Brick, RCC, Steel, Fly Ash, Precast options
- **Room-Specific Analysis**: Tailored recommendations based on room size

### 🤖 AI Integration
- **LLM Prompts**: Structured prompts for material explanation
- **Geometric Context**: Includes wall spans, types, and room statistics
- **Engineering Insights**: Tradeoff analysis and performance explanations

## 🏛️ Architecture

### Backend (Python/FastAPI)
```
backend/
├── app/
│   ├── main.py              # FastAPI application entry
│   ├── opencv_engine.py     # OpenCV wall detection
│   ├── geometry_graph.py    # Shapely geometry processing
│   ├── materials.py         # Material optimization
│   ├── pipeline.py          # Processing orchestration
│   ├── snapping.py          # Coordinate snapping utilities
│   ├── llm_prompt.py        # AI prompt generation
│   └── schemas.py           # Pydantic data models
├── data/
│   └── materials.json       # Material database
└── requirements.txt
```

### Frontend (React/TypeScript)
```
frontend/
├── src/
│   ├── components/
│   │   ├── ThreeViewer.tsx      # 3D visualization component
│   │   ├── ImageViewer.tsx      # 2D detection results
│   │   └── MaterialRecommendations.tsx
│   ├── services/
│   │   └── api.ts               # API client
│   ├── types/
│   │   └── index.ts             # TypeScript definitions
│   ├── App.tsx                  # Main application
│   └── index.tsx                # React entry point
├── public/
└── package.json
```

## 🎯 API Endpoints

### Floor Plan Processing
- `POST /api/process-floorplan` - Upload and analyze floor plan image
- `POST /api/process-fallback` - Manual geometry input when detection fails

### Material Information
- `GET /api/materials` - List all available materials
- `GET /api/materials/top?k=3` - Get top-k materials by score

### System Health
- `GET /health` - System status check

## 🧪 Testing

### Sample Floor Plan
A test floor plan is included:
```bash
python test_floorplan.py
```
This creates `test_floorplan.png` with multiple rooms and wall types.

### API Testing
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test floor plan processing
curl -X POST "http://localhost:8000/api/process-floorplan" \
     -F "file=@test_floorplan.png"
```

## 🔧 Configuration

### OpenCV Parameters (config.py)
- `snap_tolerance_px`: 10.0 (coordinate snapping tolerance)
- `canny_low`: 50, `canny_high`: 150 (edge detection thresholds)
- `hough_threshold`: 50 (line detection sensitivity)
- `min_line_length`: 30, `max_line_gap`: 10 (line parameters)

### Material Scoring Formula
```
Score = (Strength × 0.6 + Durability × 0.4) / Cost
```

## 🎨 UI Features

### Dashboard Layout
- **Stats Overview**: Nodes, walls, rooms, detection mode
- **2D Detection View**: Original image with detected lines overlay
- **3D Model View**: Interactive Three.js visualization
- **Material Recommendations**: Ranked suggestions with scores

### Interactive Elements
- File upload with drag-and-drop support
- Real-time processing indicators
- Error handling with fallback suggestions
- Responsive design for various screen sizes

## 🛠️ Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **OpenCV**: Computer vision and image processing
- **Shapely**: Geometric computation and spatial analysis
- **NumPy**: Numerical computing
- **Pydantic**: Data validation and settings

### Frontend
- **React 18**: Modern UI framework
- **TypeScript**: Type-safe development
- **Three.js**: 3D graphics and visualization
- **Tailwind CSS**: Utility-first styling
- **Axios**: HTTP client for API communication

## 📊 Material Database

The system includes 6 material types with comprehensive properties:

| Material | Strength | Durability | Cost/Unit | Best Use |
|----------|----------|------------|-----------|----------|
| AAC | 72 | 85 | 45 | Lightweight construction |
| Red Brick | 68 | 78 | 38 | Traditional masonry |
| RCC | 95 | 92 | 120 | High-strength structural |
| Steel | 98 | 88 | 200 | Maximum strength-to-weight |
| Fly Ash | 62 | 80 | 32 | Eco-friendly partitions |
| Precast | 88 | 90 | 95 | Fast construction |

## 🔮 Future Enhancements

- **Advanced Room Recognition**: Machine learning for room type identification
- **Structural Analysis**: Finite element analysis for load calculations
- **Cost Estimation**: Detailed material quantity and cost calculations
- **Export Features**: CAD file generation and BIM integration
- **Mobile Support**: Responsive design for tablet/mobile devices
- **Real-time Collaboration**: Multi-user editing and annotation

## 📄 License

This project is developed as a demonstration of autonomous structural intelligence systems.

## 🤝 Contributing

Contributions are welcome for enhancing the detection algorithms, expanding the material database, or improving the user interface.

---

**Built with ❤️ for computational architecture and structural intelligence**
