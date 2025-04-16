<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
// import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle
} from '@/components/ui/card'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

const validationSchema = toTypedSchema(z.object({
  password: z
    .string()
    .min(8, { message: 'Hasło musi mieć co najmniej 8 znaków' }),
  confirmPassword: z
    .string()
    .min(1, { message: 'Wprowadz hasło ponownie' })
})
  .refine((data) => data.password === data.confirmPassword, {
    message: "Hasła muszą być identycznie",
    path: ["confirmPassword"],
  }))

const route = useRoute()
const router = useRouter()

const token = ref('')
const apiError = ref('')
const success = ref(false)
const isSubmitting = ref(false)

onMounted(() => {
  token.value = route.query.token || ''

  if (!token.value) {
    apiError.value = 'Coś poszło nie tak, spróbuj ponownie poźniej.'
  }
})

const onSubmit = async (values) => {
  if (!token.value) {
    apiError.value = 'Coś poszło nie tak, spróbuj ponownie poźniej.'
    return
  }

  try {
    isSubmitting.value = true
    apiError.value = ''


    const response = await fetch('http://127.0.0.1:8000/api/reset-password/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        token: token.value,
        new_password: values.password
      })
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw { data: errorData }
    }

    const data = await response.json()

    success.value = true

    setTimeout(() => {
      navigateTo("/login")
    }, 3000)
  } catch (error) {
    if (error.data && error.data.error) {
      apiError.value = error.data.error
    } else {
      apiError.value = 'Cos poszło nie tak, spróbuj ponownie poźniej'
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <Card class="w-full max-w-md mx-auto">
    <CardHeader>
      <CardTitle>Resetuj hasło</CardTitle>
    </CardHeader>
    <CardContent>
      <Form @submit="onSubmit" :validation-schema="validationSchema" v-slot="{ errors }">
        <div class="grid gap-4">
          <div class="grid gap-2">
            <FormField name="password" v-slot="{ field, errorMessage }">
              <FormItem>
                <FormLabel>Nowe hasło</FormLabel>
                <FormControl>
                  <Input type="password" v-bind="field" placeholder="Nowe hasło"
                    :class="{ 'border-red-500': errorMessage }" />
                </FormControl>
                <FormMessage v-if="errorMessage">{{ errorMessage }}</FormMessage>
              </FormItem>
            </FormField>
          </div>
          <div class="grid gap-2">
            <FormField name="confirmPassword" v-slot="{ field, errorMessage }">
              <FormItem>
                <FormLabel>Potwierdz hasło</FormLabel>
                <FormControl>
                  <Input type="password" v-bind="field" placeholder="Potwierdz nowe hasło"
                    :class="{ 'border-red-500': errorMessage }" />
                </FormControl>
                <FormMessage v-if="errorMessage">{{ errorMessage }}</FormMessage>
              </FormItem>
            </FormField>
          </div>
          <div v-if="apiError" class="text-sm font-medium text-red-500">
            {{ apiError }}
          </div>
          <div v-if="success" class="text-sm font-medium text-green-500">
            <p>Reset zakończony sukcesem</p>
          </div>
          <Button type="submit" :disabled="isSubmitting" class="w-full">
            {{ isSubmitting ? 'Resetowanie' : 'Resetuj' }}
          </Button>
        </div>
      </Form>
    </CardContent>
  </Card>
</template>
