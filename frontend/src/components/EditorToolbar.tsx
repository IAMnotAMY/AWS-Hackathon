import './EditorToolbar.css';

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

interface EditorToolbarProps {
  projectName: string;
  saveStatus: SaveStatus;
  onSave: () => void;
  onBack: () => void;
  onView3D: () => void;
}

const EditorToolbar = ({
  projectName,
  saveStatus,
  onSave,
  onBack,
  onView3D,
}: EditorToolbarProps) => {
  const getSaveStatusText = () => {
    switch (saveStatus) {
      case 'saving':
        return 'Saving...';
      case 'saved':
        return 'Saved';
      case 'error':
        return 'Save failed';
      default:
        return '';
    }
  };

  const getSaveStatusClass = () => {
    switch (saveStatus) {
      case 'saving':
        return 'save-status-saving';
      case 'saved':
        return 'save-status-saved';
      case 'error':
        return 'save-status-error';
      default:
        return '';
    }
  };

  return (
    <div className="editor-toolbar">
      <div className="editor-toolbar-left">
        <button
          className="toolbar-btn toolbar-btn-back"
          onClick={onBack}
          aria-label="Back to dashboard"
        >
          ← Back
        </button>
        <h1 className="editor-toolbar-title">{projectName}</h1>
      </div>

      <div className="editor-toolbar-right">
        {saveStatus !== 'idle' && (
          <span className={`save-status ${getSaveStatusClass()}`}>
            {getSaveStatusText()}
          </span>
        )}
        
        <button
          className="toolbar-btn toolbar-btn-save"
          onClick={onSave}
          disabled={saveStatus === 'saving'}
        >
          Save
        </button>
        
        <button
          className="toolbar-btn toolbar-btn-view3d"
          onClick={onView3D}
        >
          View in 3D
        </button>
      </div>
    </div>
  );
};

export default EditorToolbar;
