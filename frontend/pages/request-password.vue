<script setup lang="ts">
import { Form } from "vee-validate";
import * as z from "zod";
import { toTypedSchema } from "@vee-validate/zod";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import {
  Form as FormComponent,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";

const router = useRouter();
const isLoading = ref(false);
const formSuccess = ref(false);
const errorMessage = ref("");
const successMessage = ref("");

const formSchema = z.object({
  email: z.string().email({ message: "Podaj prawidłowy adres email" }),
});

const schema = toTypedSchema(formSchema);

const onSubmit = async (values: z.infer<typeof formSchema>) => {
  isLoading.value = true;
  errorMessage.value = "";
  formSuccess.value = false;

  try {
    const response = await fetch("http://127.0.0.1:8000/api/request-password-reset/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: values.email,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      errorMessage.value = data.error || "Wystąpił błąd. Spróbuj ponownie.";
      return;
    }

    formSuccess.value = true;
    successMessage.value = data.message || "Link do resetowania hasła został wysłany na podany adres email.";
  } catch (error) {
    console.error("Reset error:", error);
    errorMessage.value = "Wystąpił błąd połączenia. Spróbuj ponownie.";
  } finally {
    isLoading.value = false;
  }
};

function backToLogin() {
  navigateTo("/")
}
</script>

<template>
  <div class="w-full max-w-md mx-auto p-6">
    <Card class="w-full">
      <CardHeader>
        <CardTitle class="text-2xl font-medium">Resetuj</CardTitle>

      </CardHeader>
      <CardContent>
        <div v-if="formSuccess" class="text-center py-4">
          <Alert class="bg-green-50 border-green-200">
            <AlertDescription>
              {{ successMessage }}
            </AlertDescription>
          </Alert>
        </div>

        <Form v-else @submit="onSubmit" :validation-schema="schema">
          <div class="space-y-4">
            <FormField name="email" v-slot="{ componentField }">
              <FormItem>
                <FormControl>
                  <Input v-bind="componentField" type="email" placeholder="email" />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <div v-if="errorMessage" class="text-red-500 text-sm mt-2 p-2 bg-red-50 rounded border border-red-200">
              {{ errorMessage }}
            </div>

            <Button type="submit" class="w-full font-normal" :disabled="isLoading">
              <span v-if="isLoading">Wysyłanie...</span>
              <span v-else>Wyślij link</span>
            </Button>
          </div>
        </Form>
      </CardContent>
      <CardFooter v-if="formSuccess" class="flex justify-center">
        <Button variant="link" @click="backToLogin">
          Powrót do logowania
        </Button>
      </CardFooter>
    </Card>
  </div>
</template>
