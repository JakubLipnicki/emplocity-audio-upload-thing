<template>
  <div class="w-full max-w-md mx-auto">
    <div class="bg-white rounded-lg shadow p-6">
      <div class="mb-4">
        <h2 class="text-xl font-bold mb-1">Upload Audio</h2>
      </div>

      <form @submit.prevent="uploadFile" class="space-y-4">
        <div>
          <label for="title" class="block text-sm font-medium mb-1">Tytul</label>
          <input
            id="title"
            v-model="title"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-md"
            placeholder="Tytul"
          />
        </div>
        <div>
          <label for="description" class="block text-sm font-medium mb-1"
            >Opis</label
          >
          <input
            id="description"
            v-model="description"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-md"
            placeholder="Opis"
          />
        </div>

        <div>
          <label for="audioFile" class="block text-sm font-medium mb-1"
            >Plik</label
          >
          <div
            class="border-2 border-dashed border-gray-300 rounded-md p-8 flex flex-col items-center justify-center cursor-pointer hover:border-blue-500"
            @click="$refs.fileInput.click()"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-10 w-10 text-gray-400 mb-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
              />
            </svg>
            <div v-if="!selectedFile" class="text-center">
              <p class="text-sm text-gray-500">MP3, WAV, M4A, OGG, FLAC</p>
            </div>
            <div v-else class="text-center">
              <p class="font-medium text-blue-500">{{ selectedFile.name }}</p>
              <p class="text-sm">{{ formatFileSize(selectedFile.size) }}</p>
              <button
                type="button"
                class="mt-2 text-sm text-red-500 hover:text-red-700"
                @click.stop="removeFile"
              >
                Usun plik
              </button>
            </div>
            <input
              ref="fileInput"
              id="audioFile"
              type="file"
              class="hidden"
              accept=".mp3,.wav,.m4a,.ogg,.flac"
              @change="handleFileChange"
            />
          </div>
          <p v-if="fileError" class="text-sm text-red-500 mt-1">
            {{ fileError }}
          </p>
        </div>

        <div class="flex items-center justify-between pt-2">
          <div class="flex items-center space-x-2">
            <Switch id="is-public-switch" v-model:checked="isPublic" />
            <Label for="is-public-switch">Publiczny</Label>
          </div>
        
          <button
            type="submit"
            class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="!isValid || isUploading"
          >
            {{ isUploading ? "Wysylanie..." : "Wyslij" }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

const title = ref("");
const description = ref("");
const selectedFile = ref(null);
const fileError = ref("");
const isUploading = ref(false);
const fileInput = ref(null);

const isPublic = ref(true); 

const isValid = computed(() => {
  return title.value.trim() !== "" && selectedFile.value !== null;
});

const handleFileChange = (event) => {
  const file = event.target.files[0];
  if (file) {
    validateFile(file);
  }
};

const validateFile = (file) => {
  fileError.value = "";
  const allowedTypes = [".mp3", ".wav", ".m4a", ".ogg", ".flac"];
  const fileExtension = file.name
    .substring(file.name.lastIndexOf("."))
    .toLowerCase();
  if (!allowedTypes.includes(fileExtension)) {
    fileError.value = "Akceptowane typy plikow to: MP3, WAV, M4A, OGG, FLAC.";
    return;
  }
  const maxSize = 50 * 1024 * 1024;
  if (file.size > maxSize) {
    fileError.value = "Maksymalny rozmiar pliku to 50MB";
    return;
  }
  selectedFile.value = file;
};

const removeFile = (e) => {
  e.stopPropagation();
  selectedFile.value = null;
  if (fileInput.value) {
    fileInput.value.value = "";
  }
};

const formatFileSize = (bytes) => {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
};

const uploadFile = async () => {
  if (!isValid.value) return;
  isUploading.value = true;
  const config = useRuntimeConfig();
  try {
    const formData = new FormData();
    formData.append("title", title.value);
    if (description.value) {
      formData.append("description", description.value);
    }
    formData.append("file", selectedFile.value);
    formData.append("is_public", isPublic.value.toString());

    const response = await fetch(`${config.public.apiRoot}/api/audio/upload/`, {
      method: "POST",
      body: formData,
      credentials: "include",
    });
    if (response.ok) {
      title.value = "";
      description.value = ""; 
      selectedFile.value = null;
      fileInput.value.value = "";
      isPublic.value = true; 
      alert("Sukces!");
    } else {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Blad podczas przesylania");
    }
  } catch (error) {
    fileError.value = error.message || "error upload";
  } finally {
    isUploading.value = false;
  }
};
</script>