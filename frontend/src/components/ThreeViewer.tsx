import React, { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import { GraphPayload, WallEdge, Point2D } from '../types';

interface ThreeViewerProps {
  graph: GraphPayload;
  width?: number;
  height?: number;
}

const ThreeViewer: React.FC<ThreeViewerProps> = ({ 
  graph, 
  width = 800, 
  height = 600 
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const frameRef = useRef<number | null>(null);
  const [fpMode, setFpMode] = useState(false);

  useEffect(() => {
    if (!mountRef.current || !graph) return;

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf5f5f5);
    sceneRef.current = scene;

    // Camera setup
    const camera = new THREE.PerspectiveCamera(
      75,
      width / height,
      0.1,
      100000
    );
    
    // Calculate bounds to center camera
    const bounds = calculateBounds(graph.nodes);
    const centerX = (bounds.minX + bounds.maxX) / 2;
    const centerY = (bounds.minY + bounds.maxY) / 2;
    const maxDim = Math.max(bounds.maxX - bounds.minX, bounds.maxY - bounds.minY);
    
    camera.position.set(centerX, centerY, maxDim * 2);
    camera.lookAt(centerX, centerY, 0);

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    rendererRef.current = renderer;
    mountRef.current.appendChild(renderer.domElement);

    // Lighting (Brightened for sketch look)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5);
    directionalLight.position.set(centerX + 100, centerY - 100, 200);
    directionalLight.castShadow = true;
    scene.add(directionalLight);

    // OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.target.set(centerX, centerY, 0);

    // Playable Character Avatar
    const charGeo = new THREE.CapsuleGeometry(12, 24, 4, 8);
    charGeo.rotateX(Math.PI / 2); // Stand upright along Z-axis
    const charMat = new THREE.MeshLambertMaterial({ color: 0x00bcd4 }); // Cyan character
    const character = new THREE.Mesh(charGeo, charMat);
    character.position.set(centerX, centerY, 30);
    character.castShadow = true;
    scene.add(character);

    // Keyboard state for Pilot Mode
    const keys = { w: false, a: false, s: false, d: false };
    const handleKeyDown = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();
      if (typeof (keys as any)[key] !== 'undefined') (keys as any)[key] = true;
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();
      if (typeof (keys as any)[key] !== 'undefined') (keys as any)[key] = false;
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    // Create floor plane
    if (graph.rooms.length > 0) {
      graph.rooms.forEach(room => {
        const floorGeometry = createFloorGeometry(room.polygon);
        if (floorGeometry) {
          const floorMaterial = new THREE.MeshLambertMaterial({ 
            color: 0xe8e8e8,
            side: THREE.DoubleSide 
          });
          const floorMesh = new THREE.Mesh(floorGeometry, floorMaterial);
          floorMesh.position.z = 0;
          floorMesh.receiveShadow = true;
          scene.add(floorMesh);
        }
      });
    } else {
      // Fallback floor
      const floorGeometry = new THREE.PlaneGeometry(maxDim, maxDim);
      const floorMaterial = new THREE.MeshLambertMaterial({ color: 0xe8e8e8 });
      const floorMesh = new THREE.Mesh(floorGeometry, floorMaterial);
      floorMesh.position.set(centerX, centerY, 0);
      floorMesh.receiveShadow = true;
      scene.add(floorMesh);
    }

    // Create walls
    graph.edges.forEach((wall: WallEdge) => {
      const startNode = graph.nodes[wall.a];
      const endNode = graph.nodes[wall.b];
      
      if (startNode && endNode) {
        const wallMesh = createWallMesh(startNode, endNode, wall.kind, false);
        wallMesh.castShadow = true;
        wallMesh.receiveShadow = true;
        scene.add(wallMesh);

        // Extrude inferred 2nd level for exterior walls
        if ((graph as any).has_second_floor && wall.kind === 'exterior') {
          const upperWallMesh = createWallMesh(startNode, endNode, wall.kind, true);
          upperWallMesh.position.z += 100;
          scene.add(upperWallMesh);
        }
      }
    });

    if ((graph as any).has_second_floor) {
      // 3D Sprite Label
      const canvas = document.createElement('canvas');
      canvas.width = 512;
      canvas.height = 128;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.fillStyle = 'rgba(15, 23, 42, 0.8)';
        ctx.fillRect(0, 0, 512, 128);
        ctx.font = 'bold 44px monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#22d3ee';
        ctx.fillText('INFERRED 2ND LEVEL', 256, 64);
      }
      const tex = new THREE.CanvasTexture(canvas);
      const spriteMat = new THREE.SpriteMaterial({ map: tex, transparent: true });
      const sprite = new THREE.Sprite(spriteMat);
      sprite.scale.set(300, 75, 1);
      sprite.position.set(centerX, centerY, 220); // Hover above
      scene.add(sprite);
    }

    // Animation loop
    const animate = () => {
      frameRef.current = requestAnimationFrame(animate);
      
      // Character movement (W goes up the screen which is -Y)
      const speed = 4.0;
      if (keys.w) character.position.y -= speed;
      if (keys.s) character.position.y += speed;
      if (keys.a) character.position.x -= speed;
      if (keys.d) character.position.x += speed;

      if (fpMode) {
        controls.enabled = false;
        // First Person: Camera sits inside the avatar's head and looks forward along -Y
        camera.position.set(character.position.x, character.position.y + 10, character.position.z + 15);
        camera.lookAt(character.position.x, character.position.y - 100, character.position.z + 15);
      } else {
        // Third Person Orbit
        controls.enabled = true;
        controls.target.copy(character.position);
        controls.update();
      }

      renderer.render(scene, camera);
    };

    animate();

    // Cleanup
    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      if (mountRef.current && renderer.domElement) {
        mountRef.current.removeChild(renderer.domElement);
      }
      controls.dispose();
      renderer.dispose();
    };
  }, [graph, width, height, fpMode]);

  return (
    <div className="relative">
      <button 
        onClick={() => setFpMode(!fpMode)}
        className="absolute bottom-4 left-4 z-10 px-4 py-2 bg-gray-900/80 text-cyan-400 font-mono text-xs rounded-full border border-cyan-800 hover:bg-cyan-900/50 hover:text-cyan-100 transition-colors shadow-lg backdrop-blur-md"
      >
        {fpMode ? "⏏ Exit FP Mode" : "👁 Enter First-Person (WASD)"}
      </button>
      <div ref={mountRef} className="canvas-container rounded-lg overflow-hidden shadow-[0_0_15px_rgba(0,0,0,0.5)] border border-cyan-900/30" />
    </div>
  );
};

