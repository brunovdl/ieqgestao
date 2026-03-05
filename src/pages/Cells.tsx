import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { useAuthStore } from '../state/auth';
import { Search, MapPin, Clock, Users as UsersIcon, Plus, Edit2, Trash2, PowerOff, X } from 'lucide-react';
import './Cells.css';

interface Cell {
    id: number;
    name: string;
    leader_name: string;
    host_name: string;
    address: string;
    meeting_day: string;
    meeting_time: string;
    active: boolean;
}

export default function Cells() {
    const { permissions } = useAuthStore();
    const isAdmin = permissions?.is_admin || false;

    const [cells, setCells] = useState<Cell[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');

    // Modal State
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingCell, setEditingCell] = useState<Cell | null>(null);
    const [formData, setFormData] = useState<Partial<Cell>>({
        name: '', leader_name: '', host_name: '', address: '', meeting_day: '', meeting_time: '', active: true
    });
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        fetchCells();
    }, []);

    const fetchCells = async () => {
        try {
            const { data, error } = await supabase
                .from('cells')
                .select('*')
                .order('active', { ascending: false })
                .order('name');

            if (error) throw error;
            setCells(data || []);
        } catch (err) {
            console.error('Erro ao buscar células:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleOpenModal = (cell?: Cell) => {
        if (cell) {
            setEditingCell(cell);
            setFormData(cell);
        } else {
            setEditingCell(null);
            setFormData({ name: '', leader_name: '', host_name: '', address: '', meeting_day: '', meeting_time: '', active: true });
        }
        setIsModalOpen(true);
    };

    const handleCloseModal = () => {
        setIsModalOpen(false);
        setEditingCell(null);
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value, type } = e.target;
        const finalValue = type === 'checkbox' ? (e.target as HTMLInputElement).checked : value;
        setFormData({ ...formData, [name]: finalValue });
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);
        try {
            if (editingCell) {
                const { error } = await supabase.from('cells').update(formData).eq('id', editingCell.id);
                if (error) throw error;
            } else {
                const { error } = await supabase.from('cells').insert([formData]);
                if (error) throw error;
            }
            await fetchCells();
            handleCloseModal();
        } catch (err) {
            console.error('Erro ao salvar célula:', err);
            alert('Falha ao salvar célula. Tente novamente.');
        } finally {
            setIsSaving(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (window.confirm('Tem certeza que deseja apagar esta Casa de Cornélio? Esta ação não pode ser desfeita.')) {
            try {
                const { error } = await supabase.from('cells').delete().eq('id', id);
                if (error) throw error;
                fetchCells();
            } catch (err) {
                console.error('Erro ao deletar célula:', err);
                alert('Erro ao excluir. Verifique sua conexão.');
            }
        }
    };

    const handleToggleActive = async (cell: Cell) => {
        try {
            const { error } = await supabase.from('cells').update({ active: !cell.active }).eq('id', cell.id);
            if (error) throw error;
            fetchCells();
        } catch (err) {
            console.error('Erro ao alterar status:', err);
        }
    };

    const filteredCells = cells.filter(cell => {
        if (!isAdmin && !cell.active) return false;
        return (
            cell.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            cell.leader_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            cell.address?.toLowerCase().includes(searchTerm.toLowerCase())
        );
    });

    return (
        <div className="page-container animate-fade-in cells-page">
            <div className="page-header">
                <div className="page-header-top">
                    <h2>Casas de Cornélio</h2>
                    {isAdmin && (
                        <button className="btn btn-primary" onClick={() => handleOpenModal()}>
                            <Plus size={18} /> Nova Célula
                        </button>
                    )}
                </div>
                <div className="search-bar">
                    <Search size={20} className="search-icon" />
                    <input
                        type="text"
                        placeholder="Buscar por nome, líder ou endereço..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            </div>

            {loading ? (
                <div className="loading-state">Carregando células...</div>
            ) : (
                <div className="cells-grid">
                    {filteredCells.length > 0 ? (
                        filteredCells.map(cell => (
                            <div key={cell.id} className={`cell-card glass-effect ${!cell.active ? 'inactive' : ''}`}>
                                <div className="cell-card-header">
                                    <h3>{cell.name}</h3>
                                    <span className={`status-badge ${cell.active ? 'active' : 'inactive'}`}>
                                        {cell.active ? 'Ativa' : 'Inativa'}
                                    </span>
                                </div>

                                <div className="cell-card-body">
                                    <div className="info-row">
                                        <UsersIcon size={18} className="info-icon" />
                                        <span><strong>Líder:</strong> {cell.leader_name}</span>
                                    </div>

                                    {cell.host_name && (
                                        <div className="info-row">
                                            <UsersIcon size={18} className="info-icon" />
                                            <span><strong>Anfitrião:</strong> {cell.host_name}</span>
                                        </div>
                                    )}

                                    {cell.meeting_day && cell.meeting_time && (
                                        <div className="info-row">
                                            <Clock size={18} className="info-icon" />
                                            <span>{cell.meeting_day} às {cell.meeting_time}</span>
                                        </div>
                                    )}

                                    {cell.address && (
                                        <div className="info-row">
                                            <MapPin size={18} className="info-icon" />
                                            <span>{cell.address}</span>
                                        </div>
                                    )}
                                </div>

                                {isAdmin && (
                                    <div className="cell-admin-actions">
                                        <button className="admin-action-btn" onClick={() => handleOpenModal(cell)} title="Editar">
                                            <Edit2 size={16} /> Editar
                                        </button>
                                        <button className="admin-action-btn" onClick={() => handleToggleActive(cell)} title={cell.active ? "Desativar" : "Ativar"}>
                                            <PowerOff size={16} /> {cell.active ? "Desativar" : "Ativar"}
                                        </button>
                                        <button className="admin-action-btn delete" onClick={() => handleDelete(cell.id)} title="Excluir">
                                            <Trash2 size={16} /> Apagar
                                        </button>
                                    </div>
                                )}
                            </div>
                        ))
                    ) : (
                        <div className="empty-state">Nenhuma célula encontrada.</div>
                    )}
                </div>
            )}

            {/* Admin Modal Form */}
            {isModalOpen && (
                <div className="admin-modal-backdrop fadeIn" onClick={handleCloseModal}>
                    <div className="admin-modal-content scaleIn" onClick={(e) => e.stopPropagation()}>
                        <div className="admin-modal-header">
                            <h3>{editingCell ? 'Editar Casa de Cornélio' : 'Nova Casa de Cornélio'}</h3>
                            <button className="close-btn" onClick={handleCloseModal}><X size={24} /></button>
                        </div>
                        <form className="admin-form" onSubmit={handleSave}>
                            <div className="form-group">
                                <label>Nome da Casa</label>
                                <input required type="text" name="name" value={formData.name || ''} onChange={handleChange} placeholder="Ex: Casa Betânia" />
                            </div>
                            <div className="form-group">
                                <label>Líder</label>
                                <input required type="text" name="leader_name" value={formData.leader_name || ''} onChange={handleChange} placeholder="Nome do líder" />
                            </div>
                            <div className="form-group">
                                <label>Anfitrião (Opcional)</label>
                                <input type="text" name="host_name" value={formData.host_name || ''} onChange={handleChange} placeholder="Nome do anfitrião" />
                            </div>
                            <div className="form-group">
                                <label>Endereço</label>
                                <input type="text" name="address" value={formData.address || ''} onChange={handleChange} placeholder="Rua, Número, Bairro" />
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                                <div className="form-group">
                                    <label>Dia de Reunião</label>
                                    <select name="meeting_day" value={formData.meeting_day || ''} onChange={handleChange} required>
                                        <option value="">Selecione...</option>
                                        <option value="Segunda-feira">Segunda-feira</option>
                                        <option value="Terça-feira">Terça-feira</option>
                                        <option value="Quarta-feira">Quarta-feira</option>
                                        <option value="Quinta-feira">Quinta-feira</option>
                                        <option value="Sexta-feira">Sexta-feira</option>
                                        <option value="Sábado">Sábado</option>
                                        <option value="Domingo">Domingo</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label>Horário</label>
                                    <input type="time" name="meeting_time" value={formData.meeting_time || ''} onChange={handleChange} required />
                                </div>
                            </div>
                            <div className="form-group checkbox-group">
                                <input type="checkbox" id="active" name="active" checked={formData.active || false} onChange={handleChange} />
                                <label htmlFor="active">Casa Ativa</label>
                            </div>

                            <div className="form-actions">
                                <button type="button" className="btn btn-secondary" onClick={handleCloseModal}>Cancelar</button>
                                <button type="submit" className="btn btn-primary" disabled={isSaving}>
                                    {isSaving ? 'Salvando...' : 'Salvar Casa'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
