export const DevModeBanner = () => {
  const isConfigured = 
    import.meta.env.VITE_USER_POOL_ID && 
    !import.meta.env.VITE_USER_POOL_ID.includes('XXXX');

  if (isConfigured) {
    return null;
  }

  return (
    <div style={{
      backgroundColor: '#fff3cd',
      border: '1px solid #ffc107',
      borderRadius: '4px',
      padding: '12px 16px',
      marginBottom: '20px',
      fontSize: '14px',
      color: '#856404',
    }}>
      <strong>⚠️ Development Mode:</strong> AWS Cognito is not configured. 
      Deploy the infrastructure and set environment variables to enable authentication.
      <details style={{ marginTop: '8px', fontSize: '13px' }}>
        <summary style={{ cursor: 'pointer' }}>Setup Instructions</summary>
        <ol style={{ marginTop: '8px', paddingLeft: '20px' }}>
          <li>Deploy infrastructure: <code>cd infrastructure && npm run deploy</code></li>
          <li>Copy <code>frontend/.env.example</code> to <code>frontend/.env</code></li>
          <li>Add UserPoolId and UserPoolClientId from CDK outputs</li>
          <li>Restart the dev server</li>
        </ol>
      </details>
    </div>
  );
};

export default DevModeBanner;
