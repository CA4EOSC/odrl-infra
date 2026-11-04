export const OAUTH_CONFIG = {
    google: {
        clientId: import.meta.env.VITE_GOOGLE_CLIENT_ID || "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com",
        authUrl: "https://accounts.google.com/o/oauth2/v2/auth",
        scope: "openid email profile",
        redirectUri: import.meta.env.VITE_REDIRECT_URI ? `${import.meta.env.VITE_REDIRECT_URI}/auth/google/callback` : "http://localhost:5173/auth/google/callback"
    },
    github: {
        clientId: import.meta.env.VITE_GITHUB_CLIENT_ID || "YOUR_GITHUB_CLIENT_ID",
        authUrl: "https://github.com/login/oauth/authorize",
        scope: "read:user user:email",
        redirectUri: import.meta.env.VITE_REDIRECT_URI ? `${import.meta.env.VITE_REDIRECT_URI}/auth/github/callback` : "http://localhost:5173/auth/github/callback"
    },
    orcid: {
        clientId: import.meta.env.VITE_ORCID_CLIENT_ID || "APP-YOUR_ORCID_CLIENT_ID",
        authUrl: "https://orcid.org/oauth/authorize",
        scope: "openid /authenticate",
        redirectUri: import.meta.env.VITE_REDIRECT_URI ? `${import.meta.env.VITE_REDIRECT_URI}/auth/orcid/callback` : "http://localhost:5173/auth/orcid/callback"
    }
};
