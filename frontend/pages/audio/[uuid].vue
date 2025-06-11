<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import AudioCard from "@/components/AudioCard.vue";
import { useAuth } from "@/composables/useAuth";

// Define interfaces locally for this page
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

const route = useRoute();
const { $api } = useNuxtApp();
const { isAuthenticated } = useAuth();

const audioFile = ref<AudioFile | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const activeCommentSection = ref<string | null>(null);

const fetchAudioFile = async () => {
  const uuid = route.params.uuid;
  loading.value = true;
  error.value = null;
  const config = useRuntimeConfig();

  try {
    const response = await $api.get<ApiAudioFile>(`/api/audio/${uuid}/`);
    const fileData = response.data;
    // Construct full URL for the audio file
    const fullFileUrl = new URL(fileData.file, config.public.mediaRoot).href;
    audioFile.value = { ...fileData, file: fullFileUrl };
  } catch (e: any) {
    error.value = "Nie można załadować pliku. Być może został usunięty.";
    console.error("Fetch error:", e);
  } finally {
    loading.value = false;
  }
};

// Re-implement handlers for the single card on this page
const handleVote = async (
  file: AudioFile,
  voteType: "like" | "dislike"
) => {
  if (!isAuthenticated.value) {
    navigateTo("/login");
    return;
  }
  // Optimistic UI update logic
  const originalVote = file.user_vote;
  const originalLikes = file.likes_count;
  const originalDislikes = file.dislikes_count;
  if (file.user_vote === voteType) {
    file.user_vote = null;
    if (voteType === "like") file.likes_count--;
    else file.dislikes_count--;
  } else {
    if (file.user_vote === "like") file.likes_count--;
    if (file.user_vote === "dislike") file.dislikes_count--;
    file.user_vote = voteType;
    if (voteType === "like") file.likes_count++;
    else file.dislikes_count++;
  }
  try {
    await $api.post(`/api/audio/${file.uuid}/like/`, {
      is_liked: voteType === "like",
    });
  } catch (err) {
    console.error("Failed to save vote:", err);
    // Revert on error
    file.user_vote = originalVote;
    file.likes_count = originalLikes;
    file.dislikes_count = originalDislikes;
  }
};

// The play handler is not needed here as the view count is incremented on page load
const handlePlay = () => {};

const toggleCommentSection = (uuid: string) => {
  if (!isAuthenticated.value) {
    navigateTo("/login");
    return;
  }
  activeCommentSection.value =
    activeCommentSection.value === uuid ? null : uuid;
};

onMounted(() => {
  fetchAudioFile();
});
</script>

<template>
  <div class="flex items-center justify-center min-h-[calc(100vh-200px)] p-4">
    <div v-if="loading" class="text-center">Wczytywanie...</div>
    <div v-else-if="error" class="text-center text-red-500">
      {{ error }}
    </div>
    <div v-else-if="audioFile" class="w-full max-w-2xl">
      <AudioCard
        :audio-file="audioFile"
        :is-authenticated="isAuthenticated"
        :active-comment-section="activeCommentSection"
        @vote="handleVote"
        @play="handlePlay"
        @toggle-comments="toggleCommentSection"
      />
    </div>
  </div>
</template>