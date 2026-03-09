import { useState } from 'react';
import { useAuthStore } from '../state/auth';
import { getBrasiliaTimestampString } from '../utils/timezone';
import { supabase } from '../lib/supabase';
import { X, Lock, User } from 'lucide-react';
import './LoginModal.css';

interface LoginModalProps {
    onClose: () => void;
}

export default function LoginModal({ onClose }: LoginModalProps) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const { login } = useAuthStore();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            // Usando query direta igual ao flet database.py db.check_login
            const { data, error } = await supabase
                .from('users')
                .select('*')
                .eq('username', username)
                .eq('password', password);

            if (error) throw error;

            if (data && data.length > 0) {
                const user = data[0];

                let perms = typeof user.permissions === 'string' ? JSON.parse(user.permissions) : user.permissions || {};
                const isAdmin = user.is_admin || false;

                const finalPerms = {
                    is_admin: isAdmin,
                    readonly: isAdmin ? false : (perms.readonly || false),
                    eventos: isAdmin ? true : (perms.eventos || false),
                    galeria: isAdmin ? true : (perms.galeria || false),
                    celulas: isAdmin ? true : (perms.celulas || false),
                    carona: isAdmin ? true : (perms.carona || false),
                    visitantes: isAdmin ? true : (perms.visitantes || false),
                    usuarios: isAdmin ? true : (perms.usuarios || false),
                    analytics: isAdmin ? true : (perms.analytics || false),
                };

                login({ id: user.id, username: user.username, full_name: user.full_name || user.username }, finalPerms);

                // Atualiza last login
                await supabase.from('users').update({ last_login: getBrasiliaTimestampString() }).eq('id', user.id);

                onClose();
            } else {
                setError('Usuário ou senha inválidos.');
            }
        } catch (err: any) {
            setError('Erro de conexão ao acessar o banco.');
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="modal-backdrop fadeIn" onClick={onClose}>
            <div className="modal-content glass-effect scaleIn" onClick={(e) => e.stopPropagation()}>
                <button className="modal-close" onClick={onClose}><X size={20} /></button>

                <div className="modal-header">
                    <img src="/favicon.png" alt="Logo" className="modal-logo" />
                    <h2>Acesso Restrito</h2>
                </div>

                <form onSubmit={handleLogin} className="login-form">
                    {error && <div className="error-message">{error}</div>}

                    <div className="input-group">
                        <User className="input-icon" size={18} />
                        <input
                            type="text"
                            placeholder="Usuário"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                        />
                    </div>

                    <div className="input-group">
                        <Lock className="input-icon" size={18} />
                        <input
                            type="password"
                            placeholder="Senha"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>

                    <button type="submit" className="btn btn-primary login-submit" disabled={isLoading}>
                        {isLoading ? 'Entrando...' : 'Entrar'}
                    </button>
                </form>
            </div>
        </div>
    );
}
