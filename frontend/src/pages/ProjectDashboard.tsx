import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api, Project } from '../services/api';
import ProjectCard from '../components/ProjectCard';
import CreateProjectModal from '../components/CreateProjectModal';
import './ProjectDashboard.css';

const ProjectDashboard = () => {
  const { signOut } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);

  const fetchProjects = async () => {
    setLoading(true);
    setError('');
    
    try {
      const fetchedProjects = await api.listProjects();
      setProjects(fetchedProjects);
    } catch (err: any) {
      console.error('Error fetching projects:', err);
      
      if (err.response?.status === 401) {
        setError('Session expired. Please log in again.');
      } else if (err.response?.data?.error?.message) {
        setError(err.response.data.error.message);
      } else {
        setError('Failed to load projects. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleDeleteProject = async (projectId: string) => {
    try {
      await api.deleteProject(projectId);
      
      // Update the projects list by removing the deleted project
      setProjects((prevProjects) =>
        prevProjects.filter((project) => project.projectId !== projectId)
      );
    } catch (err: any) {
      console.error('Error deleting project:', err);
      
      if (err.response?.status === 401) {
        setError('Session expired. Please log in again.');
      } else if (err.response?.status === 403) {
        setError("You don't have permission to delete this project.");
      } else if (err.response?.status === 404) {
        setError('Project not found.');
      } else if (err.response?.data?.error?.message) {
        setError(err.response.data.error.message);
      } else {
        setError('Failed to delete project. Please try again.');
      }
    }
  };

  const handleCreateSuccess = () => {
    setShowCreateModal(false);
    // Refresh the projects list
    fetchProjects();
  };

  const handleSignOut = async () => {
    await signOut();
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>My Projects</h1>
        <div className="dashboard-header-actions">
          <button
            className="btn-create-project"
            onClick={() => setShowCreateModal(true)}
          >
            + New Project
          </button>
          <button className="btn-sign-out" onClick={handleSignOut}>
            Sign Out
          </button>
        </div>
      </header>

      <main className="dashboard-content">
        {loading && (
          <div className="dashboard-loading">
            <div className="spinner"></div>
            <p>Loading projects...</p>
          </div>
        )}

        {error && (
          <div className="dashboard-error">
            <p>{error}</p>
            <button onClick={fetchProjects}>Try Again</button>
          </div>
        )}

        {!loading && !error && projects.length === 0 && (
          <div className="dashboard-empty">
            <h2>No projects yet</h2>
            <p>Create your first floorspace project to get started.</p>
            <button
              className="btn-create-first-project"
              onClick={() => setShowCreateModal(true)}
            >
              Create Project
            </button>
          </div>
        )}

        {!loading && !error && projects.length > 0 && (
          <div className="projects-grid">
            {projects.map((project) => (
              <ProjectCard
                key={project.projectId}
                project={project}
                onDelete={handleDeleteProject}
              />
            ))}
          </div>
        )}
      </main>

      <CreateProjectModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={handleCreateSuccess}
      />
    </div>
  );
};

export default ProjectDashboard;
