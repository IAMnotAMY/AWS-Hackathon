import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, Project } from '../services/api';
import EditorToolbar from '../components/EditorToolbar';
import './FloorspaceEditorPage.css';

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

const FloorspaceEditorPage = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);
  
  const [project, setProject] = useState<Project | null>(null);
  const [floorspaceData, setFloorspaceData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  const [iframeLoaded, setIframeLoaded] = useState(false);

  // Load project data on mount
  useEffect(() => {
    const loadProject = async () => {
      if (!projectId) {
        setError('No project ID provided');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const projectData = await api.getProject(projectId);
        setProject(projectData);

        // Fetch floorspace JSON from S3 using presigned URL
        if (projectData.floorspaceUrl) {
          const response = await fetch(projectData.floorspaceUrl);
          if (response.ok) {
            const jsonData = await response.json();
            setFloorspaceData(jsonData);
          } else {
            // Initialize with empty floorspace structure if fetch fails
            setFloorspaceData(getEmptyFloorspaceData());
          }
        } else {
          // Initialize with empty floorspace structure
          setFloorspaceData(getEmptyFloorspaceData());
        }
        
        setError('');
      } catch (err: any) {
        console.error('Error loading project:', err);
        
        if (err.response?.status === 404) {
          setError('Project not found.');
        } else if (err.response?.status === 403) {
          setError("You don't have permission to access this project.");
        } else if (err.response?.data?.error?.message) {
          setError(err.response.data.error.message);
        } else {
          setError('Failed to load project. Please try again.');
        }
      } finally {
        setLoading(false);
      }
    };

    loadProject();
  }, [projectId]);

  // Send floorspace data to iframe when both iframe and data are ready
  useEffect(() => {
    if (iframeLoaded && floorspaceData && iframeRef.current?.contentWindow) {
      sendDataToIframe(floorspaceData);
    }
  }, [iframeLoaded, floorspaceData]);

  // Set up auto-save functionality
  useEffect(() => {
    if (floorspaceData && projectId) {
      // Clear existing timer
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }

      // Set up new auto-save timer (30 seconds)
      autoSaveTimerRef.current = setTimeout(() => {
        handleSave();
      }, 30000);
    }

    // Cleanup on unmount
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, [floorspaceData, projectId]);

  // Set up postMessage listener for iframe communication
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      // Verify origin for security (in production, check against floorspace.js domain)
      // For now, we accept messages from any origin since floorspace.js is embedded
      
      if (event.data && event.data.type === 'floorspace-update') {
        // Capture floorspace JSON updates from iframe
        setFloorspaceData(event.data.floorspaceJson);
      }
    };

    window.addEventListener('message', handleMessage);

    return () => {
      window.removeEventListener('message', handleMessage);
    };
  }, []);

  const handleIframeLoad = () => {
    setIframeLoaded(true);
  };

  const sendDataToIframe = (data: any) => {
    if (iframeRef.current?.contentWindow) {
      try {
        iframeRef.current.contentWindow.postMessage(
          {
            type: 'load-floorspace',
            floorspaceJson: data,
          },
          '*' // In production, specify the exact origin
        );
      } catch (err) {
        console.error('Error sending data to iframe:', err);
        setError('Failed to load data into editor.');
      }
    }
  };

  const handleSave = useCallback(async () => {
    if (!projectId || !floorspaceData) {
      return;
    }

    try {
      setSaveStatus('saving');
      await api.uploadFloorspace(projectId, floorspaceData);
      setSaveStatus('saved');
      
      // Reset to idle after 2 seconds
      setTimeout(() => {
        setSaveStatus('idle');
      }, 2000);
    } catch (err: any) {
      console.error('Error saving floorspace:', err);
      setSaveStatus('error');
      
      if (err.response?.status === 403) {
        setError("You don't have permission to save this project.");
      } else if (err.response?.status === 400) {
        setError('Invalid floorspace data.');
      } else if (err.response?.data?.error?.message) {
        setError(err.response.data.error.message);
      } else {
        setError('Failed to save. Please try again.');
      }
    }
  }, [projectId, floorspaceData]);

  const handleBack = () => {
    navigate('/dashboard');
  };

  const handleView3D = () => {
    if (projectId) {
      navigate(`/viewer/${projectId}`);
    }
  };

  const getEmptyFloorspaceData = () => {
    return {
      version: '1.0',
      stories: [],
      building_units: [],
      thermal_zones: [],
      space_types: [],
      construction_sets: [],
    };
  };

  if (loading) {
    return (
      <div className="editor-container">
        <div className="editor-loading">
          <div className="spinner"></div>
          <p>Loading editor...</p>
        </div>
      </div>
    );
  }

  if (error && !project) {
    return (
      <div className="editor-container">
        <div className="editor-error">
          <h2>Error</h2>
          <p>{error}</p>
          <button onClick={handleBack}>Back to Dashboard</button>
        </div>
      </div>
    );
  }

  return (
    <div className="editor-container">
      <EditorToolbar
        projectName={project?.name || 'Untitled Project'}
        saveStatus={saveStatus}
        onSave={handleSave}
        onBack={handleBack}
        onView3D={handleView3D}
      />
      
      {error && (
        <div className="editor-error-banner">
          {error}
        </div>
      )}

      <div className="editor-content">
        <iframe
          ref={iframeRef}
          src="https://nrel.github.io/floorspace.js/"
          title="Floorspace Editor"
          className="floorspace-iframe"
          onLoad={handleIframeLoad}
          sandbox="allow-scripts allow-same-origin allow-forms"
        />
      </div>
    </div>
  );
};

export default FloorspaceEditorPage;
