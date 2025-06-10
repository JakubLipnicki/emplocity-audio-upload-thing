<script setup lang="ts">
import { ref, onMounted } from "vue";
import {
  Card,
  CardContent,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
// --- 1. FIX THE ICON IMPORT ---
import { ThumbsUp, ThumbsDown, Globe, Lock } from "lucide-vue-next"; // Replaced GlobeOff with Lock
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

// --- Interfaces (no changes) ---
interface ApiAudioFile {
  id: number;
  uuid: string;
  title: string;
  uploaded_at: string;
  file: string;
  description: string | null;
  is_public: boolean; // We will use this field
  likes_count: number;
  dislikes_count: number;
  user_vote: "like" | "dislike" | null;
}
// ... other interfaces ...
interface AudioFile extends ApiAudioFile {}

// --- All other <script setup> logic remains exactly the same ---
const latestAudioFiles = ref<AudioFile[]>([]);
const loading = ref(true);
const loadingMore = ref(false);
const error = ref<string | null>(null);
const page = ref(1);
const hasMore = ref(true);
const { $api } = useNuxtApp();
const { isAuthenticated } = useAuth();

const fetchAudioFiles = async () => {
  if (!hasMore.value) return;
  if (page.value === 1) loading.value = true;
  else loadingMore.value = true;
  error.value = null;
  const config = useRuntimeConfig();
  const apiRoot = config.public.apiRoot;
  try {
    const response = await $api.get<PaginatedResponse>(
      `/api/audio/latest/?page=${page.value}`
    );
    const data = response.data;
    const newFiles = data.results.map((file) => {
      const fullFileUrl = new URL(file.file, apiRoot).href;
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
    <h2 class="text-2xl font-bold mb-4">Latest</h2>
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
            <!-- --- 2. WRAP TITLE AND ICON IN A FLEX CONTAINER --- -->
            <div class="flex justify-between items-start gap-2">
              <CardTitle>{{ audioFile.title }}</CardTitle>

              <!-- --- 3. ADD THE TOOLTIP AND CONDITIONAL ICONS --- -->
              <TooltipProvider :delay-duration="100">
                <Tooltip>
                  <TooltipTrigger>
                    <Globe
                      v-if="audioFile.is_public"
                      class="h-5 w-5 text-gray-500"
                    />
                    <GlobeOff v-else class="h-5 w-5 text-gray-500" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{{ audioFile.is_public ? "Public" : "Private" }}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>

            <CardDescription class="mb-2 mt-1">
              Opublikowane: {{ formatDate(audioFile.uploaded_at) }}
            </CardDescription>
            <CardDescription v-if="audioFile.description" class="mb-2">
              Opis: {{ audioFile.description }}
            </CardDescription>
            <CardDescription v-else class="mb-2 text-sm text-gray-500">
              Opis: Brak opisu
            </CardDescription>
            <audio controls :src="audioFile.file" class="w-full mt-4">
              Your browser does not support the audio element.
            </audio>
            <div
              class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-start space-x-6"
            >
              <!-- Like/Dislike buttons remain the same -->
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
                  :class="{ 'text-red-500': audioFile.user_vote === 'dislike' }"
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
            </div>
          </CardContent>
        </Card>
      </div>
      <!-- "Load More" section remains the same -->
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