export async function syncTokenWithBackend(
  accessToken: string, 
  refreshToken?: string, 
  idToken?: string, 
  expiresAt?: number
): Promise<string | null> {
  try {
    console.log('Syncing tokens with backend...');
    const backendUrl = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
    
    // Create a controller with a short timeout to prevent blocking
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
    
    try {
      const response = await fetch(`${backendUrl}/api/v1/auth/google/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: idToken,
          access_token: accessToken,
          refresh_token: refreshToken,
          expires_in: expiresAt ? (expiresAt - Math.floor(Date.now() / 1000)) : 3600,
        }),
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      
      if (response.ok) {
        const data = await response.json();
        console.log('Backend token received:', data.access_token ? 'Yes' : 'No');
        return data.access_token;
      } else {
        const errorText = await response.text();
        console.error('Backend auth failed:', response.status, errorText);
        return null;
      }
    } catch (fetchError: unknown) {
      clearTimeout(timeoutId);
      // Only log legitimate errors, not aborts if we want to be quiet about timeouts
      if (fetchError instanceof Error && fetchError.name !== 'AbortError') {
        throw fetchError;
      } else if (fetchError instanceof Error && fetchError.name === 'AbortError') {
         console.warn('Backend sync timed out');
      }
      return null;
    }
  } catch (error) {
    console.error('Failed to sync with backend (non-critical):', error);
    // Continue anyway - backend sync is optional for initial login
    return null;
  }
}
