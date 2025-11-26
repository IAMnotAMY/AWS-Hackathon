// Alternative token format - try this if Bearer doesn't work
// Replace line: config.headers.Authorization = `Bearer ${idToken}`;
// With: config.headers.Authorization = idToken;

// Or if your API Gateway expects a different header:
// config.headers['x-api-key'] = idToken;
// Or: config.headers['authorizationToken'] = idToken;
