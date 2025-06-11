<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { useWindowFocus, useClipboard } from "@vueuse/core";
import { Button } from "@/components/ui/button";
import { X } from "lucide-vue-next";
import AudioCard from "@/components/AudioCard.vue";

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
interface ApiTag {
  id: number;
  name: string;
}

const latestAudioFiles = ref<AudioFile[]>([]);
const loading = ref(true);
const loadingMore = ref(false);
const error = ref<string | null>(null);
const page = ref(1);
const hasMore = ref(true);
const playedFiles = ref(new Set<string>());
const activeCommentSection = ref<string | null>(null);
const activeTags = ref<string[]>([]);
const allTags = ref<string[]>([]);
const tagsLoading = ref(true);

const sourceLinkToCopy = ref("");
const lastCopiedUuid = ref<string | null>(null);
const { copy, copied } = useClipboard({ source: sourceLinkToCopy });

const { $api } = useNuxtApp();
const { isAuthenticated } = useAuth();
const isFocused = useWindowFocus();

const handleCopyLink = (uuid: string) => {
  const link = `${window.location.origin}/audio/${uuid}`;
  sourceLinkToCopy.value = link;
  copy();
  lastCopiedUuid.value = uuid;
};

const toggleCommentSection = (uuid: string) => {
  if (!isAuthenticated.value) {
    navigateTo("/login");
    return;
  }
  if (activeCommentSection.value === uuid) {
    activeCommentSection.value = null;
  } else {
    activeCommentSection.value = uuid;
  }
};

const handleTagClick = (tag: string) => {
  const tagIndex = activeTags.value.indexOf(tag);
  if (tagIndex > -1) {
    activeTags.value.splice(tagIndex, 1);
  } else {
    activeTags.value.push(tag);
  }
  resetAndFetch();
};

const clearAllTags = () => {
  if (activeTags.value.length > 0) {
    activeTags.value = [];
    resetAndFetch();
  }
};

const handleVote = async (
  file: AudioFile,
  voteType: "like" | "dislike"
) => {
  if (!isAuthenticated.value) {
    navigateTo("/login");
    return;
  }
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
    file.user_vote = originalVote;
    file.likes_count = originalLikes;
    file.dislikes_count = originalDislikes;
  }
};

const handlePlay = async (file: AudioFile) => {
  if (playedFiles.value.has(file.uuid)) {
    return;
  }
  playedFiles.value.add(file.uuid);
  try {
    const response = await $api.get<AudioFile>(`/api/audio/${file.uuid}/`);
    file.views = response.data.views;
  } catch (err) {
    console.error("Failed to increment view count:", err);
    playedFiles.value.delete(file.uuid);
  }
};

const resetAndFetch = () => {
  latestAudioFiles.value = [];
  page.value = 1;
  hasMore.value = true;
  playedFiles.value.clear();
  activeCommentSection.value = null;
  fetchAudioFiles();
};

const fetchAudioFiles = async () => {
  if (!hasMore.value) return;
  if (page.value === 1) {
    loading.value = true;
  } else {
    loadingMore.value = true;
  }
  error.value = null;
  const config = useRuntimeConfig();

  const params = new URLSearchParams();
  params.append("page", page.value.toString());
  activeTags.value.forEach((tag) => {
    params.append("tags", tag);
  });

  const endpoint = `/api/audio/latest/?${params.toString()}`;

  try {
    const response = await $api.get<{
      results: ApiAudioFile[];
      has_more: boolean;
    }>(endpoint);

    const data = response.data;
    const newFiles = data.results.map((file) => {
      const fullFileUrl = new URL(file.file, config.public.mediaRoot).href;
      return { ...file, file: fullFileUrl };
    });
    latestAudioFiles.value.push(...newFiles);
    hasMore.value = data.has_more;
    page.value++;
  } catch (e: any) {
    error.value = `Error fetching audio files: ${e.message}`;
    console.error("Fetch error:", e);
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
};

const fetchAllTags = async () => {
  tagsLoading.value = true;
  try {
    const response = await $api.get<ApiTag[]>("/api/audio/tags/");
    allTags.value = response.data.map((tag) => tag.name);
  } catch (e) {
    console.error("Failed to fetch all tags:", e);
  } finally {
    tagsLoading.value = false;
  }
};

watch(isFocused, (isNowFocused) => {
  if (isNowFocused && !loading.value) {
    activeTags.value = [];
    resetAndFetch();
  }
});

watch(copied, (isCopied) => {
  if (!isCopied) {
    lastCopiedUuid.value = null;
  }
});

onMounted(() => {
  fetchAudioFiles();
  fetchAllTags();
});
</script>

<template>
  <div>
    <h2 class="text-2xl font-bold mb-4 text-center">Przeglądaj pliki!</h2>

    <div v-if="tagsLoading" class="text-center text-gray-500 my-4">
      Wczytywanie tagów...
    </div>
    <div
      v-else-if="allTags.length > 0"
      class="mb-6 flex flex-wrap justify-center gap-2 border-b pb-6"
    >
      <Button
        v-for="tag in allTags"
        :key="tag"
        :variant="activeTags.includes(tag) ? 'default' : 'outline'"
        size="sm"
        @click="handleTagClick(tag)"
      >
        {{ tag }}
      </Button>
    </div>

    <div
      v-if="activeTags.length > 0 && !loading"
      class="mb-4 flex items-center justify-between gap-4 p-3 bg-muted rounded-lg"
    >
      <div class="flex items-center gap-2 flex-wrap">
        <p class="text-sm text-muted-foreground">Filtrowanie po tagach:</p>
        <div
          v-for="tag in activeTags"
          :key="tag"
          class="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-primary text-primary-foreground"
        >
          {{ tag }}
        </div>
      </div>
      <Button variant="ghost" size="sm" @click="clearAllTags">
        <X class="h-4 w-4 mr-2" />
        Wyczyść filtry
      </Button>
    </div>

    <div v-if="loading" class="text-center">Wczytywanie...</div>
    <div v-else-if="error" class="text-center text-red-500">
      Error : {{ error }}
    </div>
    <div v-else>
      <div
        v-if="latestAudioFiles.length === 0"
        class="text-center text-gray-500"
      >
        Brak plikow
      </div>
      <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <AudioCard
          v-for="audioFile in latestAudioFiles"
          :key="audioFile.id"
          :audio-file="audioFile"
          :is-authenticated="isAuthenticated"
          :active-comment-section="activeCommentSection"
          :active-tags="activeTags"
          :is-link-copied="lastCopiedUuid === audioFile.uuid"
          @vote="handleVote"
          @play="handlePlay"
          @toggle-comments="toggleCommentSection"
          @tag-click="handleTagClick"
          @copy-link="handleCopyLink"
        />
      </div>
      <div class="mt-8 text-center">
        <Button
          v-if="hasMore && !loadingMore"
          @click="fetchAudioFiles"
          variant="outline"
        >
          Więcej
        </Button>
        <p v-if="loadingMore" class="text-gray-500">Wczytywanie...</p>
        <p
          v-if="!hasMore && latestAudioFiles.length > 0"
          class="text-gray-500"
        >
          Brak dalszych plikow
        </p>
      </div>
    </div>
  </div>
</template>