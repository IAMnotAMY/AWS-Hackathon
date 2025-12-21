import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api, Project } from '../services/api';
import ProjectCard from '../components/ProjectCard';
import CreateProjectModal from '../components/CreateProjectModal';

const ProjectDashboard = () => {
  const { signOut } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Mock projects for demo - keeping your original Jerusalem project
  const mockProjects: Project[] = [
    {
      ProjectID: 'jerusalem-1',
      UserID: 'user1',
      ProjectName: 'Jerusalem',
      Description: 'Your original project with AI-generated room design',
      CreatedTime: Date.now().toString(),
      UpdatedTime: Date.now().toString()
    }
  ];

  const fetchProjects = async () => {
    setLoading(true);
    setError('');
    
    try {
      // Use mock data instead of API call
      setTimeout(() => {
        setProjects(mockProjects);
        setLoading(false);
      }, 800);
    } catch (err: any) {
      console.error('Error fetching projects:', err);
      setError('Failed to load projects. Please try again.');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleDeleteProject = async (projectId: string) => {
    setProjects((prevProjects) =>
      prevProjects.filter((project) => project.ProjectID !== projectId)
    );
  };

  const handleCreateSuccess = () => {
    setShowCreateModal(false);
    fetchProjects();
  };

  const handleSignOut = async () => {
    await signOut();
  };

  return (
    <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      {/* Header */}
      <header style={{ 
        background: 'white', 
        borderBottom: '1px solid #ddd',
        padding: '20px 0'
      }}>
        <div className="container">
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between' 
          }}>
            <div>
              <h1 style={{ fontSize: '28px', fontWeight: '600', marginBottom: '4px' }}>
                FloorSpace Studio
              </h1>
              <p style={{ color: '#666', fontSize: '14px' }}>
                3D Building Visualization
              </p>
            </div>
            
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                className="btn btn-primary"
                onClick={() => setShowCreateModal(true)}
              >
                + New Project
              </button>
              <button className="btn btn-ghost" onClick={handleSignOut}>
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container" style={{ paddingTop: '40px', paddingBottom: '40px' }}>
        {loading && (
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            justifyContent: 'center', 
            padding: '80px 0' 
          }}>
            <div className="spinner" style={{ marginBottom: '16px' }}></div>
            <p style={{ color: '#666' }}>Loading your projects...</p>
          </div>
        )}

        {error && (
          <div className="card" style={{ maxWidth: '400px', margin: '0 auto', textAlign: 'center' }}>
            <div style={{ padding: '40px' }}>
              <h3 style={{ marginBottom: '8px' }}>Something went wrong</h3>
              <p style={{ color: '#666', marginBottom: '20px' }}>{error}</p>
              <button className="btn btn-primary" onClick={fetchProjects}>
                Try Again
              </button>
            </div>
          </div>
        )}

        {!loading && !error && projects.length === 0 && (
          <div style={{ textAlign: 'center', padding: '80px 0' }}>
            <h2 style={{ fontSize: '24px', marginBottom: '8px' }}>No projects yet</h2>
            <p style={{ color: '#666', marginBottom: '32px', maxWidth: '400px', margin: '0 auto 32px' }}>
              Create your first floorspace project to start designing beautiful 3D building layouts.
            </p>
            <button
              className="btn btn-primary"
              onClick={() => setShowCreateModal(true)}
            >
              + Create Your First Project
            </button>
          </div>
        )}

        {!loading && !error && projects.length > 0 && (
          <div>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between', 
              marginBottom: '32px' 
            }}>
              <div>
                <h2 style={{ fontSize: '20px', marginBottom: '4px' }}>Your Projects</h2>
                <p style={{ color: '#666', fontSize: '14px' }}>
                  {projects.length} project{projects.length !== 1 ? 's' : ''} total
                </p>
              </div>
            </div>

            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', 
              gap: '24px' 
            }}>
              {projects.map((project) => (
                <ProjectCard
                  key={project.ProjectID}
                  project={project}
                  onDelete={handleDeleteProject}
                />
              ))}
            </div>
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
