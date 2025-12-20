import { useEffect, useRef, useState } from 'react';
import './FloorspaceViewer.css';

interface FloorspaceViewerProps {
  projectId: string;
}

const FloorspaceViewer = ({ projectId }: FloorspaceViewerProps) => {
  const viewerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [floorspaceData, setFloorspaceData] = useState<any>(null);

  useEffect(() => {
    loadFloorspaceData();
  }, [projectId]);

  const loadFloorspaceData = async () => {
    setLoading(true);
    setError('');

    try {
      // For now, we'll use sample data
      // In a real implementation, you'd fetch the floorspace JSON from your API
      const sampleFloorspaceData = {
        version: "1.0.0",
        application: {
          name: "Floorspace.js",
          version: "1.0.0"
        },
        project: {
          name: "Sample Project",
          north_axis: 0
        },
        stories: [
          {
            id: "story-1",
            name: "Ground Floor",
            multiplier: 1,
            spaces: [
              {
                id: "space-1",
                name: "Living Room",
                face_id: "face-1",
                type: "living"
              },
              {
                id: "space-2", 
                name: "Kitchen",
                face_id: "face-2",
                type: "kitchen"
              }
            ],
            geometry: [
              {
                id: "face-1",
                vertices: [
                  { x: 0, y: 0 },
                  { x: 20, y: 0 },
                  { x: 20, y: 15 },
                  { x: 0, y: 15 }
                ]
              },
              {
                id: "face-2",
                vertices: [
                  { x: 20, y: 0 },
                  { x: 35, y: 0 },
                  { x: 35, y: 10 },
                  { x: 20, y: 10 }
                ]
              }
            ]
          }
        ]
      };

      setFloorspaceData(sampleFloorspaceData);
      initializeViewer(sampleFloorspaceData);
    } catch (err: any) {
      console.error('Error loading floorspace data:', err);
      setError('Failed to load floorspace data');
    } finally {
      setLoading(false);
    }
  };

  const initializeViewer = (data: any) => {
    if (!viewerRef.current) return;

    // Clear previous content
    viewerRef.current.innerHTML = '';

    // Create SVG for 2D view (we'll enhance this to 3D later)
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', '100%');
    svg.setAttribute('viewBox', '0 0 400 300');
    svg.style.background = '#f8f9fa';

    // Draw spaces
    data.stories[0].geometry.forEach((face: any, index: number) => {
      const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
      const points = face.vertices.map((v: any) => `${v.x * 8},${v.y * 8}`).join(' ');
      polygon.setAttribute('points', points);
      polygon.setAttribute('fill', index === 0 ? '#e3f2fd' : '#f3e5f5');
      polygon.setAttribute('stroke', '#2196f3');
      polygon.setAttribute('stroke-width', '2');
      polygon.style.cursor = 'pointer';
      
      // Add hover effects
      polygon.addEventListener('mouseenter', () => {
        polygon.setAttribute('fill', '#bbdefb');
      });
      
      polygon.addEventListener('mouseleave', () => {
        polygon.setAttribute('fill', index === 0 ? '#e3f2fd' : '#f3e5f5');
      });

      svg.appendChild(polygon);

      // Add space labels
      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      const centerX = face.vertices.reduce((sum: number, v: any) => sum + v.x, 0) / face.vertices.length * 8;
      const centerY = face.vertices.reduce((sum: number, v: any) => sum + v.y, 0) / face.vertices.length * 8;
      
      text.setAttribute('x', centerX.toString());
      text.setAttribute('y', centerY.toString());
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('dominant-baseline', 'middle');
      text.setAttribute('fill', '#1976d2');
      text.setAttribute('font-family', 'Inter, sans-serif');
      text.setAttribute('font-weight', '600');
      text.setAttribute('font-size', '14');
      
      const spaceName = data.stories[0].spaces[index]?.name || `Space ${index + 1}`;
      text.textContent = spaceName;
      
      svg.appendChild(text);
    });

    viewerRef.current.appendChild(svg);
  };

  const handleExport = () => {
    if (floorspaceData) {
      const dataStr = JSON.stringify(floorspaceData, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `floorspace-${projectId}.json`;
      link.click();
      URL.revokeObjectURL(url);
    }
  };

  if (loading) {
    return (
      <div className="floorspace-viewer">
        <div className="viewer-loading">
          <div className="spinner"></div>
          <p>Loading 3D viewer...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="floorspace-viewer">
        <div className="viewer-error">
          <h3>Error Loading Viewer</h3>
          <p>{error}</p>
          <button onClick={loadFloorspaceData} className="btn btn-primary">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="floorspace-viewer">
      <div className="viewer-toolbar">
        <div className="viewer-toolbar-left">
          <h3>3D Floorspace Viewer</h3>
          <span className="viewer-status">Ready</span>
        </div>
        <div className="viewer-toolbar-right">
          <button className="btn btn-secondary" onClick={loadFloorspaceData}>
            Refresh
          </button>
          <button className="btn btn-primary" onClick={handleExport}>
            Export JSON
          </button>
        </div>
      </div>
      
      <div className="viewer-container" ref={viewerRef}>
        {/* 3D viewer will be rendered here */}
      </div>
      
      <div className="viewer-info">
        <div className="info-panel">
          <h4>Project Information</h4>
          <div className="info-items">
            <div className="info-item">
              <span className="label">Stories:</span>
              <span className="value">{floorspaceData?.stories?.length || 0}</span>
            </div>
            <div className="info-item">
              <span className="label">Spaces:</span>
              <span className="value">
                {floorspaceData?.stories?.reduce((total: number, story: any) => 
                  total + (story.spaces?.length || 0), 0) || 0}
              </span>
            </div>
            <div className="info-item">
              <span className="label">Version:</span>
              <span className="value">{floorspaceData?.version || 'N/A'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FloorspaceViewer;