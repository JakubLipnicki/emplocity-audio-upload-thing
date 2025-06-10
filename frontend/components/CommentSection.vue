<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuth } from "@/composables/useAuth";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

const props = defineProps<{
  audioFileUuid: string;
}>();

interface User {
  id: number;
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
const confirmingDeleteId = ref<string | null>(null);

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

const deleteComment = async (commentId: string) => {
  try {
    await $api.delete(`/api/comments/${commentId}/`);
    const index = comments.value.findIndex((c) => c.id === commentId);
    if (index !== -1) {
      comments.value.splice(index, 1);
    } else {
      for (const comment of comments.value) {
        if (comment.replies) {
          const replyIndex = comment.replies.findIndex(
            (r) => r.id === commentId
          );
          if (replyIndex !== -1) {
            comment.replies.splice(replyIndex, 1);
            break;
          }
        }
      }
    }
  } catch (err) {
    console.error("Failed to delete comment:", err);
    alert("Nie udało się usunąć komentarza.");
  } finally {
    confirmingDeleteId.value = null;
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
          <div class="flex items-center gap-4 mt-1">
            <Button
              v-if="isAuthenticated"
              variant="link"
              class="p-0 h-auto text-xs"
              @click="showReplyForm(comment.id)"
            >
              Odpowiedz
            </Button>
            <div v-if="isAuthenticated && comment.user.id === user?.id">
              <div v-if="confirmingDeleteId !== comment.id">
                <Button
                  variant="link"
                  class="p-0 h-auto text-xs text-red-600 hover:text-red-500"
                  @click="confirmingDeleteId = comment.id"
                >
                  Usuń
                </Button>
              </div>
              <div v-else class="flex items-center gap-2">
                <span class="text-sm">Na pewno?</span>
                <Button
                  variant="link"
                  class="p-0 h-auto text-xs text-red-600"
                  @click="deleteComment(comment.id)"
                >
                  Tak
                </Button>
                <Button
                  variant="link"
                  class="p-0 h-auto text-xs"
                  @click="confirmingDeleteId = null"
                >
                  Anuluj
                </Button>
              </div>
            </div>
          </div>

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
                <div v-if="isAuthenticated && reply.user.id === user?.id" class="mt-1">
                  <div v-if="confirmingDeleteId !== reply.id">
                    <Button
                      variant="link"
                      class="p-0 h-auto text-xs text-red-600 hover:text-red-500"
                      @click="confirmingDeleteId = reply.id"
                    >
                      Usuń
                    </Button>
                  </div>
                  <div v-else class="flex items-center gap-2">
                    <span class="text-sm">Na pewno?</span>
                    <Button
                      variant="link"
                      class="p-0 h-auto text-xs text-red-600"
                      @click="deleteComment(reply.id)"
                    >
                      Tak
                    </Button>
                    <Button
                      variant="link"
                      class="p-0 h-auto text-xs"
                      @click="confirmingDeleteId = null"
                    >
                      Anuluj
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>