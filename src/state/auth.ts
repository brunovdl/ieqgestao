import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface User {
    id: string;
    username: string;
    full_name: string;
    email?: string | null;
}

interface Permissions {
    is_admin: boolean;
    readonly: boolean;
    galeria: boolean;
    celulas: boolean;
    carona: boolean;
    visitantes: boolean;
    usuarios: boolean;
    eventos: boolean;
}

interface AuthState {
    user: User | null;
    permissions: Permissions | null;
    isAuthenticated: boolean;
    isLoginModalOpen: boolean;
    setLoginModalOpen: (isOpen: boolean) => void;
    login: (user: User, permissions: Permissions) => void;
    logout: () => void;
    updateUser: (userData: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            user: null,
            permissions: null,
            isAuthenticated: false,
            isLoginModalOpen: false,
            setLoginModalOpen: (isOpen) => set({ isLoginModalOpen: isOpen }),
            login: (user, permissions) => set({ user, permissions, isAuthenticated: true, isLoginModalOpen: false }),
            logout: () => set({ user: null, permissions: null, isAuthenticated: false }),
            updateUser: (userData) => set((state) => ({ 
                user: state.user ? { ...state.user, ...userData } : null 
            })),
        }),
        {
            name: 'ieq-auth-session', // chave no localStorage
            storage: createJSONStorage(() => localStorage),
            // Apenas persists dados essenciais (não o estado do modal de login)
            partialize: (state) => ({
                user: state.user,
                permissions: state.permissions,
                isAuthenticated: state.isAuthenticated,
            }),
        }
    )
);
