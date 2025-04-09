<script setup>
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";

import { Button } from "@/components/ui/button";

const goToMainPage = () => {
  navigateTo("/")
};
</script>

<template>
  <Card class="max-w-md mx-auto border border-gray-200">
    <CardContent class="p-6 space-y-4">
      <h1 class="text-2xl font-extrabold text-gray-900 mb-4">Dziękujemy</h1>
      <p class="text-gray-700 mb-6">Rejestracja zakończona pomyślnie</p>
      <div class="mt-4">
        <Button variant="default" class="bg-gray-900 hover:bg-gray-800 text-white w-full" @click="goToMainPage">
          Przejdź do strony głównej
        </Button>
      </div>
    </CardContent>
  </Card>
</template>
