<script setup>
const route = useRoute();
const name = route.params.name;

function reset() {
  navigateTo("/request-password/")
}
</script>

<template>
  <h1>Profile page</h1>
  <h2>Username: {{ name }}</h2>
  <Button @click="reset">Reset password</Button>
</template>
