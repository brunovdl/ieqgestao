import { create } from 'zustand';

interface User {
    id: string;
    username: string;
    full_name: string;
}

interface Permissions {
    is_admin: boolean;
    readonly: boolean;
    home: boolean;
    galeria: boolean;
    celulas: boolean;
    carona: boolean;
    visitantes?: boolean;
    usuarios?: boolean;
}

interface AuthState {
    user: User | null;
    permissions: Permissions | null;
    isAuthenticated: boolean;
    isLoginModalOpen: boolean;
    setLoginModalOpen: (isOpen: boolean) => void;
    login: (user: User, permissions: Permissions) => void;
    logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
    user: null,
    permissions: null,
    isAuthenticated: false,
    isLoginModalOpen: false,
    setLoginModalOpen: (isOpen) => set({ isLoginModalOpen: isOpen }),
    login: (user, permissions) => set({ user, permissions, isAuthenticated: true, isLoginModalOpen: false }),
    logout: () => set({ user: null, permissions: null, isAuthenticated: false }),
}));
