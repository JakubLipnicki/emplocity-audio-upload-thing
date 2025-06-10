// frontend/composables/useAuth.ts

import { ref, computed } from "vue";
import { useNuxtApp } from "#app";

interface User {
  id: number;
  name: string;
  email: string;
}

// This ref will hold the token we get from the login response
const accessToken = ref<string | null>(null);
const user = ref<User | null>(null);

export const useAuth = () => {
  const { $api } = useNuxtApp();
  const isAuthenticated = computed(() => !!user.value);

  const login = async (credentials: { email: string; password: any }) => {
    // --- THIS IS THE FIX ---
    // 1. Call the login endpoint and get the response
    const response = await $api.post("/api/login", credentials);

    // 2. If the response contains an access_token, store it
    if (response.data && response.data.access_token) {
      accessToken.value = response.data.access_token;
    }
    // --- END FIX ---

    // 3. Still call fetchUser to get the user details and confirm the session
    await fetchUser();
  };

  const fetchUser = async () => {
    try {
      const response = await $api.get<User>("/api/user");
      user.value = response.data;
    } catch (error) {
      console.error("Failed to fetch user:", error);
      user.value = null;
      accessToken.value = null; // Clear token if fetching user fails
    }
  };

  const logout = async () => {
    await $api.post("/api/logout");
    user.value = null;
    accessToken.value = null; // Clear token on logout
    await navigateTo("/login");
  };

  return {
    user,
    accessToken, // Expose the token for other components to use
    isAuthenticated,
    login,
    fetchUser,
    logout,
  };
};