import { useEffect, useRef } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../state/auth';
import { Home, Users, Camera, CarFront, UserPlus, LogIn, LogOut } from 'lucide-react';
import './Sidebar.css';

const publicRoutes = [
    { path: '/', name: 'Início', icon: Home },
    { path: '/celulas', name: 'Casas de Cornélio', icon: Users },
    { path: '/carona', name: 'Carona Solidária', icon: CarFront },
];

const protectedRoutes = [
    { path: '/galeria', name: 'Galeria', icon: Camera, permKey: 'galeria' },
    { path: '/visitantes', name: 'Visitantes', icon: UserPlus, permKey: 'visitantes' },
    { path: '/usuarios', name: 'Gestão de Usuários', icon: Users, permKey: 'usuarios' },
];

export default function Sidebar() {
    const { isAuthenticated, permissions, logout } = useAuthStore();
    const navigate = useNavigate();

    const activeRoutes = [...publicRoutes];

    if (isAuthenticated && permissions) {
        protectedRoutes.forEach(route => {
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
                    <button className="nav-item btn-logout" onClick={() => { logout(); closeSidebar(); navigate('/'); }}>
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
