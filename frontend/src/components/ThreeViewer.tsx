import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import { PointerLockControls } from 'three/examples/jsm/controls/PointerLockControls';
import { GraphPayload, WallEdge, Point2D, StaircaseData, ScaleMetadata } from '../types';

interface ThreeViewerProps {
  graph: GraphPayload;
  width?: number;
  height?: number;
  totalCost?: number;
}

// Default constants (used as fallback)
const DEFAULT_WALL_HEIGHT = 3.0; // 3 meters per floor
const DEFAULT_WALL_THICKNESS_MAJOR = 0.23; // 9 inches for major walls
const DEFAULT_WALL_THICKNESS_MINOR = 0.115; // 4.5 inches for minor walls
const DEFAULT_SCALE_FACTOR = 0.01; // Convert pixels to meters (fallback)
const EYE_LEVEL = 1.6; // Human eye level in meters
const MOVE_SPEED = 5.0;
const DEFAULT_STAIR_STEP_HEIGHT = 0.15; // 15cm per step (as per spec)

type ViewLevel = 'level0' | 'level1' | 'all';

const ThreeViewer: React.FC<ThreeViewerProps> = ({ 
  graph, 
  width = 800, 
  height = 600,
  totalCost = 0
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  
  // Get scale factor from graph metadata or use default
  const scaleFactor = useMemo(() => {
    return graph.scale_metadata?.scale_factor || DEFAULT_SCALE_FACTOR;
  }, [graph.scale_metadata]);
  
  // Get scaling method info for display
  const scalingInfo = useMemo(() => {
    const meta = graph.scale_metadata;
    if (!meta) return { method: 'default', confidence: 0 };
    return {
      method: meta.scaling_method,
      confidence: meta.confidence,
      isHeuristic: meta.is_heuristic_scale,
      aspectRatio: meta.aspect_ratio
    };
  }, [graph.scale_metadata]);
  const [showInteriorWalls, setShowInteriorWalls] = useState(true);
  const [viewLevel, setViewLevel] = useState<ViewLevel>('all');
  const [voyagerMode, setVoyagerMode] = useState(false);
  const [currentFloor, setCurrentFloor] = useState(0);
  
  // Refs for Voyager mode
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const orbitControlsRef = useRef<OrbitControls | null>(null);
  const pointerControlsRef = useRef<PointerLockControls | null>(null);
  const wallMeshesRef = useRef<THREE.Mesh[]>([]);
  const staircaseBoundsRef = useRef<THREE.Box3 | null>(null);
  const moveStateRef = useRef({ forward: false, backward: false, left: false, right: false });
  const velocityRef = useRef(new THREE.Vector3());
  const directionRef = useRef(new THREE.Vector3());

  const handleEnterVoyager = useCallback(() => {
    if (!pointerControlsRef.current || !cameraRef.current) {
      alert('Voyager mode not available');
      return;
    }
    
    // Position camera at center of floor plan using dynamic scale
    const bounds = calculateBounds(graph.nodes);
    const centerX = ((bounds.minX + bounds.maxX) / 2) * scaleFactor;
    const centerZ = ((bounds.minY + bounds.maxY) / 2) * scaleFactor;
    cameraRef.current.position.set(centerX, EYE_LEVEL, centerZ);
    
    // Disable orbit controls
    if (orbitControlsRef.current) {
      orbitControlsRef.current.enabled = false;
    }
    
    // Lock pointer
    pointerControlsRef.current.lock();
    setVoyagerMode(true);
  }, [graph.nodes, scaleFactor]);

  const handleExitVoyager = useCallback(() => {
    if (pointerControlsRef.current) {
      pointerControlsRef.current.unlock();
      setVoyagerMode(false);
    }
  }, []);

  useEffect(() => {
    if (!mountRef.current || !graph) return;

    const currentMount = mountRef.current;
    
    // Use dynamic scale factor from graph metadata
    const scale = scaleFactor;
    const wallHeight = DEFAULT_WALL_HEIGHT;

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf5f5f5);
    sceneRef.current = scene;

    // Calculate bounds
    const bounds = calculateBounds(graph.nodes);
    const planeCenterX = ((bounds.minX + bounds.maxX) / 2) * scale;
    const planeCenterZ = ((bounds.minY + bounds.maxY) / 2) * scale;
    const planeSizeX = (bounds.maxX - bounds.minX) * scale;
    const planeSizeZ = (bounds.maxY - bounds.minY) * scale;
    
    // Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(planeCenterX + 15, 18, planeCenterZ + 15);
    camera.lookAt(planeCenterX, 0, planeCenterZ);
    cameraRef.current = camera;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    currentMount.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 1.2);
    directionalLight.position.set(10, 20, 10);
    directionalLight.castShadow = true;
    directionalLight.shadow.mapSize.width = 2048;
    directionalLight.shadow.mapSize.height = 2048;
    directionalLight.shadow.camera.near = 0.5;
    directionalLight.shadow.camera.far = 100;
    directionalLight.shadow.camera.left = -30;
    directionalLight.shadow.camera.right = 30;
    directionalLight.shadow.camera.top = 30;
    directionalLight.shadow.camera.bottom = -30;
    scene.add(directionalLight);
    
    const hemisphereLight = new THREE.HemisphereLight(0xffffff, 0xcccccc, 0.4);
    scene.add(hemisphereLight);

    // OrbitControls (Third-person view)
    const orbitControls = new OrbitControls(camera, renderer.domElement);
    orbitControls.enableDamping = true;
    orbitControls.dampingFactor = 0.05;
    orbitControls.target.set(planeCenterX, wallHeight / 2, planeCenterZ);
    orbitControls.maxPolarAngle = Math.PI / 2;
    orbitControls.update();
    orbitControlsRef.current = orbitControls;

    // PointerLockControls (First-person Voyager mode)
    // Uses document.body for proper pointer lock functionality
    const pointerControls = new PointerLockControls(camera, document.body);
    pointerControlsRef.current = pointerControls;
    scene.add(pointerControls.getObject());

    pointerControls.addEventListener('unlock', () => {
      setVoyagerMode(false);
    });

    // Floor planes (Level 0 and Level 1)
    const floorPadding = 1.1;
    const floorGeometry = new THREE.PlaneGeometry(
      (planeSizeX || 20) * floorPadding, 
      (planeSizeZ || 20) * floorPadding
    );
    
    // Level 0 floor
    const floor0Material = new THREE.MeshStandardMaterial({ 
      color: 0xf8f7f4, 
      roughness: 1.0,
      metalness: 0.0
    });
    const floor0 = new THREE.Mesh(floorGeometry, floor0Material);
    floor0.rotation.x = -Math.PI / 2;
    floor0.position.set(planeCenterX, 0, planeCenterZ);
    floor0.receiveShadow = true;
    floor0.userData = { level: 0 };
    scene.add(floor0);

    // Level 1 floor (only if second floor exists)
    if (graph.has_second_floor) {
      const floor1Material = new THREE.MeshStandardMaterial({ 
        color: 0xf0eeeb, 
        roughness: 1.0,
        metalness: 0.0,
        transparent: true,
        opacity: 0.7
      });
      const floor1 = new THREE.Mesh(floorGeometry.clone(), floor1Material);
      floor1.rotation.x = -Math.PI / 2;
      floor1.position.set(planeCenterX, wallHeight, planeCenterZ);
      floor1.receiveShadow = true;
      floor1.userData = { level: 1 };
      scene.add(floor1);
    }

    // Wall materials with AEC-style edges
    const wallMaterial = new THREE.MeshStandardMaterial({ 
      color: 0xf0eeeb, 
      roughness: 0.85, 
      metalness: 0.0,
      polygonOffset: true,
      polygonOffsetFactor: 1,
      polygonOffsetUnits: 1
    });

    const transparentWallMaterial = new THREE.MeshStandardMaterial({ 
      color: 0xf0eeeb, 
      roughness: 0.85, 
      metalness: 0.0,
      transparent: true,
      opacity: 0.5,
      polygonOffset: true,
      polygonOffsetFactor: 1,
      polygonOffsetUnits: 1
    });

    const wallMeshes: THREE.Mesh[] = [];

    // Create Level 0 walls
    graph.edges.forEach((wall: WallEdge) => {
      if (!showInteriorWalls && wall.kind === 'interior') return;
      
      const startNode = graph.nodes[wall.a];
      const endNode = graph.nodes[wall.b];
      
      // Get dynamic wall thickness from edge data
      const wallThickness = wall.thickness_m || 
        (wall.thickness_category === 'major' ? DEFAULT_WALL_THICKNESS_MAJOR : DEFAULT_WALL_THICKNESS_MINOR);
      
      if (startNode && endNode) {
        const wallGroup = createAECWall(
          startNode.x * scale, 
          startNode.y * scale, 
          endNode.x * scale, 
          endNode.y * scale,
          wallMaterial,
          wall.kind,
          0, // Level 0
          wallHeight,
          wallThickness
        );
        wallGroup.userData = { level: 0, kind: wall.kind };
        scene.add(wallGroup);
        
        // Store mesh for collision detection
        wallGroup.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            wallMeshes.push(child);
          }
        });
      }
    });

    // Create Level 1 walls (semi-transparent shell) if second floor exists
    if (graph.has_second_floor) {
      graph.edges.forEach((wall: WallEdge) => {
        // Only exterior walls for second floor shell
        if (wall.kind !== 'exterior') return;
        
        const startNode = graph.nodes[wall.a];
        const endNode = graph.nodes[wall.b];
        
        // Get dynamic wall thickness from edge data
        const wallThickness = wall.thickness_m || 
          (wall.thickness_category === 'major' ? DEFAULT_WALL_THICKNESS_MAJOR : DEFAULT_WALL_THICKNESS_MINOR);
        
        if (startNode && endNode) {
          const wallGroup = createAECWall(
            startNode.x * scale, 
            startNode.y * scale, 
            endNode.x * scale, 
            endNode.y * scale,
            transparentWallMaterial,
            wall.kind,
            1, // Level 1
            wallHeight,
            wallThickness
          );
          wallGroup.userData = { level: 1, kind: wall.kind };
          scene.add(wallGroup);
        }
      });
    }

    wallMeshesRef.current = wallMeshes;

    // Generate staircase if detected
    let staircaseGroup: THREE.Group | null = null;
    if (graph.staircase?.detected || graph.has_second_floor) {
      const staircaseData = graph.staircase || createDefaultStaircase(graph, bounds);
      staircaseGroup = createStaircase(staircaseData, scale);
      scene.add(staircaseGroup);
      
      // Store staircase bounds for collision/climbing
      const box = new THREE.Box3().setFromObject(staircaseGroup);
      staircaseBoundsRef.current = box;
    }

    // Keyboard event handlers for Voyager mode
    const onKeyDown = (event: KeyboardEvent) => {
      switch (event.code) {
        case 'KeyW':
        case 'ArrowUp':
          moveStateRef.current.forward = true;
          break;
        case 'KeyS':
        case 'ArrowDown':
          moveStateRef.current.backward = true;
          break;
        case 'KeyA':
        case 'ArrowLeft':
          moveStateRef.current.left = true;
          break;
        case 'KeyD':
        case 'ArrowRight':
          moveStateRef.current.right = true;
          break;
        case 'Escape':
          if (pointerControlsRef.current?.isLocked) {
            pointerControlsRef.current.unlock();
          }
          break;
      }
    };

    const onKeyUp = (event: KeyboardEvent) => {
      switch (event.code) {
        case 'KeyW':
        case 'ArrowUp':
          moveStateRef.current.forward = false;
          break;
        case 'KeyS':
        case 'ArrowDown':
          moveStateRef.current.backward = false;
          break;
        case 'KeyA':
        case 'ArrowLeft':
          moveStateRef.current.left = false;
          break;
        case 'KeyD':
        case 'ArrowRight':
          moveStateRef.current.right = false;
          break;
      }
    };

    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('keyup', onKeyUp);

    // Animation loop
    let prevTime = performance.now();
    
    const animate = () => {
      requestAnimationFrame(animate);
      
      const time = performance.now();
      const delta = (time - prevTime) / 1000;
      prevTime = time;

      // Voyager mode movement
      if (pointerControlsRef.current?.isLocked) {
        velocityRef.current.x -= velocityRef.current.x * 10.0 * delta;
        velocityRef.current.z -= velocityRef.current.z * 10.0 * delta;

        directionRef.current.z = Number(moveStateRef.current.forward) - Number(moveStateRef.current.backward);
        directionRef.current.x = Number(moveStateRef.current.right) - Number(moveStateRef.current.left);
        directionRef.current.normalize();

        if (moveStateRef.current.forward || moveStateRef.current.backward) {
          velocityRef.current.z -= directionRef.current.z * MOVE_SPEED * delta * 50;
        }
        if (moveStateRef.current.left || moveStateRef.current.right) {
          velocityRef.current.x -= directionRef.current.x * MOVE_SPEED * delta * 50;
        }

        // Calculate new position
        const newPos = camera.position.clone();
        pointerControlsRef.current.moveRight(-velocityRef.current.x * delta);
        pointerControlsRef.current.moveForward(-velocityRef.current.z * delta);

        // Simple collision detection
        const playerRadius = 0.3;
        const playerBox = new THREE.Box3().setFromCenterAndSize(
          camera.position,
          new THREE.Vector3(playerRadius * 2, 1.8, playerRadius * 2)
        );

        let collision = false;
        for (const wallMesh of wallMeshesRef.current) {
          const wallBox = new THREE.Box3().setFromObject(wallMesh);
          if (playerBox.intersectsBox(wallBox)) {
            collision = true;
            break;
          }
        }

        if (collision) {
          camera.position.copy(newPos);
        }

        // Check staircase climbing
        if (staircaseBoundsRef.current) {
          const playerPoint = new THREE.Vector3(camera.position.x, 0, camera.position.z);
          const stairBox2D = new THREE.Box3(
            new THREE.Vector3(staircaseBoundsRef.current.min.x, 0, staircaseBoundsRef.current.min.z),
            new THREE.Vector3(staircaseBoundsRef.current.max.x, 0, staircaseBoundsRef.current.max.z)
          );
          
          if (stairBox2D.containsPoint(playerPoint)) {
            // Calculate height based on position in staircase
            const progress = (camera.position.z - staircaseBoundsRef.current.min.z) / 
                           (staircaseBoundsRef.current.max.z - staircaseBoundsRef.current.min.z);
            const targetY = EYE_LEVEL + progress * DEFAULT_WALL_HEIGHT;
            camera.position.y = THREE.MathUtils.lerp(camera.position.y, targetY, 0.1);
            setCurrentFloor(progress > 0.5 ? 1 : 0);
          } else {
            // Reset to current floor level
            const targetY = EYE_LEVEL + currentFloor * DEFAULT_WALL_HEIGHT;
            camera.position.y = THREE.MathUtils.lerp(camera.position.y, targetY, 0.1);
          }
        }
      } else {
        orbitControls.update();
      }

      // Update visibility based on view level
      scene.traverse((object) => {
        if (object.userData.level !== undefined) {
          switch (viewLevel) {
            case 'level0':
              object.visible = object.userData.level === 0;
              break;
            case 'level1':
              object.visible = object.userData.level === 1 || object.userData.isStaircase;
              break;
            case 'all':
            default:
              object.visible = true;
              break;
          }
        }
      });

      renderer.render(scene, camera);
    };
    animate();

    // Cleanup
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('keyup', onKeyUp);
      
      if (currentMount && renderer.domElement) {
        currentMount.removeChild(renderer.domElement);
      }
      orbitControls.dispose();
      if (pointerControlsRef.current) {
        pointerControlsRef.current.dispose();
      }
      renderer.dispose();
    };
  }, [graph, width, height, showInteriorWalls, viewLevel, currentFloor, scaleFactor]);

  return (
    <div className="relative">
      {/* Control Panel */}
      <div className="absolute top-4 right-4 z-10 bg-white rounded-xl shadow-lg p-4 border border-gray-200 space-y-4 min-w-[200px]">
        {/* Scale Info */}
        <div className="border-b border-gray-100 pb-3">
          <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Scale Info</label>
          <div className="text-xs text-gray-600 space-y-1">
            <div className="flex justify-between">
              <span>Method:</span>
              <span className={`font-medium ${
                scalingInfo.method === 'ocr' ? 'text-green-600' : 
                scalingInfo.method === 'heuristic' ? 'text-yellow-600' : 'text-gray-500'
              }`}>
                {scalingInfo.method.toUpperCase()}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Scale:</span>
              <span className="font-mono">{(scaleFactor * 100).toFixed(2)} cm/px</span>
            </div>
            {scalingInfo.confidence > 0 && (
              <div className="flex justify-between">
                <span>Confidence:</span>
                <span>{(scalingInfo.confidence * 100).toFixed(0)}%</span>
              </div>
            )}
          </div>
        </div>

        {/* Level Selector */}
        <div>
          <label className="block text-xs font-semibold text-gray-500 uppercase mb-2">Floor Level</label>
          <div className="flex rounded-lg overflow-hidden border border-gray-200">
            {(['level0', 'level1', 'all'] as ViewLevel[]).map((level) => (
              <button
                key={level}
                onClick={() => setViewLevel(level)}
                className={`flex-1 px-3 py-1.5 text-xs font-medium transition-colors ${
                  viewLevel === level 
                    ? 'bg-cyan-500 text-white' 
                    : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
                }`}
              >
                {level === 'level0' ? 'L0' : level === 'level1' ? 'L1' : 'All'}
              </button>
            ))}
          </div>
        </div>

        {/* Interior Walls Toggle */}
        <label className="flex items-center space-x-2 text-sm text-gray-700 cursor-pointer">
          <input 
            type="checkbox" 
            checked={showInteriorWalls}
            onChange={(e) => setShowInteriorWalls(e.target.checked)}
            className="w-4 h-4 text-cyan-600 rounded"
          />
          <span className="font-mono text-xs">Interior Walls</span>
        </label>

        {/* Voyager Mode Button */}
        <button
          onClick={voyagerMode ? handleExitVoyager : handleEnterVoyager}
          className={`w-full px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            voyagerMode 
              ? 'bg-red-500 text-white hover:bg-red-600' 
              : 'bg-gradient-to-r from-cyan-500 to-blue-500 text-white hover:from-cyan-600 hover:to-blue-600'
          }`}
        >
          {voyagerMode ? '🚪 Exit Voyager' : '🚀 Enter Voyager'}
        </button>

        {voyagerMode && (
          <div className="text-xs text-gray-500 bg-gray-50 rounded-lg p-2">
            <div className="font-semibold mb-1">Controls:</div>
            <div>WASD - Move</div>
            <div>Mouse - Look</div>
            <div>ESC - Exit</div>
          </div>
        )}
      </div>

      {/* Stats Panel */}
      <div className="absolute bottom-4 left-4 z-10 bg-white/95 text-gray-700 font-mono text-xs px-4 py-3 rounded-lg shadow border border-gray-200">
        <div className="flex items-center gap-4">
          <div>
            <span className="font-bold text-cyan-600">{graph.edges.length}</span>
            <span className="text-gray-500 ml-1">walls</span>
          </div>
          <div className="w-px h-4 bg-gray-300" />
          <div>
            <span className="font-bold text-cyan-600">{graph.nodes.length}</span>
            <span className="text-gray-500 ml-1">vertices</span>
          </div>
          {graph.has_second_floor && (
            <>
              <div className="w-px h-4 bg-gray-300" />
              <div className="text-green-600 font-semibold">2 Floors</div>
            </>
          )}
        </div>
        
        {/* Cost Wallet */}
        {totalCost > 0 && (
          <div className="mt-2 pt-2 border-t border-gray-200">
            <div className="text-gray-500">Est. Cost</div>
            <div className="text-lg font-bold text-emerald-600">
              ₹{totalCost.toLocaleString('en-IN')}
            </div>
          </div>
        )}

        {voyagerMode && (
          <div className="mt-2 pt-2 border-t border-gray-200">
            <span className="text-orange-500 font-semibold">Floor {currentFloor}</span>
          </div>
        )}
      </div>

      <div 
        ref={mountRef} 
        className="rounded-xl overflow-hidden shadow-sm border border-gray-200" 
        style={{ cursor: voyagerMode ? 'none' : 'move' }} 
      />
    </div>
  );
};

