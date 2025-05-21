<script setup lang="ts">
import { ref, onMounted } from "vue"; 
import {
  Card,
  CardContent,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";

interface AudioFile {
  id: number;
  title: string;
  uploaded_at: string;
  file: string; 
  description: string | null; 
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

    const data: AudioFile[] = await response.json();
    latestAudioFiles.value = data;
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
            <CardDescription v-if="audioFile.description" class="mb-2"> Opis: {{ audioFile.description }}
            </CardDescription>
            <CardDescription v-else class="mb-2 text-sm text-gray-500"> Opis: Brak opisu
            </CardDescription>
            <audio controls :src="audioFile.file" class="w-full mt-4"> Your browser does not support the audio element.
            </audio>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>