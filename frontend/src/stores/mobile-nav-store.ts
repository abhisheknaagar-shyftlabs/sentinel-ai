import { create } from 'zustand'

interface MobileNavState {
  isOpen: boolean
  toggle: () => void
  close: () => void
}

export const useMobileNavStore = create<MobileNavState>()((set) => ({
  isOpen: false,
  toggle: () => set((state) => ({ isOpen: !state.isOpen })),
  close: () => set({ isOpen: false }),
}))
