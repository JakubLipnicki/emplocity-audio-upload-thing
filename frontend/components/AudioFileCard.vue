<script setup lang="ts">
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
import { ref } from "vue";
import { useAuth } from "@/composables/useAuth";

interface AudioFile {
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

const props = defineProps<{
  audioFile: AudioFile;
}>();

const emit = defineEmits<{
  (e: "vote", payload: { file: AudioFile; voteType: "like" | "dislike" }): void;
  (e: "play", file: AudioFile): void;
}>();

const { isAuthenticated } = useAuth();
const activeCommentSection = ref<string | null>(null);

const toggleCommentSection = (uuid: string) => {
  if (!isAuthenticated.value) {
    navigateTo("/login");
    return;
  }
  activeCommentSection.value =
    activeCommentSection.value === uuid ? null : uuid;
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
  <Card>
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
              <p>{{ audioFile.is_public ? "Publiczny" : "Prywatny" }}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      <CardDescription class="mb-2 mt-1 text-sm">
        Autor: {{ audioFile.uploader || "Anonim" }}
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

      <div
        v-if="audioFile.tags && audioFile.tags.length > 0"
        class="my-3 flex flex-wrap gap-2"
      >
        <Button
          v-for="tag in audioFile.tags"
          :key="tag"
          variant="outline"
          size="sm"
          class="h-7 cursor-default"
          @click.prevent
        >
          {{ tag }}
        </Button>
      </div>

      <audio
        controls
        :src="audioFile.file"
        class="w-full mt-4"
        @play="emit('play', audioFile)"
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
              @click="emit('vote', { file: audioFile, voteType: 'like' })"
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
              @click="emit('vote', { file: audioFile, voteType: 'dislike' })"
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
</template>