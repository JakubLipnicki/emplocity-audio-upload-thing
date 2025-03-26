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
        username: z
            .string()
            .min(3, { message: "Nazwa musi miec min 3 znaki" })
            .max(50, { message: "Nazwa moze miec max 50 znakow" }),
        email: z.string().email({ message: "Podaj prawidlowy adres email" }),
        password: z
            .string()
            .min(8, { message: "Haslo musi miec minimum 8 znakow" }),
        confirmPassword: z.string(),
    })
    .refine((data) => data.password === data.confirmPassword, {
        message: "Hasla nie sa identyczne",
        path: ["confirmPassword"],
    });

const schema = toTypedSchema(formSchema);

const onSubmit = (values: z.infer<typeof formSchema>) => {
    console.log(values);
    // console.log("Username: ", values.username)

    fetch("http://127.0.0.1:8000/api/register", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            name: values.username,
            email: values.email,
            password: values.password,
        }),
    })
        .then((response) => {
            if (!response.ok) {
                throw new Error("Registration failed");
            }
            return response.json();
        })
        .then((data) => {
            console.log("Registration success:", data);
            navigateTo(`/profile/${values.username}`);
        })
        .catch((error) => {
            console.error("Registration error:", error);
        });
};

// const onSubmit = form.handleSubmit((values) => {
//     console.log("Form submitted!", values);
// });
</script>

<template>
    <div class="w-full max-w-md mx-auto p-6">
        <Card class="w-full">
            <CardHeader>
                <CardTitle class="text-2xl font-medium">Rejestracja</CardTitle>
            </CardHeader>
            <CardContent>
                <Form @submit="onSubmit" :validation-schema="schema">
                    <div class="space-y-4">
                        <FormField name="username" v-slot="{ componentField }">
                            <FormItem>
                                <FormLabel class="font-normal"
                                    >nazwa użytkownika</FormLabel
                                >
                                <FormControl>
                                    <Input
                                        v-bind="componentField"
                                        placeholder="nazwa użytkownika"
                                    />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        </FormField>

                        <FormField name="email" v-slot="{ componentField }">
                            <FormItem>
                                <FormLabel class="font-normal"
                                    >e-mail</FormLabel
                                >
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

                        <FormField
                            name="confirmPassword"
                            v-slot="{ componentField }"
                        >
                            <FormItem>
                                <FormLabel class="font-normal"
                                    >powtórz hasło</FormLabel
                                >
                                <FormControl>
                                    <Input
                                        v-bind="componentField"
                                        type="password"
                                        placeholder="potwierdź hasło"
                                    />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        </FormField>

                        <Button type="submit" class="w-full font-normal"
                            >Utwórz konto</Button
                        >
                    </div>
                </Form>
            </CardContent>
        </Card>
    </div>
</template>
