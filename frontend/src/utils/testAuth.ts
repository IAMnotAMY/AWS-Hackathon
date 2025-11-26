import { fetchAuthSession } from 'aws-amplify/auth';
import axios from 'axios';

export async function testAuthSetup() {
  console.log('=== AUTH SETUP TEST ===');
  
  try {
    // Get session
    const session = await fetchAuthSession();
    const idToken = session.tokens?.idToken;
    const accessToken = session.tokens?.accessToken;
    
    console.log('\n1. TOKEN INFO:');
    console.log('ID Token exists:', !!idToken);
    console.log('Access Token exists:', !!accessToken);
    
    if (idToken) {
      console.log('\n2. ID TOKEN PAYLOAD:');
      console.log('- sub (user ID):', idToken.payload.sub);
      console.log('- email:', idToken.payload.email);
      console.log('- cognito:username:', idToken.payload['cognito:username']);
      console.log('- aud (client ID):', idToken.payload.aud);
      console.log('- iss (issuer):', idToken.payload.iss);
      console.log('- token_use:', idToken.payload.token_use);
      
      // Extract user pool ID from issuer
      const issuer = idToken.payload.iss as string;
      const userPoolId = issuer.split('/').pop();
      console.log('- User Pool ID from token:', userPoolId);
      console.log('- Expected User Pool ID:', import.meta.env.VITE_USER_POOL_ID);
      console.log('- MATCH:', userPoolId === import.meta.env.VITE_USER_POOL_ID);
    }
    
    if (accessToken) {
      console.log('\n3. ACCESS TOKEN PAYLOAD:');
      console.log('- sub (user ID):', accessToken.payload.sub);
      console.log('- client_id:', accessToken.payload.client_id);
      console.log('- token_use:', accessToken.payload.token_use);
    }
    
    // Test API call with different token formats
    const apiUrl = import.meta.env.VITE_API_URL + '/project';
    console.log('\n4. TESTING API CALLS:');
    console.log('API URL:', apiUrl);
    
    // Test 1: ID Token with Bearer
    console.log('\n  Test 1: ID Token with Bearer prefix');
    try {
      const response1 = await axios.get(apiUrl, {
        headers: {
          'Authorization': `Bearer ${idToken?.toString()}`,
          'Content-Type': 'application/json'
        }
      });
      console.log('  ✅ SUCCESS:', response1.status, response1.data);
    } catch (error: any) {
      console.log('  ❌ FAILED:', error.response?.status, error.response?.data || error.message);
    }
    
    // Test 2: ID Token without Bearer
    console.log('\n  Test 2: ID Token without Bearer prefix');
    try {
      const response2 = await axios.get(apiUrl, {
        headers: {
          'Authorization': idToken?.toString() || '',
          'Content-Type': 'application/json'
        }
      });
      console.log('  ✅ SUCCESS:', response2.status, response2.data);
    } catch (error: any) {
      console.log('  ❌ FAILED:', error.response?.status, error.response?.data || error.message);
    }
    
    // Test 3: Access Token with Bearer
    console.log('\n  Test 3: Access Token with Bearer prefix');
    try {
      const response3 = await axios.get(apiUrl, {
        headers: {
          'Authorization': `Bearer ${accessToken?.toString()}`,
          'Content-Type': 'application/json'
        }
      });
      console.log('  ✅ SUCCESS:', response3.status, response3.data);
    } catch (error: any) {
      console.log('  ❌ FAILED:', error.response?.status, error.response?.data || error.message);
    }
    
    console.log('\n=== TEST COMPLETE ===');
    
  } catch (error) {
    console.error('Error during auth test:', error);
  }
}

// Add to window for easy access in console
if (typeof window !== 'undefined') {
  (window as any).testAuth = testAuthSetup;
}
