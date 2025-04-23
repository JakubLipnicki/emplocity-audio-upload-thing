<template>
  <div class="container px-4 py-10 mx-auto max-w-md">
    <Card class="w-full">
      <CardHeader>
        <CardTitle>Resetuj hasło</CardTitle>
      </CardHeader>
      <CardContent>
        <div v-if="!resetSuccess && !invalidToken">
          <form @submit.prevent="onSubmit">
            <div class="grid gap-4">
              <div class="grid gap-2">
                <Label for="password">Nowe hasło</Label>
                <Input id="password" v-model="password" type="password"
                  :class="{ 'border-destructive': passwordError }" />
                <p v-if="passwordError" class="text-sm text-destructive">
                  {{ passwordError }}
                </p>
              </div>

              <div class="grid gap-2">
                <Label for="confirmPassword">Potwierdź hasło</Label>
                <Input id="confirmPassword" v-model="confirmPassword" type="password"
                  :class="{ 'border-destructive': confirmPasswordError }" />
                <p v-if="confirmPasswordError" class="text-sm text-destructive">
                  {{ confirmPasswordError }}
                </p>
              </div>

              <div v-if="errorMessage" class="text-sm text-destructive bg-destructive/10 p-3 rounded">
                {{ errorMessage }}
              </div>

              <Button type="submit" class="w-full" :disabled="isLoading">
                <Loader2 v-if="isLoading" class="mr-2 h-4 w-4 animate-spin" />
                {{ isLoading ? 'Resetowanie w toku...' : 'Resetuj' }}
              </Button>
            </div>
          </form>
        </div>

        <Alert v-else-if="resetSuccess" variant="success" class="mt-4">
          <CheckCircle class="h-4 w-4" />
          <AlertDescription>
            Hasło zostało zmienione!
            <div class="mt-2">
              <NuxtLink to="/login" class="text-primary hover:underline">
                Zaloguj sie
              </NuxtLink>
            </div>
          </AlertDescription>
        </Alert>

        <Alert v-else-if="invalidToken" variant="destructive" class="mt-4">
          <AlertCircle class="h-4 w-4" />
          <AlertTitle>Nieprawidłowy link</AlertTitle>
          <AlertDescription>
            Nieprawidłowy link lub link wygasł
            <div class="mt-2">
              <NuxtLink to="/request-password/" class="text-primary hover:underline">
                Resetuj hasło
              </NuxtLink>
            </div>
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { AlertCircle, CheckCircle, Loader2 } from 'lucide-vue-next'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'

const route = useRoute()

const password = ref('')
const confirmPassword = ref('')
const resetSuccess = ref(false)
const invalidToken = ref(false)
const errorMessage = ref('')
const isLoading = ref(false)
const token = ref('')
const passwordError = ref('')
const confirmPasswordError = ref('')

onMounted(() => {
  if (route.query && route.query.token) {
    token.value = route.query.token
    console.log('Token found:', token.value)
  } else {
    console.error('No token in URL')
    invalidToken.value = true
  }
})

const resetForm = () => {
  password.value = ''
  confirmPassword.value = ''
  passwordError.value = ''
  confirmPasswordError.value = ''
  errorMessage.value = ''
}

const validateForm = () => {
  let isValid = true
  passwordError.value = ''
  confirmPasswordError.value = ''

  if (!password.value || password.value.length < 8) {
    passwordError.value = 'Hasłó musi mieć co najmniej 8 znaków'
    isValid = false
  }

  if (password.value !== confirmPassword.value) {
    confirmPasswordError.value = 'Hasła nie są takie same'
    isValid = false
  }

  return isValid
}

const onSubmit = async () => {
  console.log('Form submitted')

  if (!validateForm()) {
    console.log('Validation failed')
    return
  }

  console.log('Validation passed, submitting request...')
  isLoading.value = true
  errorMessage.value = ''

  try {
    const response = await fetch('http://localhost:8000/api/reset-password/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        token: token.value,
        new_password: password.value
      })
    })

    const data = await response.json()
    console.log('Response:', data)

    if (!response.ok) {
      if (data.error && data.error.includes('Invalid or expired token')) {
        invalidToken.value = true
      }
      throw new Error(data.error || 'Failed to reset password')
    }

    resetSuccess.value = true
  } catch (error) {
    console.error('Error:', error)
    errorMessage.value = error.message || 'An error occurred. Please try again later.'
  } finally {
    isLoading.value = false
  }
}
</script>
