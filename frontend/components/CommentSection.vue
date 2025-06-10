<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuth } from "@/composables/useAuth";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

const props = defineProps<{
  audioFileUuid: string;
}>();

interface User {
  name: string;
}

interface Reply {
  id: string;
  content: string;
  created_at: string;
  user: User;
}

interface Comment extends Reply {
  replies: Reply[];
}

const comments = ref<Comment[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const newCommentContent = ref("");
const newReplyContent = ref("");
const replyingTo = ref<string | null>(null);
const isSubmitting = ref(false);

const { $api } = useNuxtApp();
const { isAuthenticated, user } = useAuth();

const getAvatarFallback = (name: string | undefined | null) => {
  if (name && name.length > 0) {
    return name.charAt(0).toUpperCase();
  }
  return "A";
};

const fetchComments = async () => {
  error.value = null;
  try {
    const response = await $api.get<Comment[]>(
      `/api/comments/audio/${props.audioFileUuid}/`
    );
    comments.value = response.data;
  } catch (e: any) {
    console.error("Failed to fetch comments:", e);
    error.value = "Could not load comments.";
  } finally {
    if (loading.value) {
      loading.value = false;
    }
  }
};

onMounted(() => {
  loading.value = true;
  fetchComments();
});

const postComment = async () => {
  if (!newCommentContent.value.trim() || isSubmitting.value) return;
  isSubmitting.value = true;
  try {
    await $api.post<Comment>(
      `/api/comments/audio/${props.audioFileUuid}/`,
      { content: newCommentContent.value }
    );
    newCommentContent.value = "";
    await fetchComments();
  } catch (e) {
    console.error("Failed to post comment:", e);
  } finally {
    isSubmitting.value = false;
  }
};

const postReply = async (parentComment: Comment) => {
  if (!newReplyContent.value.trim() || isSubmitting.value) return;
  isSubmitting.value = true;
  try {
    await $api.post<Reply>(`/api/comments/${parentComment.id}/replies/`, {
      content: newReplyContent.value,
    });
    newReplyContent.value = "";
    replyingTo.value = null;
    await fetchComments();
  } catch (e) {
    console.error("Failed to post reply:", e);
  } finally {
    isSubmitting.value = false;
  }
};

const showReplyForm = (commentId: string) => {
  replyingTo.value = commentId;
  newReplyContent.value = "";
};

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString();
};
</script>

<template>
  <div class="mt-4 pt-4 border-t dark:border-gray-700">
    <h3 class="text-lg font-semibold mb-3">Komentarze</h3>

    <div v-if="isAuthenticated" class="flex items-start gap-4 mb-6">
      <Avatar>
        <AvatarFallback>{{ getAvatarFallback(user?.name) }}</AvatarFallback>
      </Avatar>
      <div class="w-full">
        <form @submit.prevent="postComment">
          <Textarea
            v-model="newCommentContent"
            placeholder="Napisz komentarz"
            class="mb-2"
            :disabled="isSubmitting"
          />
          <div class="flex justify-end">
            <Button type="submit" :disabled="!newCommentContent.trim() || isSubmitting">
              Komentuj
            </Button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="loading">Wczytywanie komentarzy</div>
    <div v-else-if="error" class="text-red-500">{{ error }}</div>
    <div v-else-if="comments.length === 0" class="text-gray-500">
      Brak komentarzy
    </div>
    <div v-else class="space-y-6">
      <div v-for="comment in comments" :key="comment.id" class="flex gap-4">
        <Avatar>
          <AvatarFallback>{{ getAvatarFallback(comment.user.name) }}</AvatarFallback>
        </Avatar>
        <div class="flex-1">
          <div class="text-sm">
            <span class="font-semibold">{{ comment.user.name || "User" }}</span>
            <span class="text-xs text-gray-500 ml-2">{{
              formatDate(comment.created_at)
            }}</span>
          </div>
          <p class="mt-1 text-gray-800 dark:text-gray-300">
            {{ comment.content }}
          </p>
          <Button
            v-if="isAuthenticated"
            variant="link"
            class="p-0 h-auto text-xs mt-1"
            @click="showReplyForm(comment.id)"
          >
            Odpowiedz
          </Button>
          <div v-if="replyingTo === comment.id" class="flex items-start gap-4 mt-4">
            <Avatar class="w-8 h-8">
              <AvatarFallback>{{ getAvatarFallback(user?.name) }}</AvatarFallback>
            </Avatar>
            <div class="w-full">
              <form @submit.prevent="postReply(comment)">
                <Textarea
                  v-model="newReplyContent"
                  placeholder="Odpowiedz"
                  class="mb-2"
                  :disabled="isSubmitting"
                />
                <div class="flex justify-end gap-2">
                  <Button
                    type="button"
                    variant="ghost"
                    @click="replyingTo = null"
                    :disabled="isSubmitting"
                  >
                    Anuluj
                  </Button>
                  <Button
                    type="submit"
                    :disabled="!newReplyContent.trim() || isSubmitting"
                  >
                    Odpowiedz
                  </Button>
                </div>
              </form>
            </div>
          </div>
          <div v-if="comment.replies?.length" class="mt-4 space-y-4">
            <div v-for="reply in comment.replies" :key="reply.id" class="flex gap-4">
              <Avatar class="w-8 h-8">
                <AvatarFallback>{{ getAvatarFallback(reply.user.name) }}</AvatarFallback>
              </Avatar>
              <div class="flex-1">
                <div class="text-sm">
                  <span class="font-semibold">{{ reply.user.name || "User" }}</span>
                  <span class="text-xs text-gray-500 ml-2">{{
                    formatDate(reply.created_at)
                  }}</span>
                </div>
                <p class="mt-1 text-gray-800 dark:text-gray-300">
                  {{ reply.content }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>