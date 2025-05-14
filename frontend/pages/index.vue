<script setup lang="ts">
import { ref } from 'vue'
import { Card, CardContent, CardTitle, CardDescription } from '@/components/ui/card'

interface AudioFile {
  id: number;
  title: string;
  uploaded_at: string;
}

const latestAudioFiles = ref<AudioFile[]>([])
const loading = ref(true)
const error = ref<string | null>(null) 

const fetchAudioFiles = async () => {
  loading.value = true;
  error.value = null; 
  try {
    const response = await fetch('http://127.0.0.1:8000/api/audio/latest/'); 

    if (!response.ok) {
      error.value = `HTTP error! status: ${response.status}`;
      console.error('HTTP error:', response.status);
      return; 
    }

    const data: AudioFile[] = await response.json();
    latestAudioFiles.value = data;

  } catch (e: any) {
    error.value = `Error fetching audio files: ${e.message}`;
    console.error('Fetch error:', e);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchAudioFiles();
});

const formatDate = (dateString: string) => {
  const options: Intl.DateTimeFormatOptions = { year: 'numeric', month: 'numeric', day: 'numeric' };
  return new Date(dateString).toLocaleDateString(undefined, options);
}

import { onMounted } from 'vue'; 

</script>

<template>
  <div>
    <h2 class="text-2xl font-bold mb-4">Latest</h2>

    <div v-if="loading" class="text-center">Wczytywanie...</div>
    <div v-else-if="error" class="text-center text-red-500">Error : {{ error }}</div>
    <div v-else>
      <div v-if="latestAudioFiles.length === 0" class="text-center text-gray-500">No files.</div>
      <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card v-for="audioFile in latestAudioFiles" :key="audioFile.id">
          <CardContent class="p-6">
            <CardTitle>{{ audioFile.title }}</CardTitle>
            <CardDescription>Opublikowane: {{ formatDate(audioFile.uploaded_at) }}</CardDescription>
            <CardDescription>Opis: {{ audioFile.description }}</CardDescription>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>
