<script setup lang="ts">
import { ref, onMounted } from "vue";
import {
  Card,
  CardContent,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button"; 
import { ThumbsUp, ThumbsDown } from "lucide-vue-next"; 

interface ApiAudioFile {
  id: number;
  title: string;
  uploaded_at: string;
  file: string;
  description: string | null;
}

// Dummy like n dislike data
interface AudioFile extends ApiAudioFile {
  likes: number;
  dislikes: number;
  userVote: 'like' | 'dislike' | null; 
}

const latestAudioFiles = ref<AudioFile[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

const fetchAudioFiles = async () => {
  loading.value = true;
  error.value = null;

  const config = useRuntimeConfig();

  try {
    const response = await fetch(`${config.public.apiRoot}/api/audio/latest/`);

    if (!response.ok) {
      error.value = `HTTP error! status: ${response.status}`;
      console.error("HTTP error:", response.status);
      return;
    }

    const data: ApiAudioFile[] = await response.json();
    latestAudioFiles.value = data.map(file => ({
      ...file,
      likes: Math.floor(Math.random() * 100), 
      dislikes: Math.floor(Math.random() * 30), 
      userVote: null, 
    }));
    console.log(latestAudioFiles)
  } catch (e: any) {
    error.value = `Error fetching audio files: ${e.message}`;
    console.error("Fetch error:", e);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchAudioFiles();
});

const formatDate = (dateString: string) => {
  const options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "numeric",
    day: "numeric",
  };
  return new Date(dateString).toLocaleDateString(undefined, options);
};

const handleVote = (file: AudioFile, voteType: 'like' | 'dislike') => {
  if (voteType === 'like') {
    if (file.userVote === 'like') { 
      file.likes--;
      file.userVote = null;
    } else { 
      if (file.userVote === 'dislike') {
        file.dislikes--; 
      }
      file.likes++;
      file.userVote = 'like';
    }
  } else if (voteType === 'dislike') {
    if (file.userVote === 'dislike') { 
      file.dislikes--;
      file.userVote = null;
    } else { 
      if (file.userVote === 'like') {
        file.likes--; 
      }
      file.dislikes++;
      file.userVote = 'dislike';
    }
  }
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
            <CardTitle>{{ audioFile.title }}</CardTitle>
            <CardDescription class="mb-2"
              >Opublikowane:
              {{ formatDate(audioFile.uploaded_at) }}</CardDescription
            >
            <CardDescription v-if="audioFile.description" class="mb-2">
                Opis: {{ audioFile.description }}
            </CardDescription>
            <CardDescription v-else class="mb-2 text-sm text-gray-500">
                Opis: Brak opisu
            </CardDescription>
            <audio controls :src="audioFile.file" class="w-full mt-4">
              Your browser does not support the audio element.
            </audio>

            <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-start space-x-6">
              <div class="flex items-center space-x-1">
                <Button
                  variant="ghost"
                  size="icon"
                  @click="handleVote(audioFile, 'like')"
                  :class="{ 'text-blue-500': audioFile.userVote === 'like' }"
                  aria-label="Like"
                >
                  <ThumbsUp class="h-5 w-5" :class="{ 'fill-blue-500 dark:fill-blue-700 opacity-50': audioFile.userVote === 'like' }" />
                </Button>
                <span class="text-sm min-w-[20px] text-center">{{ audioFile.likes }}</span>
              </div>
              <div class="flex items-center space-x-1">
                <Button
                  variant="ghost"
                  size="icon"
                  @click="handleVote(audioFile, 'dislike')"
                  :class="{ 'text-red-500': audioFile.userVote === 'dislike' }"
                  aria-label="Dislike"
                >
                  <ThumbsDown class="h-5 w-5" :class="{ 'fill-red-500 dark:fill-red-700 opacity-50': audioFile.userVote === 'dislike' }" />
                </Button>
                <span class="text-sm min-w-[20px] text-center">{{ audioFile.dislikes }}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>