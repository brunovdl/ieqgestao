import { useEffect, useRef } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuthStore } from '../state/auth';
import { Home, Users, Camera, CarFront, UserPlus, BarChart3, LogIn, LogOut } from 'lucide-react';
import './Sidebar.css';

const publicRoutes = [
    { path: '/', name: 'Início', icon: Home },
    { path: '/celulas', name: 'Casas de Cornélio', icon: Users },
    { path: '/galeria', name: 'Galeria', icon: Camera },
];

const protectedRoutes = [
    { path: '/visitantes', name: 'Visitantes', icon: UserPlus, permKey: 'visitantes' },
    { path: '/carona', name: 'Carona Solidária', icon: CarFront, permKey: 'carona' },
    { path: '/usuarios', name: 'Gestão de Usuários', icon: Users, permKey: 'usuarios' },
    { path: '/analytics', name: 'Analytics', icon: BarChart3, permKey: 'is_admin' },
];

export default function Sidebar() {
    const { isAuthenticated, permissions, logout } = useAuthStore();

    const activeRoutes = [...publicRoutes];

    if (isAuthenticated && permissions) {
        if (permissions.carona) {
            activeRoutes.push(protectedRoutes.find(r => r.path === '/carona')!);
        }

        protectedRoutes.forEach(route => {
            if (route.path === '/carona') return;

            const hasPerm = route.permKey === 'is_admin'
                ? permissions.is_admin
                : (permissions as any)[route.permKey];

            if (hasPerm) {
                activeRoutes.push(route);
            }
        });
    }

    const sidebarRef = useRef<HTMLDivElement>(null);

    const closeSidebar = () => {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar && sidebar.classList.contains('open')) {
            sidebar.classList.remove('open');
        }
    };

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (
                sidebarRef.current &&
                !sidebarRef.current.contains(event.target as Node) &&
                !(event.target as Element).closest('.menu-btn')
            ) {
                closeSidebar();
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    return (
        <div className="sidebar" ref={sidebarRef}>
            <div className="sidebar-header">
                <img src="/favicon.png" alt="IEQ Logo" className="logo" />
            </div>

            <nav className="sidebar-nav">
                {activeRoutes.map((route) => (
                    <NavLink
                        key={route.path}
                        to={route.path}
                        className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                        onClick={closeSidebar}
                    >
                        <route.icon className="nav-icon" size={20} />
                        <span>{route.name}</span>
                    </NavLink>
                ))}
            </nav>

            <div className="sidebar-footer">
                {isAuthenticated ? (
                    <button className="nav-item btn-logout" onClick={() => { logout(); closeSidebar(); }}>
                        <LogOut className="nav-icon" size={20} />
                        <span>Sair</span>
                    </button>
                ) : (
                    <button className="nav-item btn-login" onClick={() => { useAuthStore.getState().setLoginModalOpen(true); closeSidebar(); }}>
                        <LogIn className="nav-icon" size={20} />
                        <span>Entrar</span>
                    </button>
                )}
            </div>
        </div>
    );
}
