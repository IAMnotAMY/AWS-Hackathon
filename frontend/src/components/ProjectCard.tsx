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
    navigate(`/editor/${project.projectId}`);
  };

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowDeleteConfirm(true);
  };

  const handleConfirmDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(project.projectId);
    setShowDeleteConfirm(false);
  };

  const handleCancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowDeleteConfirm(false);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="project-card" onClick={handleClick}>
      <div className="project-card-header">
        <h3 className="project-card-title">{project.name}</h3>
        <button
          className="project-card-delete-btn"
          onClick={handleDeleteClick}
          aria-label="Delete project"
        >
          ×
        </button>
      </div>
      
      {project.description && (
        <p className="project-card-description">{project.description}</p>
      )}
      
      <div className="project-card-dates">
        <div className="project-card-date">
          <span className="project-card-date-label">Created:</span>
          <span className="project-card-date-value">{formatDate(project.createdAt)}</span>
        </div>
        <div className="project-card-date">
          <span className="project-card-date-label">Modified:</span>
          <span className="project-card-date-value">{formatDate(project.updatedAt)}</span>
        </div>
      </div>

      {showDeleteConfirm && (
        <div className="delete-confirmation-modal" onClick={(e) => e.stopPropagation()}>
          <div className="delete-confirmation-content">
            <h4>Delete Project?</h4>
            <p>Are you sure you want to delete "{project.name}"? This action cannot be undone.</p>
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
