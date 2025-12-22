import { useEffect, useRef, useState } from 'react';
import './Integrated3DViewer.css';

interface Integrated3DViewerProps {
  projectId: string;
}

const Integrated3DViewer = ({ projectId }: Integrated3DViewerProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (iframeRef.current) {
      const iframe = iframeRef.current;
      
      const handleLoad = () => {
        setLoading(false);
      };

      iframe.addEventListener('load', handleLoad);
      
      return () => {
        iframe.removeEventListener('load', handleLoad);
      };
    }
  }, []);

  const iframeContent = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FloorspaceJS 3D Viewer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            overflow: hidden;
            background: #1a1a1a;
            color: #fff;
            height: 100vh;
        }
        #container {
            display: flex;
            height: 100vh;
        }
        #sidebar {
            width: 380px;
            background: linear-gradient(180deg, #2d2d2d 0%, #252525 100%);
            overflow-y: auto;
            padding: 25px;
            box-shadow: 4px 0 20px rgba(0,0,0,0.5);
            border-right: 1px solid #3a3a3a;
        }
        #sidebar::-webkit-scrollbar {
            width: 8px;
        }
        #sidebar::-webkit-scrollbar-track {
            background: #1a1a1a;
        }
        #sidebar::-webkit-scrollbar-thumb {
            background: #4CAF50;
            border-radius: 4px;
        }
        #sidebar::-webkit-scrollbar-thumb:hover {
            background: #45a049;
        }
        #viewer {
            flex: 1;
            position: relative;
        }
        h1 {
            font-size: 24px;
            margin-bottom: 25px;
            color: #4CAF50;
            font-weight: 600;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
            padding-bottom: 15px;
            border-bottom: 2px solid #4CAF50;
        }
        h2 {
            font-size: 15px;
            margin: 20px 0 12px 0;
            color: #64B5F6;
            border-bottom: 2px solid #444;
            padding-bottom: 8px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .section {
            margin-bottom: 25px;
            background: rgba(255,255,255,0.02);
            padding: 15px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.05);
        }
        .property {
            margin: 10px 0;
            font-size: 13px;
            padding: 6px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .property:last-child {
            border-bottom: none;
        }
        .property-label {
            color: #999;
            display: inline-block;
            min-width: 130px;
            font-weight: 500;
        }
        .property-value {
            color: #e0e0e0;
            font-weight: 600;
        }
        button, input[type="file"] {
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            color: white;
            border: none;
            padding: 8px 12px;
            margin: 6px 0;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            width: 100%;
            transition: all 0.3s ease;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }
        button:hover {
            background: linear-gradient(135deg, #45a049 0%, #3d8b40 100%);
            transform: translateY(-1px);
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        }
        input[type="text"] {
            width: 100%;
            padding: 12px 15px;
            margin: 10px 0;
            border: 2px solid #444;
            border-radius: 6px;
            background: #333;
            color: #fff;
            font-size: 13px;
            transition: all 0.3s ease;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #4CAF50;
            background: #3a3a3a;
            box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.1);
        }
        .color-indicator {
            display: inline-block;
            width: 20px;
            height: 20px;
            border-radius: 3px;
            vertical-align: middle;
            margin-right: 8px;
            border: 1px solid #555;
        }
        .collapsible {
            background: linear-gradient(135deg, #3a3a3a 0%, #333 100%);
            color: #fff;
            cursor: pointer;
            padding: 12px 15px;
            width: 100%;
            border: none;
            text-align: left;
            outline: none;
            font-size: 14px;
            font-weight: 600;
            border-radius: 6px;
            margin: 8px 0;
            transition: all 0.3s ease;
            border: 1px solid rgba(255,255,255,0.1);
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .collapsible:hover {
            background: linear-gradient(135deg, #4a4a4a 0%, #3d3d3d 100%);
            transform: translateX(2px);
            box-shadow: 0 3px 6px rgba(0,0,0,0.3);
        }
        .collapsible.active {
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            box-shadow: 0 4px 8px rgba(76, 175, 80, 0.3);
        }
        .collapsible::before {
            content: '▶ ';
            display: inline-block;
            margin-right: 8px;
            transition: transform 0.3s;
        }
        .collapsible.active::before {
            transform: rotate(90deg);
        }
        .collapsible-content {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
            background: #2a2a2a;
            padding: 0 10px;
        }
        .collapsible-content.active {
            max-height: 2000px;
            padding: 10px;
        }
        .nested-collapsible {
            background: #333;
            font-size: 13px;
            margin-left: 10px;
        }
        .nested-collapsible-content {
            background: #2a2a2a;
            margin-left: 10px;
        }
        .component-item {
            background: linear-gradient(135deg, #3a3a3a 0%, #333 100%);
            padding: 10px 12px;
            margin: 8px 0;
            border-radius: 6px;
            font-size: 12px;
            border-left: 3px solid #64B5F6;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            transition: all 0.2s;
        }
        .component-item:hover {
            transform: translateX(2px);
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            border-left-color: #4CAF50;
        }
        #controls {
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(42, 42, 42, 0.9);
            padding: 10px;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.4);
            min-width: 140px;
        }
        #loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 18px;
            color: #4CAF50;
        }
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div id="container">
        <div id="sidebar">
            <h1>🏢 FloorspaceJS Viewer</h1>
            
            <div class="section">
                <input type="text" id="urlInput" placeholder="Enter presigned URL or leave empty for file upload">
                <button onclick="loadFromURL()">Load from URL</button>
                <input type="file" id="fileInput" accept=".json" onchange="loadFromFile(event)">
            </div>

            <div id="buildingInfo">
                <div class="section">
                    <h2>Sample Building</h2>
                    <div class="property">
                        <span class="property-label">Project ID:</span>
                        <span class="property-value">${projectId}</span>
                    </div>
                    <div class="property">
                        <span class="property-label">Status:</span>
                        <span class="property-value">Ready to load</span>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="viewer">
            <div id="loading" class="hidden">Loading...</div>
            <div id="controls">
                <button onclick="resetCamera()">Reset View</button>
                <button onclick="toggleAxes()">Toggle Axes</button>
                <button onclick="loadSampleBuilding()">Load Sample</button>
                <div style="font-size: 10px; color: #aaa; margin-top: 8px; line-height: 1.3;">
                    <strong>Controls:</strong><br>
                    • Left-click + drag: Rotate<br>
                    • Right-click + drag: Pan<br>
                    • Scroll: Zoom
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <script src="https://cdn.rawgit.com/sshirokov/ThreeBSP/master/ThreeBSP.js"></script>
    
    <script>
        let scene, camera, renderer, controls;
        let buildingGroup;
        let axesHelper;

        function init3DViewer() {
            const viewerElement = document.getElementById('viewer');
            
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x1a1a1a);
            
            camera = new THREE.PerspectiveCamera(
                60,
                viewerElement.clientWidth / viewerElement.clientHeight,
                0.1,
                10000
            );
            camera.position.set(100, 100, 100);
            
            renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(viewerElement.clientWidth, viewerElement.clientHeight);
            renderer.shadowMap.enabled = false;
            viewerElement.appendChild(renderer.domElement);
            
            controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;
            controls.enablePan = true;
            controls.panSpeed = 1.0;
            controls.screenSpacePanning = true;
            
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
            scene.add(ambientLight);
            
            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.6);
            directionalLight.position.set(50, 100, 50);
            directionalLight.castShadow = false;
            scene.add(directionalLight);
            
            axesHelper = new THREE.AxesHelper(50);
            scene.add(axesHelper);
            
            const gridHelper = new THREE.GridHelper(200, 40, 0x444444, 0x222222);
            scene.add(gridHelper);
            
            buildingGroup = new THREE.Group();
            scene.add(buildingGroup);
            
            window.addEventListener('resize', onWindowResize);
            animate();
            
            // Start with empty scene - comment out the line below to start empty
            // loadSampleBuilding();
        }

        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }

        function onWindowResize() {
            const viewerElement = document.getElementById('viewer');
            camera.aspect = viewerElement.clientWidth / viewerElement.clientHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(viewerElement.clientWidth, viewerElement.clientHeight);
        }

        function loadSampleBuilding() {
            const sampleData = {
                "project": {
                    "config": {
                        "units": "ft",
                        "language": "EN-US"
                    },
                    "grid": {
                        "spacing": 10
                    }
                },
                "stories": [
                    {
                        "name": "Ground Floor",
                        "floor_to_ceiling_height": 10,
                        "multiplier": 1,
                        "color": "#88ccee",
                        "spaces": [
                            {
                                "name": "Living Room",
                                "type": "living",
                                "color": "#88ccee",
                                "face_id": "face-1"
                            },
                            {
                                "name": "Kitchen", 
                                "type": "kitchen",
                                "color": "#ffaabb",
                                "face_id": "face-2"
                            },
                            {
                                "name": "Bedroom",
                                "type": "bedroom", 
                                "color": "#aaffcc",
                                "face_id": "face-3"
                            }
                        ],
                        "geometry": {
                            "vertices": [
                                {"id": "v1", "x": 0, "y": 0},
                                {"id": "v2", "x": 30, "y": 0},
                                {"id": "v3", "x": 30, "y": 20},
                                {"id": "v4", "x": 0, "y": 20},
                                {"id": "v5", "x": 15, "y": 20},
                                {"id": "v6", "x": 15, "y": 10}
                            ],
                            "edges": [
                                {"id": "e1", "vertex_ids": ["v1", "v2"]},
                                {"id": "e2", "vertex_ids": ["v2", "v3"]},
                                {"id": "e3", "vertex_ids": ["v3", "v5"]},
                                {"id": "e4", "vertex_ids": ["v5", "v4"]},
                                {"id": "e5", "vertex_ids": ["v4", "v1"]},
                                {"id": "e6", "vertex_ids": ["v5", "v6"]},
                                {"id": "e7", "vertex_ids": ["v6", "v2"]}
                            ],
                            "faces": [
                                {
                                    "id": "face-1",
                                    "edge_ids": ["e1", "e7", "e6", "e4", "e5"],
                                    "edge_order": [1, -1, -1, 1, 1]
                                },
                                {
                                    "id": "face-2", 
                                    "edge_ids": ["e7", "e2", "e3", "e6"],
                                    "edge_order": [1, 1, 1, 1]
                                }
                            ]
                        },
                        "windows": [],
                        "doors": [],
                        "shading": []
                    }
                ],
                "window_definitions": [],
                "door_definitions": []
            };
            
            createBuilding(sampleData);
            displayBuildingInfo(sampleData);
        }

        function createBuilding(data) {
            buildingGroup.clear();
            
            data.stories.forEach((story, storyIndex) => {
                const storyHeight = story.floor_to_ceiling_height || 8;
                const zOffset = storyIndex * storyHeight;
                
                story.spaces.forEach(space => {
                    const face = story.geometry.faces.find(f => f.id === space.face_id);
                    if (!face) return;
                    
                    const vertices = getVerticesForFace(face, story.geometry);
                    if (vertices.length < 3) return;
                    
                    const shape = new THREE.Shape();
                    shape.moveTo(vertices[0].x, vertices[0].z);
                    for (let i = 1; i < vertices.length; i++) {
                        shape.lineTo(vertices[i].x, vertices[i].z);
                    }
                    
                    const extrudeSettings = {
                        depth: storyHeight,
                        bevelEnabled: false
                    };
                    
                    const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);
                    geometry.rotateX(-Math.PI / 2);
                    geometry.translate(0, 0, 0);
                    
                    const color = new THREE.Color(space.color || '#88ccee');
                    const material = new THREE.MeshPhongMaterial({
                        color: color,
                        transparent: false,
                        opacity: 1.0,
                        side: THREE.DoubleSide
                    });
                    
                    let finalMesh = new THREE.Mesh(geometry, material);
                    finalMesh.position.y = zOffset;
                    
                    // Subtract window volumes from walls using CSG
                    if (typeof ThreeBSP !== 'undefined') {
                        console.log('ThreeBSP is available, cutting window holes...');
                        let wallBSP = new ThreeBSP(finalMesh);
                        let holesCount = 0;
                        
                        // Find all windows for edges of this face
                        face.edge_ids.forEach(edgeId => {
                            const windowsOnEdge = story.windows.filter(w => w.edge_id === edgeId);
                            
                            windowsOnEdge.forEach(window => {
                                holesCount++;
                                const windowDef = data.window_definitions.find(w => w.id === window.window_definition_id);
                                if (!windowDef) return;
                                
                                const edge = story.geometry.edges.find(e => e.id === edgeId);
                                if (!edge) return;
                                
                                const v1 = story.geometry.vertices.find(v => v.id === edge.vertex_ids[0]);
                                const v2 = story.geometry.vertices.find(v => v.id === edge.vertex_ids[1]);
                                if (!v1 || !v2) return;
                                
                                const centerX = v1.x + (v2.x - v1.x) * window.alpha;
                                const centerZ = -(v1.y + (v2.y - v1.y) * window.alpha);
                                const centerY = (windowDef.sill_height || 3) + windowDef.height / 2;
                                
                                // Create window box to subtract
                                const windowBox = new THREE.BoxGeometry(windowDef.width + 0.2, windowDef.height + 0.2, 2);
                                const windowMesh = new THREE.Mesh(windowBox);
                                
                                const angle = Math.atan2(v2.y - v1.y, v2.x - v1.x);
                                windowMesh.rotation.y = -angle;
                                windowMesh.position.set(centerX, centerY, centerZ);
                                windowMesh.updateMatrix();
                                
                                const windowBSP = new ThreeBSP(windowMesh);
                                wallBSP = wallBSP.subtract(windowBSP);
                            });
                        });
                        
                        console.log(\`Cut \${holesCount} window holes in space \${space.name}\`);
                        finalMesh = wallBSP.toMesh(material);
                        finalMesh.geometry.computeFaceNormals();
                        finalMesh.geometry.computeVertexNormals();
                        finalMesh.position.y = zOffset;
                    } else {
                        console.warn('ThreeBSP not available - walls will not have holes');
                    }
                    
                    buildingGroup.add(finalMesh);
                    
                    const edges = new THREE.EdgesGeometry(finalMesh.geometry);
                    const line = new THREE.LineSegments(
                        edges,
                        new THREE.LineBasicMaterial({ color: 0x000000, linewidth: 2 })
                    );
                    line.position.y = zOffset;
                    buildingGroup.add(line);
                });
                
                // Add shading elements (roofs/overhangs)
                story.shading.forEach(shading => {
                    const face = story.geometry.faces.find(f => f.id === shading.face_id);
                    if (!face) return;
                    
                    const vertices = getVerticesForFace(face, story.geometry);
                    if (vertices.length < 3) return;
                    
                    const shape = new THREE.Shape();
                    shape.moveTo(vertices[0].x, vertices[0].z);
                    for (let i = 1; i < vertices.length; i++) {
                        shape.lineTo(vertices[i].x, vertices[i].z);
                    }
                    
                    // Create a flat roof/overhang with minimal thickness
                    const geometry = new THREE.ExtrudeGeometry(shape, {
                        depth: 0.2,
                        bevelEnabled: false
                    });
                    geometry.rotateX(-Math.PI / 2);
                    
                    const material = new THREE.MeshPhongMaterial({
                        color: 0x8B7355,
                        transparent: false,
                        opacity: 1.0,
                        side: THREE.DoubleSide
                    });
                    
                    const mesh = new THREE.Mesh(geometry, material);
                    mesh.position.y = zOffset + storyHeight;
                    buildingGroup.add(mesh);
                });
                
                // Add windows - using exact same logic as doors
                story.windows.forEach(window => {
                    const windowDef = data.window_definitions.find(w => w.id === window.window_definition_id);
                    if (!windowDef) return;
                    
                    const edge = story.geometry.edges.find(e => e.id === window.edge_id);
                    if (!edge) return;
                    
                    const v1 = story.geometry.vertices.find(v => v.id === edge.vertex_ids[0]);
                    const v2 = story.geometry.vertices.find(v => v.id === edge.vertex_ids[1]);
                    if (!v1 || !v2) return;
                    
                    const windowPos = window.alpha;
                    
                    const centerX = v1.x + (v2.x - v1.x) * windowPos;
                    const centerZ = -(v1.y + (v2.y - v1.y) * windowPos);
                    // Position window bottom at sill height, center at sill + half height
                    const centerY = zOffset + (windowDef.sill_height || 3) + windowDef.height / 2;
                    
                    // Store coordinates for debugging
                    window._debugCoords = {
                        x: centerX,
                        y: centerY,
                        z: centerZ,
                        v1: { x: v1.x, y: v1.y },
                        v2: { x: v2.x, y: v2.y },
                        angle: Math.atan2(v2.y - v1.y, v2.x - v1.x) * (180 / Math.PI)
                    };
                    
                    // Create transparent glass window
                    const windowGeometry = new THREE.BoxGeometry(windowDef.width, windowDef.height, 0.1);
                    const windowMaterial = new THREE.MeshPhongMaterial({
                        color: 0xADD8E6,
                        transparent: true,
                        opacity: 0.15,
                        side: THREE.DoubleSide,
                        depthWrite: false
                    });
                    
                    const windowMesh = new THREE.Mesh(windowGeometry, windowMaterial);
                    
                    // Use exact same rotation as doors
                    const angle = Math.atan2(v2.y - v1.y, v2.x - v1.x);
                    windowMesh.rotation.y = -angle;
                    
                    // Use exact same position setting as doors
                    windowMesh.position.set(centerX, centerY, centerZ);
                    buildingGroup.add(windowMesh);
                    
                    // Add thin black border outline around window
                    const borderThickness = 0.15;
                    const borderGeometry = new THREE.BoxGeometry(
                        windowDef.width + borderThickness * 2,
                        windowDef.height + borderThickness * 2,
                        0.1
                    );
                    const borderEdges = new THREE.EdgesGeometry(borderGeometry);
                    const borderLine = new THREE.LineSegments(
                        borderEdges,
                        new THREE.LineBasicMaterial({ color: 0x000000, linewidth: 2 })
                    );
                    
                    borderLine.rotation.y = -angle;
                    borderLine.position.set(centerX, centerY, centerZ);
                    buildingGroup.add(borderLine);
                    
                    console.log(\`Window \${window.name}: pos(\${centerX.toFixed(2)}, \${centerY.toFixed(2)}, \${centerZ.toFixed(2)}), angle: \${(angle * 180 / Math.PI).toFixed(2)}°, edge: \${window.edge_id}, alpha: \${windowPos.toFixed(3)}\`);
                });
                
                // Add doors
                story.doors.forEach(door => {
                    const doorDef = data.door_definitions.find(d => d.id === door.door_definition_id);
                    if (!doorDef) return;
                    
                    const edge = story.geometry.edges.find(e => e.id === door.edge_id);
                    if (!edge) return;
                    
                    const v1 = story.geometry.vertices.find(v => v.id === edge.vertex_ids[0]);
                    const v2 = story.geometry.vertices.find(v => v.id === edge.vertex_ids[1]);
                    if (!v1 || !v2) return;
                    
                    const doorPos = door.alpha;
                    
                    const centerX = v1.x + (v2.x - v1.x) * doorPos;
                    const centerZ = -(v1.y + (v2.y - v1.y) * doorPos);
                    const centerY = zOffset + doorDef.height / 2;
                    
                    // Store coordinates for debugging
                    door._debugCoords = {
                        x: centerX,
                        y: centerY,
                        z: centerZ,
                        v1: { x: v1.x, y: v1.y },
                        v2: { x: v2.x, y: v2.y },
                        angle: Math.atan2(v2.y - v1.y, v2.x - v1.x) * (180 / Math.PI)
                    };
                    
                    const doorGeometry = new THREE.BoxGeometry(doorDef.width, doorDef.height, 0.3);
                    const doorMaterial = new THREE.MeshPhongMaterial({
                        color: 0x8B4513,
                        transparent: false,
                        opacity: 1.0,
                        side: THREE.DoubleSide
                    });
                    
                    const doorMesh = new THREE.Mesh(doorGeometry, doorMaterial);
                    
                    const angle = Math.atan2(v2.y - v1.y, v2.x - v1.x);
                    doorMesh.rotation.y = -angle;
                    
                    doorMesh.position.set(centerX, centerY, centerZ);
                    buildingGroup.add(doorMesh);
                    
                    // Add thin black border outline around door
                    const doorBorderThickness = 0.15;
                    const doorBorderGeometry = new THREE.BoxGeometry(
                        doorDef.width + doorBorderThickness * 2,
                        doorDef.height + doorBorderThickness * 2,
                        0.3
                    );
                    const doorBorderEdges = new THREE.EdgesGeometry(doorBorderGeometry);
                    const doorBorderLine = new THREE.LineSegments(
                        doorBorderEdges,
                        new THREE.LineBasicMaterial({ color: 0x000000, linewidth: 2 })
                    );
                    
                    doorBorderLine.rotation.y = -angle;
                    doorBorderLine.position.set(centerX, centerY, centerZ);
                    buildingGroup.add(doorBorderLine);
                    
                    console.log(\`Door \${door.name || 'unnamed'}: pos(\${centerX.toFixed(2)}, \${centerY.toFixed(2)}, \${centerZ.toFixed(2)}), angle: \${(angle * 180 / Math.PI).toFixed(2)}°, edge: \${door.edge_id}, alpha: \${doorPos.toFixed(3)}\`);
                });
            });
            
            centerCamera();
        }

        function getVerticesForFace(face, geometry) {
            const vertices = [];
            const processedVertices = new Set();
            
            face.edge_ids.forEach((edgeId, index) => {
                const edge = geometry.edges.find(e => e.id === edgeId);
                if (!edge) return;
                
                const order = face.edge_order[index];
                const vertexId = order === 1 ? edge.vertex_ids[0] : edge.vertex_ids[1];
                
                if (!processedVertices.has(vertexId)) {
                    const vertex = geometry.vertices.find(v => v.id === vertexId);
                    if (vertex) {
                        vertices.push({ x: vertex.x, z: vertex.y });
                        processedVertices.add(vertexId);
                    }
                }
            });
            
            return vertices;
        }

        function displayBuildingInfo(data) {
            const infoDiv = document.getElementById('buildingInfo');
            let html = '<div class="section"><h2>Project Info</h2>';
            html += \`<div class="property"><span class="property-label">Units:</span><span class="property-value">\${data.project.config.units}</span></div>\`;
            html += \`<div class="property"><span class="property-label">Language:</span><span class="property-value">\${data.project.config.language}</span></div>\`;
            html += \`<div class="property"><span class="property-label">Grid Spacing:</span><span class="property-value">\${data.project.grid.spacing}</span></div>\`;
            html += \`<div class="property"><span class="property-label">Stories:</span><span class="property-value">\${data.stories.length}</span></div>\`;
            html += '</div>';
            
            data.stories.forEach((story, storyIndex) => {
                const storyId = \`story-\${storyIndex}\`;
                html += \`<button class="collapsible" onclick="toggleCollapsible('\${storyId}')">Story \${storyIndex + 1}: \${story.name}</button>\`;
                html += \`<div id="\${storyId}" class="collapsible-content">\`;
                html += \`<div class="property"><span class="property-label">Height:</span><span class="property-value">\${story.floor_to_ceiling_height}</span></div>\`;
                html += \`<div class="property"><span class="property-label">Multiplier:</span><span class="property-value">\${story.multiplier}</span></div>\`;
                html += \`<div class="property"><span class="property-label">Color:</span><span class="property-value"><span class="color-indicator" style="background-color: \${story.color}"></span>\${story.color}</span></div>\`;
                
                // Spaces collapsible
                const spacesId = \`\${storyId}-spaces\`;
                html += \`<button class="collapsible nested-collapsible" onclick="toggleCollapsible('\${spacesId}')">Spaces (\${story.spaces.length})</button>\`;
                html += \`<div id="\${spacesId}" class="collapsible-content nested-collapsible-content">\`;
                story.spaces.forEach((space, spaceIndex) => {
                    html += \`<div class="component-item">\`;
                    html += \`<span class="color-indicator" style="background-color: \${space.color}"></span>\`;
                    html += \`<strong>\${space.name}</strong><br>\`;
                    html += \`<span class="property-label">Type:</span> \${space.type}<br>\`;
                    if (space.building_unit_id) html += \`<span class="property-label">Building Unit:</span> \${space.building_unit_id}<br>\`;
                    if (space.thermal_zone_id) html += \`<span class="property-label">Thermal Zone:</span> \${space.thermal_zone_id}<br>\`;
                    html += '</div>';
                });
                html += '</div>';
                
                // Windows collapsible
                const windowsId = \`\${storyId}-windows\`;
                html += \`<button class="collapsible nested-collapsible" onclick="toggleCollapsible('\${windowsId}')">Windows (\${story.windows.length})</button>\`;
                html += \`<div id="\${windowsId}" class="collapsible-content nested-collapsible-content">\`;
                story.windows.forEach((window, winIndex) => {
                    const windowDef = data.window_definitions.find(w => w.id === window.window_definition_id);
                    html += \`<div class="component-item">\`;
                    html += \`<strong>\${window.name || 'Window ' + (winIndex + 1)}</strong><br>\`;
                    if (windowDef) {
                        html += \`<span class="property-label">Width:</span> \${windowDef.width}<br>\`;
                        html += \`<span class="property-label">Height:</span> \${windowDef.height}<br>\`;
                        html += \`<span class="property-label">Sill Height:</span> \${windowDef.sill_height}<br>\`;
                        html += \`<span class="property-label">Type:</span> \${windowDef.window_type}<br>\`;
                    }
                    html += \`<span class="property-label">Position (α):</span> \${window.alpha.toFixed(3)}<br>\`;
                    html += \`<span class="property-label">Edge ID:</span> \${window.edge_id}<br>\`;
                    if (window._debugCoords) {
                        html += \`<span class="property-label">3D Position:</span><br>\`;
                        html += \`&nbsp;&nbsp;X: \${window._debugCoords.x.toFixed(2)}<br>\`;
                        html += \`&nbsp;&nbsp;Y: \${window._debugCoords.y.toFixed(2)}<br>\`;
                        html += \`&nbsp;&nbsp;Z: \${window._debugCoords.z.toFixed(2)}<br>\`;
                        html += \`<span class="property-label">Edge Vertices:</span><br>\`;
                        html += \`&nbsp;&nbsp;V1: (\${window._debugCoords.v1.x}, \${window._debugCoords.v1.y})<br>\`;
                        html += \`&nbsp;&nbsp;V2: (\${window._debugCoords.v2.x}, \${window._debugCoords.v2.y})<br>\`;
                        html += \`<span class="property-label">Rotation:</span> \${window._debugCoords.angle.toFixed(2)}°\`;
                    }
                    html += '</div>';
                });
                html += '</div>';
                
                // Doors collapsible
                const doorsId = \`\${storyId}-doors\`;
                html += \`<button class="collapsible nested-collapsible" onclick="toggleCollapsible('\${doorsId}')">Doors (\${story.doors.length})</button>\`;
                html += \`<div id="\${doorsId}" class="collapsible-content nested-collapsible-content">\`;
                story.doors.forEach((door, doorIndex) => {
                    const doorDef = data.door_definitions.find(d => d.id === door.door_definition_id);
                    html += \`<div class="component-item">\`;
                    html += \`<strong>\${door.name || 'Door ' + (doorIndex + 1)}</strong><br>\`;
                    if (doorDef) {
                        html += \`<span class="property-label">Width:</span> \${doorDef.width}<br>\`;
                        html += \`<span class="property-label">Height:</span> \${doorDef.height}<br>\`;
                        html += \`<span class="property-label">Type:</span> \${doorDef.door_type}<br>\`;
                    }
                    html += \`<span class="property-label">Position (α):</span> \${door.alpha.toFixed(3)}<br>\`;
                    html += \`<span class="property-label">Edge ID:</span> \${door.edge_id}<br>\`;
                    if (door._debugCoords) {
                        html += \`<span class="property-label">3D Position:</span><br>\`;
                        html += \`&nbsp;&nbsp;X: \${door._debugCoords.x.toFixed(2)}<br>\`;
                        html += \`&nbsp;&nbsp;Y: \${door._debugCoords.y.toFixed(2)}<br>\`;
                        html += \`&nbsp;&nbsp;Z: \${door._debugCoords.z.toFixed(2)}<br>\`;
                        html += \`<span class="property-label">Edge Vertices:</span><br>\`;
                        html += \`&nbsp;&nbsp;V1: (\${door._debugCoords.v1.x}, \${door._debugCoords.v1.y})<br>\`;
                        html += \`&nbsp;&nbsp;V2: (\${door._debugCoords.v2.x}, \${door._debugCoords.v2.y})<br>\`;
                        html += \`<span class="property-label">Rotation:</span> \${door._debugCoords.angle.toFixed(2)}°\`;
                    }
                    html += '</div>';
                });
                html += '</div>';
                
                // Shading collapsible
                const shadingId = \`\${storyId}-shading\`;
                html += \`<button class="collapsible nested-collapsible" onclick="toggleCollapsible('\${shadingId}')">Shading (\${story.shading.length})</button>\`;
                html += \`<div id="\${shadingId}" class="collapsible-content nested-collapsible-content">\`;
                story.shading.forEach((shading, shadingIndex) => {
                    html += \`<div class="component-item">\`;
                    html += \`<strong>\${shading.name}</strong><br>\`;
                    html += \`<span class="property-label">Type:</span> \${shading.type}<br>\`;
                    html += \`<span class="property-label">Color:</span> <span class="color-indicator" style="background-color: \${shading.color}"></span>\${shading.color}<br>\`;
                    html += \`<span class="property-label">Face ID:</span> \${shading.face_id}\`;
                    html += '</div>';
                });
                html += '</div>';
                
                html += '</div>';
            });
            
            infoDiv.innerHTML = html;
        }
        
        function toggleCollapsible(id) {
            const content = document.getElementById(id);
            const button = content.previousElementSibling;
            
            content.classList.toggle('active');
            button.classList.toggle('active');
        }

        function centerCamera() {
            const box = new THREE.Box3().setFromObject(buildingGroup);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());
            
            const maxDim = Math.max(size.x, size.y, size.z);
            const fov = camera.fov * (Math.PI / 180);
            let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
            
            cameraZ *= 2;
            
            camera.position.set(center.x + cameraZ, center.y + cameraZ, center.z + cameraZ);
            camera.lookAt(center);
            
            controls.target.copy(center);
            controls.update();
        }

        function resetCamera() {
            centerCamera();
        }

        function toggleAxes() {
            axesHelper.visible = !axesHelper.visible;
        }

        function loadAIGeneratedRoom() {
            // Load the AI-generated room JSON file
            fetch('/room_20251220_152544.json')
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Failed to load AI-generated room JSON');
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('AI-generated room data loaded:', data);
                    createBuilding(data);
                    displayBuildingInfo(data);
                })
                .catch(error => {
                    console.error('Error loading AI-generated room:', error);
                    // Fallback to sample building if AI room fails to load
                    console.log('Falling back to sample building');
                    loadSampleBuilding();
                });
        }

        function loadFromURL() {
            const url = document.getElementById('urlInput').value;
            if (!url) {
                alert('Please enter a URL');
                return;
            }
            
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    createBuilding(data);
                    displayBuildingInfo(data);
                })
                .catch(error => {
                    console.error('Error loading from URL:', error);
                    alert('Error loading from URL: ' + error.message);
                });
        }

        function loadFromFile(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            const reader = new FileReader();
            reader.onload = function(e) {
                try {
                    const data = JSON.parse(e.target.result);
                    createBuilding(data);
                    displayBuildingInfo(data);
                } catch (error) {
                    console.error('Error parsing JSON:', error);
                    alert('Error parsing JSON file: ' + error.message);
                }
            };
            reader.readAsText(file);
        }

        // Initialize when page loads
        window.addEventListener('load', function() {
            init3DViewer();
            
            // Auto-load the AI-generated room JSON
            const projectId = '${projectId}';
            console.log('Loading AI-generated room for project:', projectId);
            
            // Load the specific JSON file
            loadAIGeneratedRoom();
        });
    </script>
</body>
</html>
  `;

  return (
    <div className="integrated-3d-viewer" ref={containerRef}>
      {loading && (
        <div className="viewer-loading">
          <div className="spinner"></div>
          <p>Loading 3D Viewer...</p>
        </div>
      )}
      <iframe
        ref={iframeRef}
        srcDoc={iframeContent}
        title="3D Floorspace Viewer"
        className="viewer-iframe"
        style={{ 
          width: '100%', 
          height: '100%', 
          border: 'none',
          display: loading ? 'none' : 'block'
        }}
      />
    </div>
  );
};

export default Integrated3DViewer;