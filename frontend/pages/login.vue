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

const router = useRouter();

const formSchema = z
  .object({
    email: z.string().email({ message: "Podaj prawidlowy adres email" }),
    password: z
      .string()
      .min(8, { message: "Haslo musi miec minimum 8 znakow" }),
  })

const schema = toTypedSchema(formSchema);

function onForgot() {
  navigateTo("/request-password/")
}

const onSubmit = async (values) => {
  try {
    const response = await fetch("http://127.0.0.1:8000/api/login", {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: values.email,
        password: values.password,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      console.error("Error details:", data.detail);
      return;
    }

    console.log("Login success:", data);
    navigateTo(`/profile/${values.email}`)

  } catch (error) {
    console.error("Login error:", error);
  }
};

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
                  <Input v-bind="componentField" type="email" placeholder="e-mail" />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormField name="password" v-slot="{ componentField }">
              <FormItem>
                <FormLabel class="font-normal">hasło</FormLabel>
                <FormControl>
                  <Input v-bind="componentField" type="password" placeholder="hasło" />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <div class="mt-4">
              <a @click="onForgot" class="text-sm cursor-pointer">Nie pamiętam hasła</a>
            </div>

            <Button type="submit" class="w-full font-normal">Zaloguj</Button>
          </div>
        </Form>
      </CardContent>
    </Card>
  </div>
</template>
