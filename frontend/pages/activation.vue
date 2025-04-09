<script setup>
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

const navigateToHome = () => {
  navigateTo('/')
}
</script>

<template>
  <div class="flex items-center justify-center h-full min-h-screen bg-white mx-auto">
    <Card class="w-full max-w-md mx-auto">
      <CardContent class="pt-6">
        <div class="space-y-6">
          <div class="space-y-2 text-center">
            <h1 class="text-2xl font-bold text-gray-900">Dziękujemy</h1>
            <p class="text-gray-700">Rejestracja zakończona pomyślnie</p>
          </div>
          <div class="flex justify-center content-center h-svh">
            <Button @click="navigateToHome" class="bg-slate-900 text-white">
              Przejdź do strony głównej
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
