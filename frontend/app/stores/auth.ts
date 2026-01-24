import { defineStore } from 'pinia'

interface User {
  id: string
  username: string
}

interface LoginResponse {
  access_token: string
  expires_in: number
}

type MeResponse = User

export const useAuthStore = defineStore('auth', () => {
  const config = useRuntimeConfig()

  // State
  const user = ref<User | null>(null)
  const loading = ref(true)
  const accessToken = ref('')

  // Getters
  const isAuthenticated = computed(() => {
    if (user.value === null) {
      return false
    }
    return user.value.id !== null
  })

  // Actions
  const login = async (username: string, password: string) => {
    try {
      const response = await $fetch<LoginResponse>(
        `${config.public.apiUrl}/auth/login`,
        {
          method: 'POST',
          credentials: 'include',
          body: {
            username,
            password,
          },
        },
      )
      accessToken.value = response.access_token
    } catch (error) {
      console.log('Login failed')
      throw error
    } finally {
      loading.value = false
    }

    try {
      const response = await $fetch<MeResponse>(
        `${config.public.apiUrl}/auth/me`,
        {
          method: 'GET',
          credentials: 'include',
          headers: {
            Authorization: `Bearer ${accessToken.value}`,
          },
        },
      )
      user.value = response
    } catch (error) {
      console.log('Login failed')
      throw error
    } finally {
      loading.value = false
    }
  }
  // Return everything that components need access to
  return { user, isAuthenticated, loading, login }
})
