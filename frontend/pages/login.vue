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

const { login, user } = useAuth();
const router = useRouter();

const formSchema = z.object({
  email: z.string().email({ message: "Podaj prawidlowy adres email" }),
  password: z.string().min(8, { message: "Haslo musi miec minimum 8 znakow" }),
});

const schema = toTypedSchema(formSchema);

async function onSubmit(values) {
  try {
    await login({ email: values.email, password: values.password });

    if (user.value) {
      navigateTo(`/profile/${user.value.name}`);
    } else {
      console.error("Login succeeded, but failed to fetch user details.");
    }
  } catch (error) {
    console.error("Login failed:", error);
  }
}

function onForgot() {
  navigateTo("/request-password/");
}
</script>

<template>
  <div class="w-full max-w-md mx-auto p-6">
    <Card class="w-full">
      <CardHeader>
        <CardTitle class="text-2xl font-medium">Logowanie</CardTitle>
      </CardHeader>
      <CardContent>
        <Form @submit="onSubmit" :validation-schema="schema">
          <div class="space-y-4">
            <FormField name="email" v-slot="{ componentField }">
              <FormItem>
                <FormLabel class="font-normal">e-mail</FormLabel>
                <FormControl>
                  <Input
                    v-bind="componentField"
                    type="email"
                    placeholder="e-mail"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormField name="password" v-slot="{ componentField }">
              <FormItem>
                <FormLabel class="font-normal">hasło</FormLabel>
                <FormControl>
                  <Input
                    v-bind="componentField"
                    type="password"
                    placeholder="hasło"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <!-- --- MODIFIED SECTION --- -->
            <div class="mt-4 flex items-center justify-between">
              <a @click="onForgot" class="text-sm cursor-pointer"
                >Nie pamiętam hasła</a
              >
              <NuxtLink to="/register" class="text-sm cursor-pointer"
                >Zarejestruj się</NuxtLink
              >
            </div>
            <!-- --- END MODIFIED SECTION --- -->

            <Button type="submit" class="w-full font-normal">Zaloguj</Button>
          </div>
        </Form>
      </CardContent>
    </Card>
  </div>
</template>