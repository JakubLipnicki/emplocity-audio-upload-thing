<template>
    <div>
        <Navbar />
        <NuxtPage />

        <footer><!-- Your footer --></footer>
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
