<script setup lang="ts">
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardTitle,
} from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import {
  ThumbsUp,
  ThumbsDown,
  Globe,
  Lock,
  Eye,
  Trash2,
} from "lucide-vue-next";

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
  showDeleteButton?: boolean;
}>();

const emit = defineEmits<{
  (e: "vote", payload: { file: AudioFile; voteType: "like" | "dislike" }): void;
  (e: "play", file: AudioFile): void;
  (e: "delete", file: AudioFile): void;
}>();

const handleVote = (voteType: "like" | "dislike") => {
  emit("vote", { file: props.audioFile, voteType });
};

const handlePlay = () => {
  emit("play", props.audioFile);
};

const handleDelete = () => {
  emit("delete", props.audioFile);
};

const formatDate = (dateString: string) => {
  const options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "numeric",
    day: "numeric",
  };
  return new Date(dateString).toLocaleDateString("pl-PL", options);
};
</script>

<template>
  <Card class="w-full flex flex-col">
    <CardContent class="p-6 flex-grow">
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
        Opublikowano: {{ formatDate(audioFile.uploaded_at) }}
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
        @play="handlePlay"
      >
        Your browser does not support the audio element.
      </audio>
    </CardContent>

    <CardFooter
      class="mt-auto border-t border-gray-200 dark:border-gray-700 flex items-center justify-between mt-4 pt-4 px-6 pb-6"
    >
      <!-- Left side: Stats -->
      <div class="flex items-center space-x-6">
        <div class="flex items-center space-x-1">
          <Button
            variant="ghost"
            size="icon"
            @click="handleVote('like')"
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
            @click="handleVote('dislike')"
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
        <div class="flex items-center space-x-1 text-gray-500">
          <Eye class="h-5 w-5" />
          <span class="text-sm min-w-[20px] text-center">{{
            audioFile.views
          }}</span>
        </div>
      </div>

      <!-- Right side: Delete Button (conditional) -->
      <div v-if="showDeleteButton">
        <TooltipProvider :delay-duration="200">
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                @click.capture="handleDelete"
                variant="ghost"
                size="icon"
                class="text-red-500 hover:text-red-700"
                aria-label="Delete"
              >
                <Trash2 class="h-5 w-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Usuń plik</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </CardFooter>
  </Card>
</template>