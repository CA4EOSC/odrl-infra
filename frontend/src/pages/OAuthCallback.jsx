import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';

export default function OAuthCallback() {
  const { provider } = useParams();

  useEffect(() => {
    // Parse token from hash (implicit flow) or search params
    const hash = new URLSearchParams(window.location.hash.substring(1));
    const search = new URLSearchParams(window.location.search);
    
    let token = hash.get('id_token') || hash.get('access_token') || search.get('access_token');
    let orcid = search.get('orcid'); // Sometimes ORCID returns it in search params

    if (token) {
      if (window.opener) {
        window.opener.postMessage({
          type: 'OAUTH_CALLBACK',
          provider,
          token,
          orcid
        }, window.location.origin);
        window.close();
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
