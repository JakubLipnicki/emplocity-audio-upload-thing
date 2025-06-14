// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  typescript: {
    strict: false,
  },
  runtimeConfig: {
    public: {
      apiRoot: 'http://localhost:8000', 
      mediaRoot: "http://localhost:9000/audio-files/",
    }
  },
  compatibilityDate: "2024-11-01",
  devtools: { enabled: true },

  nitro: {
    devProxy: {
      "/api": {
        target: "http://localhost:8000/api",
        changeOrigin: true,
      },
    },
  },

  modules: ["@nuxtjs/tailwindcss", "shadcn-nuxt"],

  shadcn: {
    /**
     * Prefix for all the imported component
     */
    prefix: "",
    /**
     * Directory that the component lives in.
     * @default "./components/ui"
     */
    componentDir: "./components/ui",
  },
});
