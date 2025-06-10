<template>
  <nav class="w-full h-16 bg-white shadow">
    <div
      class="container mx-auto h-full flex items-center justify-between px-4"
    >
      <NuxtLink to="/">
        <h1 class="text-xl font-bold cursor-pointer">AudioUploadThing</h1>
      </NuxtLink>

      <div class="flex items-center gap-x-6">
        <NuxtLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          class="text-sm font-medium text-gray-500 transition-colors hover:text-gray-900"
          exact-active-class="!text-gray-900"
        >
          {{ link.label }}
        </NuxtLink>
      </div>

      <div>
        <!-- Authenticated State: Link to user's profile -->
        <NuxtLink v-if="isAuthenticated && user" :to="`/profile/${user.name}`">
          <User class="h-6 w-6 text-gray-700 hover:text-blue-600" />
        </NuxtLink>
        <!-- Unauthenticated State: Link to login page -->
        <NuxtLink v-else to="/login">
          <User class="h-6 w-6 text-gray-700 hover:text-blue-600" />
        </NuxtLink>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { User } from "lucide-vue-next";
// 1. Import the composable to get auth state
import { useAuth } from "@/composables/useAuth";

// 2. Get the reactive state and user data from the composable
const { isAuthenticated, user } = useAuth();

// 3. The hardcoded `isAuthenticated` line has been removed.

interface NavLink {
  label: string;
  to: string;
}

const navLinks: NavLink[] = [
  { label: "Przeglądaj", to: "/" },
  { label: "Prześlij plik", to: "/upload" },
];
</script>