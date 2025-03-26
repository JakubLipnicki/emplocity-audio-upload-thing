<script setup>
const route = useRoute();
const name = route.params.name;
</script>

<template>
    <h1>Profile page</h1>
    <h2>Username: {{ name }}</h2>
</template>
