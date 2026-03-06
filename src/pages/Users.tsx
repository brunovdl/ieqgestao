import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { useAuthStore } from '../state/auth';
import { Shield, ShieldAlert, User, Plus, Edit2, X, Trash2 } from 'lucide-react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import './Users.css';

interface UserData {
    id: string;
    username: string;
    full_name: string;
    email: string;
    is_admin: boolean;
    permissions: any;
    created_at: string;
    last_login: string;
}

export default function Users() {
    const { permissions, user } = useAuthStore();
    const [usersList, setUsersList] = useState<UserData[]>([]);
    const [loading, setLoading] = useState(true);

    // Modals State
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [isSaving, setIsSaving] = useState(false);

    // Edit State
    const [selectedUser, setSelectedUser] = useState<UserData | null>(null);
    const [editPerms, setEditPerms] = useState({
        is_admin: false,
        visitantes: false,
        usuarios: false,
        readonly: false,
        celulas: true,
        galeria: true,
        carona: true,
        eventos: false,
        analytics: false
    });

    // Create State
    const [newUserForm, setNewUserForm] = useState({
        full_name: '',
        email: '',
        password: '',
        is_admin: false
    });

    if (!permissions?.is_admin && !permissions?.usuarios) {
        return <div className="page-container"><h2>Acesso Negado</h2><p>Você não tem permissão para administrar usuários.</p></div>;
    }

    useEffect(() => {
        fetchUsers();
    }, []);

    const fetchUsers = async () => {
        try {
            const { data, error } = await supabase
                .from('users')
                .select('*')
                .order('full_name', { ascending: true });

            if (error) throw error;
            setUsersList(data || []);
        } catch (err) {
            console.error('Erro ao buscar usuários:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleOpenModal = (usr: UserData) => {
        setSelectedUser(usr);
        setEditPerms({
            is_admin: usr.is_admin || false,
            visitantes: usr.permissions?.visitantes || false,
            usuarios: usr.permissions?.usuarios || false,
            readonly: usr.permissions?.readonly || false,
            celulas: usr.permissions?.celulas ?? true,
            galeria: usr.permissions?.galeria ?? true,
            carona: usr.permissions?.carona ?? true,
            eventos: usr.permissions?.eventos || false,
            analytics: usr.permissions?.analytics || false,
        });
        setIsEditModalOpen(true);
    };

    const handleSavePermissions = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedUser) return;
        setIsSaving(true);
        try {
            const newPermissions = {
                visitantes: editPerms.visitantes,
                usuarios: editPerms.usuarios,
                readonly: editPerms.readonly,
                celulas: editPerms.celulas,
                galeria: editPerms.galeria,
                carona: editPerms.carona,
                eventos: editPerms.eventos,
                analytics: editPerms.analytics,
            };

            const { error } = await supabase.from('users').update({
                is_admin: editPerms.is_admin,
                permissions: newPermissions
            }).eq('id', selectedUser.id);

            if (error) throw error;
            await fetchUsers();
            setIsEditModalOpen(false);
        } catch (err) {
            console.error('Erro ao salvar permissões:', err);
            alert("Erro ao salvar permissões.");
        } finally {
            setIsSaving(false);
        }
    };

    const handleCreateUser = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);
        try {
            // First create the user in Auth
            const { data: authData, error: authError } = await supabase.auth.signUp({
                email: newUserForm.email,
                password: newUserForm.password,
            });

            if (authError) {
                // Se o usuário já existir no auth, vamos tentar apenas inserir no public.users (bypass para ambiente dev)
                if (authError.message.includes('already registered')) {
                    alert("Este email já está registrado. Tente usar outro ou recupere a senha.");
                    return;
                } else {
                    throw authError;
                }
            }

            if (authData.user) {
                // Ensure record is updated/inserted in public.users via trigger or manual if needed.
                // Our current python logic used to depend on standard supabase flow.
                // We'll update the public user profile manually with the name and admin powers just in case
                const defaultPerms = { celulas: true, galeria: false, readonly: true, usuarios: false, visitantes: false, eventos: false, carona: true, analytics: false };
                const { error: profileError } = await supabase.from('users').upsert({
                    id: authData.user.id,
                    username: newUserForm.email.split('@')[0],
                    full_name: newUserForm.full_name,
                    email: newUserForm.email,
                    is_admin: newUserForm.is_admin,
                    permissions: newUserForm.is_admin ? {} : defaultPerms
                });

                if (profileError) throw profileError;
            }

            await fetchUsers();
            setIsCreateModalOpen(false);
            setNewUserForm({ full_name: '', email: '', password: '', is_admin: false });
            alert("Usuário criado com sucesso!");
        } catch (err: any) {
            console.error('Erro ao criar usuário:', err);
            alert(`Erro ao criar usuário: ${err.message}`);
        } finally {
            setIsSaving(false);
        }
    };

    const handleDeleteUser = async (id: string) => {
        if (!window.confirm("Certeza que deseja remover este usuário? Esta ação é irreversível.")) return;
        try {
            const { error } = await supabase.from('users').delete().eq('id', id);
            if (error) throw error;
            setUsersList((prev) => prev.filter((u) => u.id !== id));
        } catch (err) {
            console.error('Erro ao excluir usuário:', err);
            alert("Não foi possível excluir o usuário.");
        }
    };

    return (
        <div className="page-container animate-fade-in users-page">
            <div className="page-header" style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h2>Gestão de Usuários</h2>
                    <p className="subtitle">Controle de acessos e permissões do sistema</p>
                </div>
                {permissions?.is_admin && (
                    <button className="btn btn-primary" onClick={() => setIsCreateModalOpen(true)}>
                        <Plus size={20} /> Novo Usuário
                    </button>
                )}
            </div>

            {loading ? (
                <div className="loading-state">Carregando usuários...</div>
            ) : (
                <div className="users-table-container glass-effect">
                    <table className="users-table">
                        <thead>
                            <tr>
                                <th>Usuário</th>
                                <th>E-mail</th>
                                <th>Nível de Acesso</th>
                                <th>Último Login</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody>
                            {usersList.length > 0 ? (
                                usersList.map(usr => (
                                    <tr key={usr.id}>
                                        <td>
                                            <div className="table-user-cell">
                                                <div className="user-avatar-small">
                                                    <User size={18} color={usr.is_admin ? "var(--primary-color)" : "var(--text-secondary)"} />
                                                </div>
                                                <div className="user-title-small">
                                                    <strong>{usr.full_name || usr.username}</strong>
                                                    <span>@{usr.username}</span>
                                                </div>
                                            </div>
                                        </td>
                                        <td>{usr.email || '-'}</td>
                                        <td>
                                            {usr.is_admin ? (
                                                <span className="role-badge admin"><ShieldAlert size={14} /> Admin</span>
                                            ) : (
                                                <span className="role-badge standard"><Shield size={14} /> Padrão</span>
                                            )}
                                        </td>
                                        <td>{usr.last_login ? format(new Date(usr.last_login), "dd/MM/yy HH:mm", { locale: ptBR }) : '-'}</td>
                                        <td>
                                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                                {permissions?.is_admin && (
                                                    <>
                                                        <button className="icon-btn" onClick={() => handleOpenModal(usr)} title="Editar Permissões">
                                                            <Edit2 size={16} />
                                                        </button>
                                                        {user?.id !== usr.id && (
                                                            <button className="icon-btn" style={{ color: '#c62828' }} onClick={() => handleDeleteUser(usr.id)} title="Excluir Usuário">
                                                                <Trash2 size={16} />
                                                            </button>
                                                        )}
                                                    </>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            ) : (
                                <tr>
                                    <td colSpan={5} style={{ textAlign: 'center', padding: '2rem' }}>Nenhum usuário encontrado.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Edit Permissions Modal */}
            {isEditModalOpen && selectedUser && (
                <div className="admin-modal-backdrop fadeIn" onClick={() => setIsEditModalOpen(false)}>
                    <div className="admin-modal-content scaleIn" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '500px' }}>
                        <div className="admin-modal-header">
                            <h3>Editar Permissões</h3>
                            <button className="close-btn" onClick={() => setIsEditModalOpen(false)}><X size={24} /></button>
                        </div>
                        <form className="admin-form" onSubmit={handleSavePermissions}>
                            <div style={{ marginBottom: '1.5rem', padding: '1rem', backgroundColor: 'var(--bg-body)', borderRadius: 'var(--radius-md)' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                    <div className="user-avatar-small" style={{ width: '40px', height: '40px' }}>
                                        <User size={20} color="var(--primary-color)" />
                                    </div>
                                    <div>
                                        <h4 style={{ margin: 0 }}>{selectedUser.full_name || selectedUser.username}</h4>
                                        <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>@{selectedUser.username}</p>
                                    </div>
                                </div>
                            </div>

                            <div className="permissions-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>

                                <label className="perm-toggle">
                                    <input type="checkbox" checked={editPerms.is_admin} onChange={(e) => setEditPerms(prev => ({ ...prev, is_admin: e.target.checked }))} />
                                    <span>Administrador (Acesso Total)</span>
                                </label>

                                {!editPerms.is_admin && (
                                    <>
                                        <label className="perm-toggle">
                                            <input type="checkbox" checked={editPerms.usuarios} onChange={(e) => setEditPerms(prev => ({ ...prev, usuarios: e.target.checked }))} />
                                            <span>Gerir Usuários</span>
                                        </label>
                                        <label className="perm-toggle">
                                            <input type="checkbox" checked={editPerms.visitantes} onChange={(e) => setEditPerms(prev => ({ ...prev, visitantes: e.target.checked }))} />
                                            <span>Gerir Visitantes</span>
                                        </label>
                                        <label className="perm-toggle">
                                            <input type="checkbox" checked={editPerms.celulas} onChange={(e) => setEditPerms(prev => ({ ...prev, celulas: e.target.checked }))} />
                                            <span>Gerir Células</span>
                                        </label>
                                        <label className="perm-toggle">
                                            <input type="checkbox" checked={editPerms.galeria} onChange={(e) => setEditPerms(prev => ({ ...prev, galeria: e.target.checked }))} />
                                            <span>Gerir Galeria</span>
                                        </label>
                                        <label className="perm-toggle">
                                            <input type="checkbox" checked={editPerms.eventos} onChange={(e) => setEditPerms(prev => ({ ...prev, eventos: e.target.checked }))} />
                                            <span>Mural Eventos</span>
                                        </label>
                                        <label className="perm-toggle">
                                            <input type="checkbox" checked={editPerms.carona} onChange={(e) => setEditPerms(prev => ({ ...prev, carona: e.target.checked }))} />
                                            <span>Gerir Carona</span>
                                        </label>
                                        <label className="perm-toggle">
                                            <input type="checkbox" checked={editPerms.analytics} onChange={(e) => setEditPerms(prev => ({ ...prev, analytics: e.target.checked }))} />
                                            <span>Ver Analytics</span>
                                        </label>
                                        <label className="perm-toggle" style={{ borderLeft: '3px solid #fbd38d', paddingLeft: '0.5rem' }}>
                                            <input type="checkbox" checked={editPerms.readonly} onChange={(e) => setEditPerms(prev => ({ ...prev, readonly: e.target.checked }))} />
                                            <span>Modo Leitura (Apenas Ver)</span>
                                        </label>
                                    </>
                                )}
                            </div>

                            <div className="form-actions">
                                <button type="button" className="btn btn-secondary" onClick={() => setIsEditModalOpen(false)}>Cancelar</button>
                                <button type="submit" className="btn btn-primary" disabled={isSaving}>
                                    {isSaving ? 'Salvando...' : 'Atualizar Permissões'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Create User Modal */}
            {isCreateModalOpen && (
                <div className="admin-modal-backdrop fadeIn" onClick={() => setIsCreateModalOpen(false)}>
                    <div className="admin-modal-content scaleIn" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '500px' }}>
                        <div className="admin-modal-header">
                            <h3>Cadastrar Novo Usuário</h3>
                            <button className="close-btn" onClick={() => setIsCreateModalOpen(false)}><X size={24} /></button>
                        </div>
                        <form className="admin-form" onSubmit={handleCreateUser}>
                            <div className="form-group">
                                <label>Nome Completo</label>
                                <input
                                    type="text"
                                    required
                                    value={newUserForm.full_name}
                                    onChange={(e) => setNewUserForm(prev => ({ ...prev, full_name: e.target.value }))}
                                    placeholder="Ex: João Silva"
                                />
                            </div>
                            <div className="form-group">
                                <label>E-mail (Credencial de Login)</label>
                                <input
                                    type="email"
                                    required
                                    value={newUserForm.email}
                                    onChange={(e) => setNewUserForm(prev => ({ ...prev, email: e.target.value }))}
                                    placeholder="joao@email.com"
                                />
                            </div>
                            <div className="form-group">
                                <label>Senha Padrão</label>
                                <input
                                    type="password"
                                    required
                                    minLength={6}
                                    value={newUserForm.password}
                                    onChange={(e) => setNewUserForm(prev => ({ ...prev, password: e.target.value }))}
                                    placeholder="Mínimo 6 caracteres"
                                />
                            </div>

                            <div className="form-group" style={{ marginTop: '1rem' }}>
                                <label className="perm-toggle" style={{ border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-body)' }}>
                                    <input type="checkbox" checked={newUserForm.is_admin} onChange={(e) => setNewUserForm(prev => ({ ...prev, is_admin: e.target.checked }))} />
                                    <span>Cadastrar como Administrador Geral?</span>
                                </label>
                                <small style={{ color: 'var(--text-secondary)', marginTop: '0.5rem', display: 'block' }}>
                                    Se não for administrador, o novo usuário terá permissões básicas de padrão. Você pode editar os detalhes após a criação.
                                </small>
                            </div>

                            <div className="form-actions" style={{ marginTop: '2rem' }}>
                                <button type="button" className="btn btn-secondary" onClick={() => setIsCreateModalOpen(false)}>Cancelar</button>
                                <button type="submit" className="btn btn-primary" disabled={isSaving}>
                                    {isSaving ? 'Criando...' : 'Criar Conta'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
