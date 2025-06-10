<script setup lang="ts">
import { Button } from "./components/ui/button/";

const { fetchUser } = useAuth();

onMounted(() => {
  fetchUser();
});

</script>

<template>
    <div>
        <NuxtLayout>
            <NuxtPage />
        </NuxtLayout>
    </div>
</template>
