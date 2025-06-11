<script setup>
import { ref, computed, onMounted } from "vue";
import { useNuxtApp } from "#app";
import { useAuth } from "@/composables/useAuth";
import { useClipboard } from "@vueuse/core";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// Composables
const { accessToken, isAuthenticated } = useAuth();
const { $api } = useNuxtApp();

// Component State
const title = ref("");
const description = ref("");
const selectedFile = ref(null);
const fileError = ref("");
const isUploading = ref(false);
const fileInput = ref(null);
const isPublic = ref(true);
const availableTags = ref([]);
const selectedTags = ref(new Set());

// Dialog State
const isSuccessDialogOpen = ref(false);
const isLinkDialogOpen = ref(false);
const shareableLink = ref("");
const { copy, copied } = useClipboard({ source: shareableLink });

// Computed property for form validation
const isValid = computed(() => {
  return title.value.trim() !== "" && selectedFile.value !== null;
});

// Fetch available tags on component mount
onMounted(async () => {
  try {
    const response = await $api.get("/api/audio/tags/");
    availableTags.value = response.data;
  } catch (error) {
    console.error("Failed to fetch tags:", error);
  }
});

// Helper functions
const toggleTag = (tagName) => {
  if (selectedTags.value.has(tagName)) {
    selectedTags.value.delete(tagName);
  } else {
    selectedTags.value.add(tagName);
  }
};

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
  const maxSize = 50 * 1024 * 1024; // 50MB
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

const resetForm = () => {
  title.value = "";
  description.value = "";
  selectedFile.value = null;
  if (fileInput.value) {
    fileInput.value.value = "";
  }
  isPublic.value = true;
  selectedTags.value.clear();
  fileError.value = "";
};

// Main upload function
const uploadFile = async () => {
  if (!isValid.value) return;
  isUploading.value = true;
  fileError.value = "";

  const formData = new FormData();
  formData.append("title", title.value);
  if (description.value) {
    formData.append("description", description.value);
  }
  formData.append("file", selectedFile.value);
  formData.append("is_public", isPublic.value.toString());
  selectedTags.value.forEach((tag) => {
    formData.append("tags", tag);
  });

  const headers = {};
  if (accessToken.value) {
    headers["Authorization"] = `Bearer ${accessToken.value}`;
  }

  try {
    const response = await $api.post("/api/audio/upload/", formData, {
      headers: headers,
    });

    // Conditional success logic
    if (!isAuthenticated.value && !isPublic.value) {
      // Case: Anonymous user uploading a private file
      const uuid = response.data.uuid;
      if (uuid) {
        shareableLink.value = `${window.location.origin}/audio/${uuid}`;
        isLinkDialogOpen.value = true;
      }
    } else {
      // Default case for all other uploads
      isSuccessDialogOpen.value = true;
    }
    resetForm();
  } catch (error) {
    // Corrected error handling
    const errorMessage =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      "Blad podczas przesylania";
    fileError.value = errorMessage;
    console.error("Upload error:", error);
  } finally {
    isUploading.value = false;
  }
};
</script>

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
          <label class="block text-sm font-medium mb-2">Tagi</label>
          <div
            v-if="availableTags.length > 0"
            class="flex flex-wrap gap-2"
          >
            <Badge
              v-for="tag in availableTags"
              :key="tag.id"
              :variant="selectedTags.has(tag.name) ? 'default' : 'outline'"
              class="cursor-pointer"
              @click="toggleTag(tag.name)"
            >
              {{ tag.name }}
            </Badge>
          </div>
          <p v-else class="text-sm text-gray-500">Ladowanie tagow...</p>
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
            <!-- --- THIS IS THE CORRECTED LINE --- -->
            <Switch id="is-public-switch" v-model="isPublic" />
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

    <!-- Standard Success Dialog -->
    <Dialog v-model:open="isSuccessDialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Sukces!</DialogTitle>
          <DialogDescription>
            Twój plik audio został pomyślnie przesłany.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button @click="isSuccessDialogOpen = false">Zamknij</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Shareable Link Dialog -->
    <Dialog v-model:open="isLinkDialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Prywatny link do pliku</DialogTitle>
          <DialogDescription>
            Twój plik został przesłany jako prywatny. Użyj poniższego linku, aby
            go wyświetlić i udostępnić.
          </DialogDescription>
        </DialogHeader>
        <div class="flex items-center space-x-2 mt-4">
          <Input id="link" :default-value="shareableLink" readonly />
          <Button @click="copy(shareableLink)">
            {{ copied ? "Skopiowano!" : "Kopiuj" }}
          </Button>
        </div>
        <DialogFooter class="mt-4">
          <Button @click="isLinkDialogOpen = false">Zamknij</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>