export default defineNuxtRouteMiddleware((to, from) => {
  // The useAuth composable provides the authentication state.
  const { isAuthenticated } = useAuth();

  // If the user is not authenticated, redirect them to the login page.
  if (!isAuthenticated.value) {
    return navigateTo("/login");
  }

  // If the user is authenticated, allow them to proceed to the requested page.
});