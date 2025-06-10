<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { useWindowFocus } from "@vueuse/core";
import {
  Card,
  CardContent,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  ThumbsUp,
  ThumbsDown,
  Globe,
  Lock,
  Eye,
  MessageCircle,
} from "lucide-vue-next";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import CommentSection from "@/components/CommentSection.vue";

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
}
interface AudioFile extends ApiAudioFile {}

const latestAudioFiles = ref<AudioFile[]>([]);
const loading = ref(true);
const loadingMore = ref(false);
const error = ref<string | null>(null);
const page = ref(1);
const hasMore = ref(true);
const playedFiles = ref(new Set<string>());
const activeCommentSection = ref<string | null>(null);

const { $api } = useNuxtApp();
const { isAuthenticated } = useAuth();

const isFocused = useWindowFocus();

// --- MODIFIED FUNCTION ---
const toggleCommentSection = (uuid: string) => {
  // First, check if the user is logged in.
  if (!isAuthenticated.value) {
    // If not, redirect to the login page and stop.
    navigateTo("/login");
    return;
  }

  // If they are logged in, proceed with the original toggle logic.
  if (activeCommentSection.value === uuid) {
    activeCommentSection.value = null; // Close if already open
  } else {
    activeCommentSection.value = uuid; // Open new one
  }
};

watch(isFocused, (isNowFocused) => {
  if (isNowFocused && !loading.value) {
    latestAudioFiles.value = [];
    page.value = 1;
    hasMore.value = true;
    playedFiles.value.clear();
    activeCommentSection.value = null;
    fetchAudioFiles();
  }
});

const fetchAudioFiles = async () => {
  if (!hasMore.value) return;
  if (page.value === 1) {
    loading.value = true;
  } else {
    loadingMore.value = true;
  }
  error.value = null;
  const config = useRuntimeConfig();
  try {
    const response = await $api.get<{
      results: ApiAudioFile[];
      has_more: boolean;
    }>(`/api/audio/latest/?page=${page.value}`);
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
onMounted(() => {
  fetchAudioFiles();
});
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
const formatDate = (dateString: string) => {
  const options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "numeric",
    day: "numeric",
  };
  return new Date(dateString).toLocaleDateString(undefined, options);
};
</script>

<template>
  <div>
    <h2 class="text-2xl font-bold mb-4">Przeglądaj pliki!</h2>
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
        <Card v-for="audioFile in latestAudioFiles" :key="audioFile.id">
          <CardContent class="p-6">
            <div class="flex justify-between items-start gap-2">
              <CardTitle>{{ audioFile.title }}</CardTitle>
              <TooltipProvider :delay-duration="100">
                <Tooltip>
                  <TooltipTrigger>
                    <Globe
                      v-if="audioFile.is_public"
                      class="h-5 w-5 text-gray-500"
                    />
                    <Lock v-else class="h-5 w-5 text-gray-500" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{{ audioFile.is_public ? "Public" : "Private" }}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <CardDescription class="mb-2 mt-1 text-sm">
              Author: {{ audioFile.uploader || "Anonim" }}
            </CardDescription>
            <CardDescription class="mb-2 mt-1">
              Opublikowane: {{ formatDate(audioFile.uploaded_at) }}
            </CardDescription>
            <CardDescription v-if="audioFile.description" class="mb-2">
              Opis: {{ audioFile.description }}
            </CardDescription>
            <CardDescription v-else class="mb-2 text-sm text-gray-500">
              Opis: Brak opisu
            </CardDescription>
            <audio
              controls
              :src="audioFile.file"
              class="w-full mt-4"
              @play="handlePlay(audioFile)"
            >
              Your browser does not support the audio element.
            </audio>
            <div
              class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-start"
            >
              <div class="flex items-center space-x-6">
                <div class="flex items-center space-x-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    @click="handleVote(audioFile, 'like')"
                    :class="{ 'text-blue-500': audioFile.user_vote === 'like' }"
                    aria-label="Like"
                  >
                    <ThumbsUp
                      class="h-5 w-5"
                      :class="{
                        'fill-blue-500 dark:fill-blue-700 opacity-50':
                          audioFile.user_vote === 'like',
                      }"
                    />
                  </Button>
                  <span class="text-sm min-w-[20px] text-center">{{
                    audioFile.likes_count
                  }}</span>
                </div>
                <div class="flex items-center space-x-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    @click="handleVote(audioFile, 'dislike')"
                    :class="{
                      'text-red-500': audioFile.user_vote === 'dislike',
                    }"
                    aria-label="Dislike"
                  >
                    <ThumbsDown
                      class="h-5 w-5"
                      :class="{
                        'fill-red-500 dark:fill-red-700 opacity-50':
                          audioFile.user_vote === 'dislike',
                      }"
                    />
                  </Button>
                  <span class="text-sm min-w-[20px] text-center">{{
                    audioFile.dislikes_count
                  }}</span>
                </div>
                <div class="flex items-center space-x-1 text-gray-500">
                  <Eye class="h-5 w-5" />
                  <span class="text-sm min-w-[20px] text-center">{{
                    audioFile.views
                  }}</span>
                </div>
              </div>
              <div class="flex-grow flex justify-end">
                <Button
                  variant="ghost"
                  size="icon"
                  @click="toggleCommentSection(audioFile.uuid)"
                  aria-label="Toggle Comments"
                >
                  <MessageCircle class="h-5 w-5" />
                </Button>
              </div>
            </div>
            <CommentSection
              v-if="activeCommentSection === audioFile.uuid"
              :audio-file-uuid="audioFile.uuid"
            />
          </CardContent>
        </Card>
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