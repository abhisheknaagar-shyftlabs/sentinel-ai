import { z } from 'zod'
import type { AuthUser } from '@/stores/auth-store'

export const loginSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
})

export type LoginFormValues = z.infer<typeof loginSchema>

export interface LoginResponse {
  token: string
  user: AuthUser
}
