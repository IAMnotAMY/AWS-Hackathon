// Utility to verify AWS configuration is loaded
export const verifyAwsConfig = () => {
  const userPoolId = import.meta.env.VITE_USER_POOL_ID;
  const userPoolClientId = import.meta.env.VITE_USER_POOL_CLIENT_ID;
  
  const isConfigured = 
    userPoolId && 
    userPoolClientId && 
    !userPoolId.includes('XXXX') &&
    !userPoolClientId.includes('XXXX');
  
  if (isConfigured) {
    console.log('✅ AWS Cognito configured successfully');
    console.log('User Pool ID:', userPoolId);
    console.log('Region:', import.meta.env.VITE_AWS_REGION || 'us-east-1');
  } else {
    console.warn('⚠️ AWS Cognito not configured - running in development mode');
  }
  
  return isConfigured;
};
