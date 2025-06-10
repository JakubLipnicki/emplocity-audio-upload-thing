// frontend/composables/useAuth.ts

import { ref, computed } from "vue";

// Define a type for our user object for better type safety
interface User {
  id: number;
  name: string;
  email: string;
  // Add any other fields your UserSerializer returns
}

const user = ref<User | null>(null);

export const useAuth = () => {
  // useNuxtApp() gives us access to the app context, including our provided helpers
  const { $api } = useNuxtApp();

  const login = async (credentials: { email: string; password: any }) => {
    // Use the provided $api instance
    await $api.post("/api/login", credentials);
    await fetchUser();
  };

  const fetchUser = async () => {
    try {
      // Use the provided $api instance
      const response = await $api.get<User>("/api/user");
      user.value = response.data;
    } catch (error) {
      console.error("Failed to fetch user:", error);
      user.value = null;
    }
  };

  const logout = async () => {
    // Use the provided $api instance
    await $api.post("/api/logout");
    user.value = null;
    await navigateTo("/login");
  };

  return {
    user,
    isAuthenticated: computed(() => !!user.value),
    login,
    fetchUser,
    logout,
  };
};