function calculateBounds(nodes: Point2D[]) {
  if (nodes.length === 0) {
    return { minX: 0, maxX: 2000, minY: 0, maxY: 2000 };
  }
  
  const xs = nodes.map(n => n.x);
  const ys = nodes.map(n => n.y);
  
  return {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys)
  };
}

// Create AEC-style wall with solid mesh + wireframe edges
function createAECWall(
  x1: number, 
  y1: number, 
  x2: number, 
  y2: number, 
  material: THREE.MeshStandardMaterial,
  kind: 'exterior' | 'interior',
  level: number,
  wallHeight: number = DEFAULT_WALL_HEIGHT,
  wallThickness: number = DEFAULT_WALL_THICKNESS_MINOR
): THREE.Group {
  const length = Math.hypot(x2 - x1, y2 - y1);
  const group = new THREE.Group();
  
  // Solid wall geometry - use dynamic thickness
  const geometry = new THREE.BoxGeometry(length, wallHeight, wallThickness);
  geometry.computeVertexNormals();
  
  const mesh = new THREE.Mesh(geometry, material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  group.add(mesh);
  
  // AEC-style wireframe edges (dashed line look)
  const edgesGeometry = new THREE.EdgesGeometry(geometry);
  const edgeColor = kind === 'exterior' ? 0x0284c7 : 0x64748b;
  const edgeMaterial = new THREE.LineBasicMaterial({ 
    color: edgeColor,
    linewidth: 1
  });
  const wireframe = new THREE.LineSegments(edgesGeometry, edgeMaterial);
  group.add(wireframe);
  
  // Position at midpoint, elevated for level
  const yOffset = level * wallHeight;
  group.position.set(
    (x1 + x2) / 2,
    wallHeight / 2 + yOffset,
    (y1 + y2) / 2
  );
  
  // Rotate to align with wall direction
  group.rotation.y = -Math.atan2(y2 - y1, x2 - x1);
  
  return group;
}

// Create default staircase data when not detected but second floor exists
function createDefaultStaircase(graph: GraphPayload, bounds: ReturnType<typeof calculateBounds>): StaircaseData {
  // If void_coordinates exist, use them as staircase center
  const center = graph.void_coordinates 
    ? { x: graph.void_coordinates[0], y: graph.void_coordinates[1] }
    : { x: (bounds.minX + bounds.maxX) / 2, y: bounds.maxY - 200 }; // Default to center-back
  
  return {
    detected: true,
    type: 'straight',
    bounding_box: {
      x: center.x - 100,
      y: center.y - 150,
      width: 200,
      height: 300
    },
    center,
    direction: 'up',
    num_steps: Math.ceil(DEFAULT_WALL_HEIGHT / DEFAULT_STAIR_STEP_HEIGHT)
  };
}

// Generate 3D staircase geometry
function createStaircase(data: StaircaseData, scaleFactor: number, wallHeight: number = DEFAULT_WALL_HEIGHT): THREE.Group {
  const group = new THREE.Group();
  group.userData = { isStaircase: true, level: 'both' };
  
  const stepWidth = (data.bounding_box.width * scaleFactor);
  const stepDepth = (data.bounding_box.height * scaleFactor) / data.num_steps;
  const stepHeight = wallHeight / data.num_steps;
  
  const stepMaterial = new THREE.MeshStandardMaterial({
    color: 0xe0ddd9,
    roughness: 0.7,
    metalness: 0.1
  });

  // Create steps
  for (let i = 0; i < data.num_steps; i++) {
    const stepGeometry = new THREE.BoxGeometry(stepWidth, stepHeight, stepDepth);
    stepGeometry.computeVertexNormals();
    
    const step = new THREE.Mesh(stepGeometry, stepMaterial);
    step.position.set(
      0,
      stepHeight / 2 + (i * stepHeight),
      stepDepth / 2 + (i * stepDepth)
    );
    step.castShadow = true;
    step.receiveShadow = true;
    group.add(step);
    
    // Add edge wireframe
    const edgesGeo = new THREE.EdgesGeometry(stepGeometry);
    const edgeMat = new THREE.LineBasicMaterial({ color: 0x888888 });
    const edges = new THREE.LineSegments(edgesGeo, edgeMat);
    edges.position.copy(step.position);
    group.add(edges);
  }

  // Side rails
  const railMaterial = new THREE.MeshStandardMaterial({
    color: 0x8b7355,
    roughness: 0.6,
    metalness: 0.2
  });
  
  const railHeight = 0.9;
  const railWidth = 0.05;
  const totalLength = Math.sqrt(
    Math.pow(data.bounding_box.height * scaleFactor, 2) + 
    Math.pow(wallHeight, 2)
  );
  
  const railGeometry = new THREE.BoxGeometry(railWidth, railHeight, totalLength);
  
  // Left rail
  const leftRail = new THREE.Mesh(railGeometry, railMaterial);
  leftRail.position.set(-stepWidth / 2, wallHeight / 2 + railHeight / 2, (data.bounding_box.height * scaleFactor) / 2);
  leftRail.rotation.x = Math.atan2(wallHeight, data.bounding_box.height * scaleFactor);
  leftRail.castShadow = true;
  group.add(leftRail);
  
  // Right rail
  const rightRail = new THREE.Mesh(railGeometry, railMaterial);
  rightRail.position.set(stepWidth / 2, wallHeight / 2 + railHeight / 2, (data.bounding_box.height * scaleFactor) / 2);
  rightRail.rotation.x = Math.atan2(wallHeight, data.bounding_box.height * scaleFactor);
  rightRail.castShadow = true;
  group.add(rightRail);

  // Position the entire staircase
  group.position.set(
    data.center.x * scaleFactor,
    0,
    data.center.y * scaleFactor
  );

  return group;
}

export default ThreeViewer;
