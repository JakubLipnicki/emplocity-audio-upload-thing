<template>
    <div>
        <header class="mb-4">
            <Navbar />
        </header>
        <NuxtPage />

        <footer></footer>
    </div>
</template>

<script>
import Navbar from "~/components/Navbar/Navbar.vue";

export default {
    components: {
        Navbar,
    },
};
</script>