function calculateBounds(nodes: Point2D[]) {
  if (nodes.length === 0) {
    return { minX: 0, maxX: 100, minY: 0, maxY: 100 };
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

function createFloorGeometry(polygon: Point2D[]): THREE.BufferGeometry | null {
  if (polygon.length < 3) return null;
  
  const shape = new THREE.Shape();
  shape.moveTo(polygon[0].x, polygon[0].y);
  
  for (let i = 1; i < polygon.length; i++) {
    shape.lineTo(polygon[i].x, polygon[i].y);
  }
  
  const geometry = new THREE.ShapeGeometry(shape);
  return geometry;
}

function createWallMesh(start: Point2D, end: Point2D, kind: 'exterior' | 'interior', isUpperFloor: boolean = false): THREE.Mesh {
  const length = Math.sqrt(Math.pow(end.x - start.x, 2) + Math.pow(end.y - start.y, 2));
  const wallHeight = 100;
  const wallThickness = kind === 'exterior' ? 8 : 4;
  
  const geometry = new THREE.BoxGeometry(length, wallThickness, wallHeight);
  
  let color = kind === 'exterior' ? 0x8b4513 : 0xd3d3d3; // Brown for exterior, gray for interior
  if (isUpperFloor) color = 0x64748b; // Slate shell color
  
  const material = new THREE.MeshLambertMaterial({ 
    color, 
    transparent: isUpperFloor, 
    opacity: isUpperFloor ? 0.5 : 1.0 
  });
  
  const mesh = new THREE.Mesh(geometry, material);
  
  // Aesthetic: Add clear solid black edges over walls
  const edges = new THREE.EdgesGeometry(geometry);
  const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ 
    color: isUpperFloor ? 0x334155 : 0x000000, 
    linewidth: 2,
    transparent: isUpperFloor,
    opacity: isUpperFloor ? 0.3 : 1.0
  }));
  mesh.add(line);
  
  // Position and rotate wall
  const centerX = (start.x + end.x) / 2;
  const centerY = (start.y + end.y) / 2;
  const angle = Math.atan2(end.y - start.y, end.x - start.x);
  
  mesh.position.set(centerX, centerY, wallHeight / 2);
  mesh.rotation.z = angle;
  
  return mesh;
}

export default ThreeViewer;
