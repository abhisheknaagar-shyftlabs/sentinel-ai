import { useMutation } from '@tanstack/react-query'
import { useAuthStore } from '@/stores/auth-store'
import { login } from '../api/auth.api'

export function useLogin() {
  const setAuth = useAuthStore((state) => state.login)
  return useMutation({
    mutationFn: login,
    onSuccess: (data) => setAuth(data.user, data.token),
  })
}
