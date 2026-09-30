import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';

export default function OAuthCallback() {
  const { provider } = useParams();

  useEffect(() => {
    // Parse token from hash (implicit flow) or search params
    const hash = new URLSearchParams(window.location.hash.substring(1));
    const search = new URLSearchParams(window.location.search);

    // id_token is the JWT (contains sub = ORCID iD); access_token is for API calls
    const idToken = hash.get('id_token') || search.get('id_token');
    const accessToken = hash.get('access_token') || search.get('access_token');
    let token = idToken || accessToken;
    let orcid = search.get('orcid'); // Sometimes ORCID returns it in search params

    if (token) {
      // Always save to localStorage as a robust fallback
      localStorage.setItem('oauth_fallback', JSON.stringify({ provider, token, accessToken, orcid }));

      if (window.opener && window.opener !== window) {
        window.opener.postMessage({
          type: 'OAUTH_CALLBACK',
          provider,
          token,          // id_token JWT (used to decode name/ORCID iD)
          accessToken,    // raw access_token (used for API calls)
          orcid
        }, window.location.origin);
        window.close();
        
        // If window didn't close after 1 second, fallback to redirect
        setTimeout(() => {
          window.location.href = '/vcs';
        }, 1000);
      } else {
        // Fallback if not opened in a popup
        window.location.href = '/vcs';
      }
    } else {
      console.error('No token found in URL');
      if (window.opener) {
        window.opener.postMessage({ type: 'OAUTH_ERROR', error: 'No token found' }, window.location.origin);
        window.close();
      }
    }
  }, [provider]);

  return (
    <div className="flex h-screen items-center justify-center">
      <div className="text-center">
        <h2 className="text-xl font-semibold mb-2">Authenticating...</h2>
        <p className="text-gray-500">Please wait while we complete the login process.</p>
      </div>
    </div>
  );
}
