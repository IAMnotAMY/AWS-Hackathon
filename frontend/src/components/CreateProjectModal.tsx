import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import './CreateProjectModal.css';

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const CreateProjectModal = ({ isOpen, onClose, onSuccess }: CreateProjectModalProps) => {
  const navigate = useNavigate();
  const [projectName, setProjectName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const validateForm = (): boolean => {
    if (!projectName.trim()) {
      setError('Project name is required');
      return false;
    }
    setError('');
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Generate a unique project ID
      const projectId = `project-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      
      const project = await api.createUpdateProject(projectId, {
        name: projectName.trim(),
        description: description.trim() || undefined,
      });

      // Success - redirect to editor
      onSuccess();
      navigate(`/editor/${project.projectId}`);
    } catch (err: any) {
      console.error('Error creating project:', err);
      
      if (err.response?.status === 401) {
        setError('Session expired. Please log in again.');
      } else if (err.response?.data?.error?.message) {
        setError(err.response.data.error.message);
      } else {
        setError('Failed to create project. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      setProjectName('');
      setDescription('');
      setError('');
      onClose();
    }
  };

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Create New Project</h2>
          <button
            className="modal-close-btn"
            onClick={handleClose}
            disabled={loading}
            aria-label="Close modal"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="projectName">Project Name *</label>
            <input
              id="projectName"
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="Enter project name"
              disabled={loading}
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter project description (optional)"
              rows={3}
              disabled={loading}
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <div className="modal-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={handleClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={loading}
            >
              {loading ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateProjectModal;
