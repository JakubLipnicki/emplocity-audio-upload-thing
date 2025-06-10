import axios from "axios";

export default defineNuxtPlugin((nuxtApp) => {
  // Get the runtime config, which is valid inside a plugin
  const config = useRuntimeConfig();

  // Create the axios instance
  const api = axios.create({
    baseURL: config.public.apiRoot,
    withCredentials: true,
  });

  // --- CSRF Token Interceptor ---
  // This logic remains the same, but lives inside the plugin now.
  api.interceptors.request.use((config) => {
    // We need a browser environment to access document.cookie
    if (process.server) {
      return config;
    }

    function getCookie(name: string): string | null {
      const value = `; ${document.cookie}`;
      const parts = value.split(`; ${name}=`);
      if (parts.length === 2) return parts.pop()?.split(";").shift() || null;
      return null;
    }

    const csrfToken = getCookie("csrftoken");
    if (csrfToken) {
      config.headers["X-CSRFToken"] = csrfToken;
    }
    return config;
  });
  // --- End Interceptor ---

  // Provide the configured instance to the rest of the app
  return {
    provide: {
      api: api,
    },
  };
});