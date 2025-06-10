<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuth } from "@/composables/useAuth";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import AudioFileCard from "@/components/AudioFileCard.vue";

// Define the interface for our audio files, matching the API response
interface ApiAudioFile {
  id: number;
  uuid: string;
  title: string;
  uploaded_at: string;
  file: string;
  description: string | null;
  is_public: boolean;
  likes_count: number;
  dislikes_count: number;
  user_vote: "like" | "dislike" | null;
  uploader: string | null;
  views: number;
  tags: string[];
}
interface AudioFile extends ApiAudioFile {}

// Use Nuxt's built-in route protection middleware
definePageMeta({
  middleware: "auth",
});

const { user, isAuthenticated } = useAuth();
const { $api } = useNuxtApp();
const config = useRuntimeConfig();

const uploadedFiles = ref<AudioFile[]>([]);
const likedFiles = ref<AudioFile[]>([]);
const loadingUploaded = ref(true);
const loadingLiked = ref(true);
const errorUploaded = ref<string | null>(null);
const errorLiked = ref<string | null>(null);
const playedFiles = ref(new Set<string>());

// Utility to get the first letter of a name for the avatar
const getAvatarFallback = (name: string | undefined | null) => {
  return name && name.length > 0 ? name.charAt(0).toUpperCase() : "U";
};

// Function to construct the full media URL
const processFiles = (files: ApiAudioFile[]): AudioFile[] => {
  return files.map((file) => ({
    ...file,
    file: new URL(file.file, config.public.mediaRoot).href,
  }));
};

// Fetch files uploaded by the user
const fetchUploadedFiles = async () => {
  loadingUploaded.value = true;
  errorUploaded.value = null;
  try {
    const response = await $api.get<ApiAudioFile[]>("/api/audio/");
    uploadedFiles.value = processFiles(response.data);
  } catch (e: any) {
    console.error("Error fetching uploaded files:", e);
    errorUploaded.value = "Nie udało się wczytać Twoich plików.";
  } finally {
    loadingUploaded.value = false;
  }
};

// Fetch files liked by the user
const fetchLikedFiles = async () => {
  loadingLiked.value = true;
  errorLiked.value = null;
  try {
    const response = await $api.get<ApiAudioFile[]>("/api/audio/liked/");
    likedFiles.value = processFiles(response.data);
  } catch (e: any) {
    console.error("Error fetching liked files:", e);
    errorLiked.value = "Nie udało się wczytać polubionych plików.";
  } finally {
    loadingLiked.value = false;
  }
};

onMounted(() => {
  if (isAuthenticated.value) {
    fetchUploadedFiles();
    fetchLikedFiles();
  }
});

// Navigate to the password reset page
const resetPassword = () => {
  navigateTo("/request-password/"); // Assuming this is the correct route
};

// Optimistic UI for voting
const handleVote = async (payload: {
  file: AudioFile;
  voteType: "like" | "dislike";
}) => {
  const { file, voteType } = payload;
  if (!isAuthenticated.value) {
    navigateTo("/login");
    return;
  }

  // Find the file in both lists to keep them in sync
  const fileInUploaded = uploadedFiles.value.find((f) => f.uuid === file.uuid);
  const fileInLiked = likedFiles.value.find((f) => f.uuid === file.uuid);
  const filesToUpdate = [fileInUploaded, fileInLiked].filter(Boolean) as AudioFile[];

  if (filesToUpdate.length === 0) return;

  const originalStates = filesToUpdate.map((f) => ({
    user_vote: f.user_vote,
    likes_count: f.likes_count,
    dislikes_count: f.dislikes_count,
  }));

  // Optimistic update
  filesToUpdate.forEach((f) => {
    if (f.user_vote === voteType) {
      f.user_vote = null;
      if (voteType === "like") f.likes_count--;
      else f.dislikes_count--;
    } else {
      if (f.user_vote === "like") f.likes_count--;
      if (f.user_vote === "dislike") f.dislikes_count--;
      f.user_vote = voteType;
      if (voteType === "like") f.likes_count++;
      else f.dislikes_count++;
    }
  });

  try {
    await $api.post(`/api/audio/${file.uuid}/like/`, {
      is_liked: voteType === "like",
    });
  } catch (err) {
    console.error("Failed to save vote:", err);
    // Revert on error
    filesToUpdate.forEach((f, index) => {
      Object.assign(f, originalStates[index]);
    });
  }
};

// Handle view count increment
const handlePlay = async (file: AudioFile) => {
  if (playedFiles.value.has(file.uuid)) return;
  playedFiles.value.add(file.uuid);

  try {
    const response = await $api.get<AudioFile>(`/api/audio/${file.uuid}/`);
    const updatedViews = response.data.views;
    const fileInUploaded = uploadedFiles.value.find((f) => f.uuid === file.uuid);
    const fileInLiked = likedFiles.value.find((f) => f.uuid === file.uuid);
    if (fileInUploaded) fileInUploaded.views = updatedViews;
    if (fileInLiked) fileInLiked.views = updatedViews;
  } catch (err) {
    console.error("Failed to increment view count:", err);
    playedFiles.value.delete(file.uuid);
  }
};
</script>

<template>
  <div v-if="isAuthenticated && user" class="container mx-auto p-4">
    <!-- User Info Panel -->
    <div class="flex justify-center mb-12">
      <div
        class="flex items-center gap-6 p-6 border rounded-lg shadow-sm bg-card text-card-foreground w-full max-w-lg"
      >
        <Avatar class="h-20 w-20">
          <AvatarFallback class="text-3xl">{{
            getAvatarFallback(user.name)
          }}</AvatarFallback>
        </Avatar>
        <div>
          <h1 class="text-2xl font-bold">{{ user.name }}</h1>
          <p class="text-muted-foreground">{{ user.email }}</p>
          <Button @click="resetPassword" variant="link" class="p-0 mt-2">
            Zresetuj hasło
          </Button>
        </div>
      </div>
    </div>

    <!-- Uploaded and Liked Files Sections -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-x-8 gap-y-12">
      <!-- Left Section: Uploaded Files -->
      <div>
        <h2 class="text-2xl font-bold mb-4">Twoje pliki</h2>
        <div v-if="loadingUploaded">Wczytywanie...</div>
        <div v-else-if="errorUploaded" class="text-red-500">
          {{ errorUploaded }}
        </div>
        <div v-else-if="uploadedFiles.length === 0" class="text-gray-500">
          Nie masz jeszcze żadnych plików.
        </div>
        <div v-else class="grid gap-4">
          <AudioFileCard
            v-for="file in uploadedFiles"
            :key="'uploaded-' + file.id"
            :audio-file="file"
            @vote="handleVote"
            @play="handlePlay"
          />
        </div>
      </div>

      <!-- Right Section: Liked Files -->
      <div>
        <h2 class="text-2xl font-bold mb-4">Polubione pliki</h2>
        <div v-if="loadingLiked">Wczytywanie...</div>
        <div v-else-if="errorLiked" class="text-red-500">
          {{ errorLiked }}
        </div>
        <div v-else-if="likedFiles.length === 0" class="text-gray-500">
          Nie polubiłeś jeszcze żadnych plików.
        </div>
        <div v-else class="grid gap-4">
          <AudioFileCard
            v-for="file in likedFiles"
            :key="'liked-' + file.id"
            :audio-file="file"
            @vote="handleVote"
            @play="handlePlay"
          />
        </div>
      </div>
    </div>
  </div>
</template>