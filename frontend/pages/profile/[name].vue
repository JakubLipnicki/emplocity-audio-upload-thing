<script setup>
const route = useRoute();
const name = route.params.name;

const getUserInfo = async () => {
  try {
    // console.log("Cookies jwt:", document.cookie);
    const cookie = useCookie('jwt')
    console.log("JWT cookie: ", cookie.value)

    const response = await fetch("http://127.0.0.1:8000/api/user", {
      method: "GET",
      credentials: 'include',
      jwt: cookie.value,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error("Fail: ", response.status, errorData);
      return null;
    }

    const userInfo = await response.json();
    console.log("Authenticated user:", userInfo);
    console.log("User ID:", userInfo.id);
    return userInfo;
  } catch (error) {
    console.error("Request error:", error);
    return null;
  }
};

onMounted(() => {
  console.log('All cookies:', document.cookie)
})

</script>


<template>
  <h1>Profile page</h1>
  <h2>Username: {{ name }}</h2>
  <Button @click="getUserInfo">TEST JWT</Button>
</template>
