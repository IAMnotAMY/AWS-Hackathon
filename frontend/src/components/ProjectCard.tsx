import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Project } from '../services/api';
import './ProjectCard.css';

interface ProjectCardProps {
  project: Project;
  onDelete: (projectId: string) => void;
}

const ProjectCard = ({ project, onDelete }: ProjectCardProps) => {
  const navigate = useNavigate();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleClick = () => {
    navigate(`/editor/${project.ProjectID}`);
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
    // Handle Unix timestamp (seconds) as string or number
    let date: Date;
    
    if (typeof timestamp === 'string') {
      // If it's a numeric string (Unix timestamp), convert to number
      const numTimestamp = parseInt(timestamp, 10);
      if (!isNaN(numTimestamp)) {
        date = new Date(numTimestamp * 1000);
      } else {
        // Otherwise treat as ISO string
        date = new Date(timestamp);
      }
    } else {
      // It's a number (Unix timestamp in seconds)
      date = new Date(timestamp * 1000);
    }
    
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="project-card" onClick={handleClick}>
      <div className="project-card-header">
        <h3 className="project-card-title">{project.ProjectName}</h3>
        <button
          className="project-card-delete-btn"
          onClick={handleDeleteClick}
          aria-label="Delete project"
        >
          ×
        </button>
      </div>
      
      {project.Description && (
        <p className="project-card-description">{project.Description}</p>
      )}
      
      <div className="project-card-dates">
        <div className="project-card-date">
          <span className="project-card-date-label">Created:</span>
          <span className="project-card-date-value">{formatDate(project.CreatedTime)}</span>
        </div>
        <div className="project-card-date">
          <span className="project-card-date-label">Modified:</span>
          <span className="project-card-date-value">{formatDate(project.UpdatedTime)}</span>
        </div>
      </div>

      {showDeleteConfirm && (
        <div className="delete-confirmation-modal" onClick={(e) => e.stopPropagation()}>
          <div className="delete-confirmation-content">
            <h4>Delete Project?</h4>
            <p>Are you sure you want to delete "{project.ProjectName}"? This action cannot be undone.</p>
            <div className="delete-confirmation-buttons">
              <button
                className="delete-confirmation-cancel"
                onClick={handleCancelDelete}
              >
                Cancel
              </button>
              <button
                className="delete-confirmation-confirm"
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
