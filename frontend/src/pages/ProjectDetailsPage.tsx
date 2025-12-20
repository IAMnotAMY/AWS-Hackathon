import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, Project } from '../services/api';
import FloorspaceViewer from '../components/FloorspaceViewer';
import './ProjectDetailsPage.css';

const ProjectDetailsPage = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'viewer' | 'details' | 'settings'>('viewer');

  useEffect(() => {
    if (projectId) {
      fetchProject();
    }
  }, [projectId]);

  const fetchProject = async () => {
    if (!projectId) return;
    
    setLoading(true);
    setError('');
    
    try {
      const fetchedProject = await api.getProject(projectId);
      setProject(fetchedProject);
    } catch (err: any) {
      console.error('Error fetching project:', err);
      setError('Failed to load project. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    navigate('/dashboard');
  };

  const formatDate = (timestamp: string | number) => {
    let date: Date;
    
    if (typeof timestamp === 'string') {
      const numTimestamp = parseInt(timestamp, 10);
      if (!isNaN(numTimestamp)) {
        date = new Date(numTimestamp * 1000);
      } else {
        date = new Date(timestamp);
      }
    } else {
      date = new Date(timestamp * 1000);
    }
    
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="project-details-container">
        <div className="project-details-loading">
          <div className="spinner"></div>
          <p>Loading project...</p>
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="project-details-container">
        <div className="project-details-error">
          <h2>Error</h2>
          <p>{error || 'Project not found'}</p>
          <button onClick={handleBack} className="btn btn-primary">
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="project-details-container">
      {/* Header */}
      <header className="project-details-header">
        <div className="project-details-header-content">
          <div className="project-details-header-left">
            <button onClick={handleBack} className="btn-back">
              ← Back to Dashboard
            </button>
            <div className="project-details-title-section">
              <h1 className="project-details-title">{project.ProjectName}</h1>
              {project.Description && (
                <p className="project-details-subtitle">{project.Description}</p>
              )}
            </div>
          </div>
          <div className="project-details-header-right">
            <div className="project-details-meta">
              <span className="project-details-meta-item">
                Created: {formatDate(project.CreatedTime)}
              </span>
              <span className="project-details-meta-item">
                Updated: {formatDate(project.UpdatedTime)}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="project-details-nav">
        <div className="project-details-nav-content">
          <button
            className={`nav-tab ${activeTab === 'viewer' ? 'active' : ''}`}
            onClick={() => setActiveTab('viewer')}
          >
            3D Viewer
          </button>
          <button
            className={`nav-tab ${activeTab === 'details' ? 'active' : ''}`}
            onClick={() => setActiveTab('details')}
          >
            Project Details
          </button>
          <button
            className={`nav-tab ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('settings')}
          >
            Settings
          </button>
        </div>
      </nav>

      {/* Content */}
      <main className="project-details-content">
        {activeTab === 'viewer' && (
          <div className="tab-content">
            <FloorspaceViewer projectId={project.ProjectID} />
          </div>
        )}

        {activeTab === 'details' && (
          <div className="tab-content">
            <div className="project-details-info">
              <div className="info-section">
                <h3>Project Information</h3>
                <div className="info-grid">
                  <div className="info-item">
                    <label>Project ID</label>
                    <span>{project.ProjectID}</span>
                  </div>
                  <div className="info-item">
                    <label>Owner</label>
                    <span>{project.UserID}</span>
                  </div>
                  <div className="info-item">
                    <label>Created</label>
                    <span>{formatDate(project.CreatedTime)}</span>
                  </div>
                  <div className="info-item">
                    <label>Last Modified</label>
                    <span>{formatDate(project.UpdatedTime)}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="tab-content">
            <div className="project-settings">
              <div className="settings-section">
                <h3>Project Settings</h3>
                <p>Project settings and configuration options will be available here.</p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default ProjectDetailsPage;