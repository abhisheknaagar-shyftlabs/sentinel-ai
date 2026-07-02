import { httpClient } from '@/services/http-client'
import type { LoginFormValues, LoginResponse } from '../types/login-schema'

export async function login(payload: LoginFormValues): Promise<LoginResponse> {
  return httpClient.post<LoginResponse>('/auth/login', payload)
}
