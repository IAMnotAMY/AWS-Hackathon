import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Project } from '../services/api';

interface ProjectCardProps {
  project: Project;
  onDelete: (projectId: string) => void;
}

const ProjectCard = ({ project, onDelete }: ProjectCardProps) => {
  const navigate = useNavigate();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleClick = () => {
    navigate(`/project/${project.ProjectID}`);
  };

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowDeleteConfirm(true);
  };

  const handleConfirmDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(project.ProjectID);
    setShowDeleteConfirm(false);
  };

  const handleCancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowDeleteConfirm(false);
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
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="card" onClick={handleClick} style={{ cursor: 'pointer', position: 'relative' }}>
      {/* Project Preview */}
      <div style={{ 
        height: '180px', 
        background: 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative'
      }}>
        <svg 
          style={{ width: '48px', height: '48px', color: '#1976d2' }} 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={1.5} 
            d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" 
          />
        </svg>
        
        {/* 3D Badge */}
        <div style={{
          position: 'absolute',
          top: '12px',
          left: '12px',
          background: 'rgba(255,255,255,0.9)',
          padding: '4px 8px',
          borderRadius: '12px',
          fontSize: '12px',
          fontWeight: '500',
          color: '#1976d2'
        }}>
          3D View
        </div>

        {/* Delete Button */}
        <button
          style={{
            position: 'absolute',
            top: '12px',
            right: '12px',
            width: '32px',
            height: '32px',
            background: 'rgba(255,255,255,0.9)',
            border: 'none',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            color: '#666'
          }}
          onClick={handleDeleteClick}
          onMouseOver={(e) => e.currentTarget.style.color = '#dc3545'}
          onMouseOut={(e) => e.currentTarget.style.color = '#666'}
        >
          <svg style={{ width: '16px', height: '16px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
      
      {/* Project Info */}
      <div style={{ padding: '20px' }}>
        <h3 style={{ 
          fontSize: '18px', 
          fontWeight: '600', 
          marginBottom: '8px',
          color: '#333'
        }}>
          {project.ProjectName}
        </h3>
        
        {project.Description && (
          <p style={{ 
            color: '#666', 
            fontSize: '14px', 
            marginBottom: '16px',
            lineHeight: '1.4'
          }}>
            {project.Description}
          </p>
        )}
        
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          fontSize: '12px',
          color: '#999'
        }}>
          <span>Created {formatDate(project.CreatedTime)}</span>
          <span style={{ color: '#007bff', fontWeight: '500' }}>View →</span>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div 
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(255,255,255,0.95)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px'
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div style={{ textAlign: 'center' }}>
            <h4 style={{ marginBottom: '8px', fontSize: '16px' }}>Delete Project?</h4>
            <p style={{ color: '#666', fontSize: '14px', marginBottom: '20px' }}>
              This action cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                className="btn btn-secondary"
                style={{ flex: 1, fontSize: '12px', padding: '8px 16px' }}
                onClick={handleCancelDelete}
              >
                Cancel
              </button>
              <button
                className="btn"
                style={{ 
                  flex: 1, 
                  fontSize: '12px', 
                  padding: '8px 16px',
                  background: '#dc3545',
                  color: 'white'
                }}
                onClick={handleConfirmDelete}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectCard;
