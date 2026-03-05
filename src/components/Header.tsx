import { Menu, LogIn, User } from 'lucide-react';
import { useAuthStore } from '../state/auth';
import { useLocation } from 'react-router-dom';
import LoginModal from './LoginModal';
import './Header.css';

export default function Header() {
    const { isAuthenticated, user, isLoginModalOpen, setLoginModalOpen } = useAuthStore();
    const location = useLocation();

    const getPageTitle = () => {
        const path = location.pathname;
        if (path === '/') return 'Início';
        if (path === '/celulas') return 'Casas de Cornélio';
        if (path === '/galeria') return 'Galeria';
        if (path === '/visitantes') return 'Visitantes';
        if (path === '/carona') return 'Carona Solidária';
        if (path === '/usuarios') return 'Gestão de Usuários';
        if (path === '/analytics') return 'Analytics';
        return 'Dashboard';
    };

    const toggleSidebar = () => {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            sidebar.classList.toggle('open');
        }
    };

    return (
        <>
            <header className="header">
                <div className="header-left">
                    <button className="menu-btn" onClick={toggleSidebar}>
                        <Menu size={24} />
                    </button>
                    <div className="header-title">
                        <img src="/home_icon.png" alt="Icon" className="header-icon" />
                        <h1>{getPageTitle()}</h1>
                    </div>
                </div>

                <div className="header-right">
                    <a href="https://www.instagram.com/ieqjdportugal/" target="_blank" rel="noopener noreferrer" className="icon-btn" title="Instagram">
                        <img src="/instagram_icon.png" alt="Insta" width={26} height={26} />
                    </a>

                    {isAuthenticated ? (
                        <div className="user-profile">
                            <User size={20} />
                            <span className="user-name">{user?.full_name?.split(' ')[0]}</span>
                        </div>
                    ) : (
                        <button className="icon-btn btn-login-header" onClick={() => setLoginModalOpen(true)} title="Entrar">
                            <LogIn size={24} color="var(--primary-color)" />
                        </button>
                    )}
                </div>
            </header>

            {isLoginModalOpen && <LoginModal onClose={() => setLoginModalOpen(false)} />}
        </>
    );
}
