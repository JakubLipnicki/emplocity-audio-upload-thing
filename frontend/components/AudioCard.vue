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
  Copy,
} from "lucide-vue-next";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import CommentSection from "@/components/CommentSection.vue";

const props = defineProps({
  audioFile: {
    type: Object,
    required: true,
  },
  isAuthenticated: {
    type: Boolean,
    required: true,
  },
  activeCommentSection: {
    type: String,
    default: null,
  },
  activeTags: {
    type: Array,
    default: () => [],
  },
  isLinkCopied: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits([
  "vote",
  "play",
  "toggle-comments",
  "tag-click",
  "copy-link",
]);

const handleVote = (voteType: "like" | "dislike") => {
  emit("vote", props.audioFile, voteType);
};

const handlePlay = () => {
  emit("play", props.audioFile);
};

const toggleComments = () => {
  emit("toggle-comments", props.audioFile.uuid);
};

const onTagClick = (tagName: string) => {
  emit("tag-click", tagName);
};

const onCopyLink = () => {
  emit("copy-link", props.audioFile.uuid);
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
        <div
          @click="onCopyLink"
          class="flex items-center gap-2 cursor-pointer group"
        >
          <CardTitle class="group-hover:text-primary transition-colors">{{
            audioFile.title
          }}</CardTitle>
          <span
            v-if="isLinkCopied"
            class="text-sm font-medium text-green-600"
            >Copied!</span
          >
          <Copy
            v-else
            class="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity"
          />
        </div>
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
          :variant="activeTags.includes(tag) ? 'default' : 'outline'"
          size="sm"
          class="h-7 cursor-pointer"
          @click="onTagClick(tag)"
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
      <div
        class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-start"
      >
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
            @click="toggleComments"
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