import { useState, useEffect } from 'react';
import { useAuthStore } from '../state/auth';
import { supabase } from '../lib/supabase';
import { User, Lock, Save, AlertCircle, CheckCircle2 } from 'lucide-react';
import './Profile.css';

export default function Profile() {
    const { user, updateUser } = useAuthStore();
    
    const [fullName, setFullName] = useState('');
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    
    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    useEffect(() => {
        if (user) {
            setFullName(user.full_name || '');
            setUsername(user.username || '');
            setEmail(user.email || '');
        }
    }, [user]);

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setMessage(null);

        if (!user) return;

        if (password && password !== confirmPassword) {
            setMessage({ type: 'error', text: 'As senhas não coincidem.' });
            return;
        }

        setIsLoading(true);

        try {
            const updates: any = {
                full_name: fullName,
                username: username,
                email: email || null,
            };

            if (password) {
                updates.password = password;
            }

            const { error } = await supabase
                .from('users')
                .update(updates)
                .eq('id', user.id)
                .select();

            if (error) {
                if (error.code === '23505') { // Unique violation
                    throw new Error('Nome de usuário já está em uso.');
                }
                throw error;
            }

            // Atualiza o estado global
            updateUser({
                full_name: fullName,
                username: username,
                email: email || null
            });

            setPassword('');
            setConfirmPassword('');
            setMessage({ type: 'success', text: 'Perfil atualizado com sucesso!' });
            
        } catch (err: any) {
            console.error('Erro ao atualizar perfil:', err);
            setMessage({ type: 'error', text: err.message || 'Erro ao atualizar os dados.' });
        } finally {
            setIsLoading(false);
        }
    };

    if (!user) {
        return <div className="page-container empty-state">Acesso negado.</div>;
    }

    return (
        <div className="page-container animate-fade-in profile-page">
            <div className="profile-header">
                <h2>Meu Perfil</h2>
                <p>Gerencie suas informações pessoais e credenciais de acesso.</p>
            </div>

            <div className="profile-content">
                <div className="profile-card glass-effect">
                    {message && (
                        <div className={`alert-message ${message.type}`}>
                            {message.type === 'success' ? <CheckCircle2 size={20} /> : <AlertCircle size={20} />}
                            <span>{message.text}</span>
                        </div>
                    )}

                    <form onSubmit={handleSave} className="profile-form">
                        <h3 className="section-title"><User size={20} /> Dados Pessoais</h3>
                        
                        <div className="form-group">
                            <label>Nome Completo</label>
                            <input 
                                type="text" 
                                value={fullName} 
                                onChange={(e) => setFullName(e.target.value)} 
                                required 
                                placeholder="Seu nome completo"
                            />
                        </div>

                        <div className="form-group">
                            <label>E-mail (Opcional)</label>
                            <input 
                                type="email" 
                                value={email} 
                                onChange={(e) => setEmail(e.target.value)} 
                                placeholder="seu@email.com"
                            />
                        </div>

                        <div className="form-group">
                            <label>Nome de Usuário (Login)</label>
                            <input 
                                type="text" 
                                value={username} 
                                onChange={(e) => setUsername(e.target.value)} 
                                required 
                                placeholder="Como você acessa o sistema"
                            />
                        </div>

                        <div className="divider"></div>

                        <h3 className="section-title"><Lock size={20} /> Alterar Senha</h3>
                        <p className="helper-text">Deixe em branco se não quiser alterar a senha atual.</p>
                        
                        <div className="form-row grid-1-2">
                            <div className="form-group">
                                <label>Nova Senha</label>
                                <input 
                                    type="password" 
                                    value={password} 
                                    onChange={(e) => setPassword(e.target.value)} 
                                    placeholder="••••••••"
                                />
                            </div>
                            <div className="form-group">
                                <label>Confirmar Nova Senha</label>
                                <input 
                                    type="password" 
                                    value={confirmPassword} 
                                    onChange={(e) => setConfirmPassword(e.target.value)} 
                                    placeholder="••••••••"
                                />
                            </div>
                        </div>

                        <div className="form-actions" style={{ marginTop: '2rem' }}>
                            <button type="submit" className="btn btn-primary btn-lg" disabled={isLoading}>
                                <Save size={20} /> {isLoading ? 'Salvando...' : 'Salvar Alterações'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}
