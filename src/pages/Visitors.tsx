import { useEffect, useState } from 'react';
import { getBrasiliaDateString, getBrasiliaTimestampString } from '../utils/timezone';
import { supabase } from '../lib/supabase';
import { useAuthStore } from '../state/auth';
import { Phone, MapPin, Calendar, CheckSquare, Plus, X, Search, Edit2, MessageSquare, Bot, Trash2, ChevronDown, ChevronUp } from 'lucide-react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import Modal from '../components/Modal';
import { generateAIText } from '../utils/ai';
import './Visitors.css';

interface Visitor {
    id: number;
    name: string;
    phone: string;
    address: string;
    date_visit: string;
    observations: string;
    contacted_by: string;
    contacted_at: string;
}

interface AgendaEvent {
    id: number;
    title: string;
    event_date: string;
}

export default function Visitors() {
    const { permissions, user } = useAuthStore();
    const isAdmin = permissions?.is_admin || false;

    const [visitors, setVisitors] = useState<Visitor[]>([]);
    const [events, setEvents] = useState<AgendaEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedDates, setExpandedDates] = useState<Record<string, boolean>>({});

    // Modal State
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [formData, setFormData] = useState<Partial<Visitor>>({
        name: '', phone: '', address: '', observations: '', date_visit: getBrasiliaDateString()
    });
    const [editingId, setEditingId] = useState<number | null>(null);
    const [cep, setCep] = useState('');
    const [isLoadingCep, setIsLoadingCep] = useState(false);
    const [numero, setNumero] = useState('');
    const [complemento, setComplemento] = useState('');

    // AI Modal State
    const [isAiModalOpen, setIsAiModalOpen] = useState(false);
    const [aiGeneratedText, setAiGeneratedText] = useState('');
    const [isGeneratingAi, setIsGeneratingAi] = useState(false);
    const [currentVisitorPhone, setCurrentVisitorPhone] = useState('');

    // Visitor Details Modal State
    const [selectedVisitor, setSelectedVisitor] = useState<Visitor | null>(null);
    const [isVisitorDetailsModalOpen, setIsVisitorDetailsModalOpen] = useState(false);

    if (!permissions?.visitantes && !isAdmin) {
        return <div className="page-container"><h2>Acesso Negado</h2><p>Você não tem permissão para ver esta página.</p></div>;
    }

    useEffect(() => {
        fetchVisitors();
        fetchEvents();
    }, []);

    const fetchEvents = async () => {
        try {
            const { data, error } = await supabase
                .from('agenda')
                .select('id, title, event_date');
            if (error) throw error;
            setEvents(data || []);
        } catch (err) {
            console.error('Erro ao buscar eventos:', err);
        }
    };

    const fetchVisitors = async () => {
        try {
            const { data, error } = await supabase
                .from('visitors')
                .select('*')
                .order('date_visit', { ascending: false });

            if (error) throw error;
            setVisitors(data || []);

            // Initialize all groups as collapsed by default
            if (data) {
                const uniqueDates = Array.from(new Set(data.map(v => v.date_visit.split('T')[0])));
                const initialExpandedState: Record<string, boolean> = {};
                uniqueDates.forEach(date => {
                    initialExpandedState[date] = false;
                });
                setExpandedDates(initialExpandedState);
            }
        } catch (err) {
            console.error('Erro ao buscar visitantes:', err);
        } finally {
            setLoading(false);
        }
    };

    const fetchCep = async (cepCode: string) => {
        const cleanCep = cepCode.replace(/\D/g, '');
        if (cleanCep.length === 8) {
            setIsLoadingCep(true);
            try {
                const res = await fetch(`https://viacep.com.br/ws/${cleanCep}/json/`);
                const data = await res.json();
                if (!data.erro) {
                    setFormData(prev => ({
                        ...prev,
                        address: `${data.logradouro}, ${data.bairro}, ${data.localidade} - ${data.uf}`
                    }));
                } else {
                    alert('CEP não encontrado.');
                }
            } catch (e) {
                console.error("Erro ao buscar CEP", e);
            } finally {
                setIsLoadingCep(false);
            }
        }
    };

    const markAsContacted = async (id: number) => {
        try {
            const { error } = await supabase
                .from('visitors')
                .update({
                    contacted_by: user?.full_name || user?.username,
                    contacted_at: getBrasiliaTimestampString()
                })
                .eq('id', id);

            if (error) throw error;
            fetchVisitors(); // Reload list
        } catch (err) {
            console.error('Erro ao atualizar visitante:', err);
        }
    };

    const unmarkAsContacted = async (id: number) => {
        if (!window.confirm("Certeza que deseja desmarcar este visitante como contatado?")) return;
        try {
            const { error } = await supabase
                .from('visitors')
                .update({
                    contacted_by: null,
                    contacted_at: null
                })
                .eq('id', id);

            if (error) throw error;
            fetchVisitors(); // Reload list
        } catch (err) {
            console.error('Erro ao atualizar visitante:', err);
            alert('Falha ao desmarcar visitante.');
        }
    };

    const handleDeleteVisitor = async (id: number) => {
        if (!window.confirm("Certeza que deseja excluir este visitante permanentemente?")) return;
        try {
            const { error } = await supabase.from('visitors').delete().eq('id', id);
            if (error) throw error;
            fetchVisitors();
        } catch (err) {
            console.error("Erro ao excluir visitante", err);
            alert("Falha ao excluir visitante.");
        }
    };

    const handleOpenModal = (visitor?: Visitor) => {
        if (visitor) {
            setFormData(visitor);
            setEditingId(visitor.id);
            setCep('');
            setNumero('');
            setComplemento('');
        } else {
            setFormData({ name: '', phone: '', address: '', observations: '', date_visit: getBrasiliaDateString() });
            setEditingId(null);
            setCep('');
            setNumero('');
            setComplemento('');
        }
        setIsModalOpen(true);
    };

    const handleCloseModal = () => setIsModalOpen(false);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSaveVisitor = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);
        try {
            let finalAddress = formData.address || '';
            if (numero && !finalAddress.includes(`Nº ${numero}`)) finalAddress += `, Nº ${numero}`;
            if (complemento && !finalAddress.includes(`${complemento}`)) finalAddress += ` - ${complemento}`;

            const payload = { ...formData, address: finalAddress };

            if (editingId) {
                const { error } = await supabase.from('visitors').update(payload).eq('id', editingId);
                if (error) throw error;
            } else {
                const { error } = await supabase.from('visitors').insert([payload]);
                if (error) throw error;
            }
            await fetchVisitors();
            handleCloseModal();
        } catch (err) {
            console.error('Erro ao salvar visitante:', err);
            alert('Falha ao salvar visitante.');
        } finally {
            setIsSaving(false);
        }
    };

    const handleWhatsAppDirect = (phone: string, text: string = "") => {
        if (!phone) {
            alert("Este visitante não possui telefone cadastrado.");
            return;
        }
        const cleanPhone = phone.replace(/\D/g, '');
        const encodedText = encodeURIComponent(text);
        let url = `https://wa.me/55${cleanPhone}`;
        if (text) url += `?text=${encodedText}`;
        window.open(url, '_blank');
    };

    const handleGenerateAIPost = async (visitor: Visitor) => {
        setCurrentVisitorPhone(visitor.phone);
        setIsAiModalOpen(true);
        setIsGeneratingAi(true);
        setAiGeneratedText('');

        try {
            const prompt = `Crie uma mensagem curta, amigável e calorosa de WhatsApp para um visitante da nossa igreja IEQ Jd Portugal. 
            Nome dele(a): ${visitor.name}. 
            Data da visita: ${visitor.date_visit}. 
            Observações que você pode sutilmente mencionar se fizer sentido (não mencione se não fizer sentido): ${visitor.observations || "Nenhuma"}
            
            O tom deve ser acolhedor, agradecendo a visita, nos colocando à disposição para ajudar no que precisarem, e fazendo um convite para voltarem no próximo culto de celebração neste Domingo às 19h.
            Por favor, não use formatação complexa além de emojis e quebras de linha para WhatsApp.`;

            const systemPrompt = "Você é um assistente de boas-vindas de uma Igreja Evangélica atuando pelo WhatsApp.";
            const text = await generateAIText(prompt, systemPrompt);
            setAiGeneratedText(text);
        } catch (error) {
            console.error("Erro ao gerar post via IA:", error);
            setAiGeneratedText("Desculpe, houve um erro ao comunicar com a inteligência artificial. Tente novamente mais tarde.");
        } finally {
            setIsGeneratingAi(false);
        }
    };

    const toggleGroup = (dateStr: string) => {
        setExpandedDates(prev => ({
            ...prev,
            [dateStr]: !prev[dateStr]
        }));
    };

    // Group visitors by date
    const groupedVisitors = visitors.reduce((acc, visitor) => {
        const dateKey = visitor.date_visit.split('T')[0];
        if (!acc[dateKey]) {
            acc[dateKey] = [];
        }
        acc[dateKey].push(visitor);
        return acc;
    }, {} as Record<string, Visitor[]>);

    // Sort dates descending
    const sortedDates = Object.keys(groupedVisitors).sort((a, b) => new Date(b).getTime() - new Date(a).getTime());

    // Calculate global stats
    const totalVisitorsCount = visitors.length;
    const totalContactedCount = visitors.filter(v => v.contacted_at).length;
    const totalPendingCount = visitors.filter(v => !v.contacted_at).length;

    return (
        <>
            <div className="page-container animate-fade-in visitors-page">
                <div className="page-header" style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-start', gap: '2rem', width: '100%', textAlign: 'left' }}>
                <div style={{ textAlign: 'left' }}>
                    <h2 style={{ margin: 0, textAlign: 'left' }}>Registro de Visitantes</h2>
                    <p className="subtitle" style={{ margin: 0, textAlign: 'left' }}>Histórico de pessoas que visitaram a igreja</p>
                </div>
                {(isAdmin || permissions?.visitantes) && !permissions?.readonly && (
                    <button className="btn btn-primary" onClick={() => handleOpenModal()}>
                        <Plus size={18} /> Novo Visitante
                    </button>
                )}
            </div>

            {!loading && visitors.length > 0 && (
                <div className="visitors-stats" style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
                    <div className="stat-card" style={{ flex: 1, minWidth: '150px', padding: '1rem', backgroundColor: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.25rem', boxShadow: 'var(--shadow-sm)' }}>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Total de Visitantes</span>
                        <strong style={{ fontSize: '1.5rem', color: 'var(--text-primary)' }}>{totalVisitorsCount}</strong>
                    </div>
                    <div className="stat-card" style={{ flex: 1, minWidth: '150px', padding: '1rem', backgroundColor: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.25rem', boxShadow: 'var(--shadow-sm)' }}>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Contatados</span>
                        <strong style={{ fontSize: '1.5rem', color: '#2e7d32' }}>{totalContactedCount}</strong>
                    </div>
                    <div className="stat-card" style={{ flex: 1, minWidth: '150px', padding: '1rem', backgroundColor: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.25rem', boxShadow: 'var(--shadow-sm)' }}>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Pendentes</span>
                        <strong style={{ fontSize: '1.5rem', color: '#d32f2f' }}>{totalPendingCount}</strong>
                    </div>
                </div>
            )}

            {loading ? (
                <div className="loading-state">Carregando visitantes...</div>
            ) : (
                <div className="visitors-list">
                    {sortedDates.length > 0 ? (
                        sortedDates.map(dateKey => {
                            const groupVisitors = groupedVisitors[dateKey];
                            const isExpanded = expandedDates[dateKey];
                            const relatedEvent = events.find(ev => ev.event_date === dateKey);
                            const formattedDate = format(new Date(`${dateKey}T00:00:00`), "dd/MM/yyyy", { locale: ptBR });
                            const groupTitle = relatedEvent ? `${relatedEvent.title} - ${formattedDate}` : `Visitas: ${formattedDate}`;

                            const groupContacted = groupVisitors.filter(v => v.contacted_at).length;
                            const groupPending = groupVisitors.filter(v => !v.contacted_at).length;

                            return (
                                <div key={dateKey} className="visitor-group" style={{ marginBottom: '1.5rem' }}>
                                    <div
                                        className="visitor-group-header"
                                        onClick={() => toggleGroup(dateKey)}
                                        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', backgroundColor: 'var(--bg-card)', borderRadius: 'var(--radius-md)', cursor: 'pointer', border: '1px solid var(--border-color)', marginBottom: '0.5rem', boxShadow: 'var(--shadow-sm)' }}
                                    >
                                        <h3 style={{ margin: 0, fontSize: '1.1rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                                            <Calendar size={18} style={{ color: 'var(--primary-color)' }} />
                                            {groupTitle} 
                                            <div style={{ display: 'flex', gap: '0.5rem', marginLeft: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                                                <span style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', borderRadius: '1rem', backgroundColor: 'var(--bg-body)', color: 'var(--text-secondary)' }}>
                                                    Total: {groupVisitors.length}
                                                </span>
                                                {groupContacted > 0 && (
                                                    <span style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem', borderRadius: '1rem', backgroundColor: 'rgba(46, 125, 50, 0.1)', color: '#2e7d32', border: '1px solid rgba(46, 125, 50, 0.2)' }}>
                                                        {groupContacted} {groupContacted === 1 ? 'Contatado' : 'Contatados'}
                                                    </span>
                                                )}
                                                {groupPending > 0 && (
                                                    <span style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem', borderRadius: '1rem', backgroundColor: 'rgba(211, 47, 47, 0.1)', color: '#d32f2f', border: '1px solid rgba(211, 47, 47, 0.2)' }}>
                                                        {groupPending} {groupPending === 1 ? 'Pendente' : 'Pendentes'}
                                                    </span>
                                                )}
                                            </div>
                                        </h3>
                                        <div style={{ color: 'var(--text-secondary)' }}>
                                            {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                                        </div>
                                    </div>

                                    {isExpanded && (
                                        <div className="visitor-group-content" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', paddingLeft: '0.5rem' }}>
                                            {[...groupVisitors]
                                                .sort((a, b) => {
                                                    if (a.contacted_at && !b.contacted_at) return 1;
                                                    if (!a.contacted_at && b.contacted_at) return -1;
                                                    return 0;
                                                })
                                                .map(visitor => (
                                                <div
                                                    key={visitor.id}
                                                    className={`visitor-card glass-effect ${visitor.contacted_at ? 'contacted' : 'pending'}`}
                                                    onClick={() => { setSelectedVisitor(visitor); setIsVisitorDetailsModalOpen(true); }}
                                                    style={{ cursor: 'pointer', padding: '1rem' }}
                                                >
                                                    <div className="visitor-header" style={{ marginBottom: 0 }}>
                                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                                                            <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{visitor.name}</h3>
                                                            {visitor.phone && (
                                                                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                                                    {visitor.phone}
                                                                </div>
                                                            )}
                                                        </div>
                                                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                                            <div className={`status-badge ${visitor.contacted_at ? 'active' : 'inactive'}`}>
                                                                {visitor.contacted_at ? 'Contatado' : 'Pendente'}
                                                            </div>
                                                            {!permissions?.readonly && (isAdmin || permissions?.visitantes) && (
                                                                <button
                                                                    className="icon-btn"
                                                                    onClick={(e) => { e.stopPropagation(); handleOpenModal(visitor); }}
                                                                    title="Editar Visitante"
                                                                >
                                                                    <Edit2 size={16} />
                                                                </button>
                                                            )}
                                                            {!permissions?.readonly && (isAdmin || permissions?.visitantes) && (
                                                                <button
                                                                    className="icon-btn"
                                                                    onClick={(e) => { e.stopPropagation(); handleDeleteVisitor(visitor.id); }}
                                                                    title="Excluir Visitante"
                                                                    style={{ color: '#c62828' }}
                                                                >
                                                                    <Trash2 size={16} />
                                                                </button>
                                                            )}
                                                        </div>
                                                    </div>

                                                    {!visitor.contacted_at && !permissions?.readonly && (
                                                        <div className="visitor-actions-compact" style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem', flexWrap: 'wrap', justifyContent: 'flex-start' }}>
                                                            <button onClick={(e) => { e.stopPropagation(); handleWhatsAppDirect(visitor.phone); }} className="btn btn-outline" style={{ fontSize: '0.75rem', padding: '0.4rem 0.6rem', color: '#25D366', borderColor: '#25D366', display: 'flex', alignItems: 'center', gap: '4px' }} title="Iniciar conversa no WhatsApp">
                                                                <MessageSquare size={14} /> Msg
                                                            </button>
                                                            <button onClick={(e) => { e.stopPropagation(); handleGenerateAIPost(visitor); }} className="btn btn-outline" style={{ fontSize: '0.75rem', padding: '0.4rem 0.6rem', color: 'var(--primary-color)', borderColor: 'var(--primary-color)', display: 'flex', alignItems: 'center', gap: '4px' }} title="Esboçar mensagem com IA">
                                                                <Bot size={14} /> IA
                                                            </button>
                                                            <button onClick={(e) => { e.stopPropagation(); markAsContacted(visitor.id); }} className="btn btn-outline" style={{ fontSize: '0.75rem', padding: '0.4rem 0.6rem', color: '#2e7d32', borderColor: '#2e7d32', display: 'flex', alignItems: 'center', gap: '4px' }} title="Marcar como Contatado">
                                                                <CheckSquare size={14} /> Contatado
                                                            </button>
                                                        </div>
                                                    )}
                                                    {visitor.contacted_at && !permissions?.readonly && (isAdmin || user?.full_name === visitor.contacted_by || user?.username === visitor.contacted_by) && (
                                                        <div className="visitor-actions-compact" style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem', flexWrap: 'wrap', justifyContent: 'flex-start' }}>
                                                            <button onClick={(e) => { e.stopPropagation(); unmarkAsContacted(visitor.id); }} className="btn btn-outline" style={{ fontSize: '0.75rem', padding: '0.4rem 0.6rem', color: '#d32f2f', borderColor: '#d32f2f', display: 'flex', alignItems: 'center', gap: '4px' }} title="Desmarcar Contato">
                                                                <X size={14} /> Desmarcar
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            );
                        })
                    ) : (
                        <div className="empty-state">Nenhum visitante registrado.</div>
                    )}
                </div>
            )}
            </div>

            {/* Admin Add Visitor Modal */}
            <Modal isOpen={isModalOpen} onClose={handleCloseModal} title={editingId ? 'Editar Visitante' : 'Registrar Novo Visitante'} maxWidth="600px">
                <form className="admin-form" onSubmit={handleSaveVisitor}>
                    <div className="form-group">
                        <label>Nome Completo*</label>
                        <input required type="text" name="name" value={formData.name || ''} onChange={handleChange} placeholder="Nome do visitante" />
                    </div>
                    <div className="form-row grid-1-1">
                        <div className="form-group">
                            <label>Telefone/WhatsApp</label>
                            <input type="tel" name="phone" value={formData.phone || ''} onChange={handleChange} placeholder="(00) 00000-0000" />
                        </div>
                        <div className="form-group">
                            <label>Data da Visita*</label>
                            <input required type="date" name="date_visit" value={formData.date_visit || ''} onChange={handleChange} />
                        </div>
                    </div>
                    <div className="form-group">
                        <label>CEP (Busca Automática)</label>
                        <div className="cep-input-group" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                            <input
                                type="text"
                                value={cep}
                                onChange={(e) => {
                                    setCep(e.target.value);
                                    if (e.target.value.replace(/\D/g, '').length === 8) {
                                        fetchCep(e.target.value);
                                    }
                                }}
                                placeholder="00000-000"
                                style={{ flex: '1 1 min-content', minWidth: '150px' }}
                                maxLength={9}
                            />
                            <button
                                type="button"
                                className="btn btn-secondary"
                                onClick={() => fetchCep(cep)}
                                disabled={isLoadingCep}
                                style={{ flex: '1 1 auto', whiteSpace: 'nowrap' }}
                            >
                                <Search size={16} /> {isLoadingCep ? 'Buscando...' : 'Buscar'}
                            </button>
                        </div>
                    </div>
                    <div className="form-group">
                        <label>Logradouro / Rua</label>
                        <input type="text" name="address" value={formData.address || ''} onChange={handleChange} placeholder="Av Paulista, Bairro, Cidade - UF" />
                    </div>
                    <div className="form-row grid-1-2">
                        <div className="form-group">
                            <label>Número</label>
                            <input type="text" value={numero} onChange={(e) => setNumero(e.target.value)} placeholder="S/N" />
                        </div>
                        <div className="form-group">
                            <label>Complemento</label>
                            <input type="text" value={complemento} onChange={(e) => setComplemento(e.target.value)} placeholder="Apto, Bloco, Casa" />
                        </div>
                    </div>
                    <div className="form-group">
                        <label>Observações</label>
                        <textarea
                            name="observations"
                            value={formData.observations || ''}
                            onChange={handleChange}
                            placeholder="Ex: Veio através de um amigo, deseja participar da célula..."
                            rows={3}
                            style={{ padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', fontFamily: 'inherit', resize: 'vertical' }}
                        />
                    </div>

                    <div className="form-actions">
                        <button type="button" className="btn btn-secondary" onClick={handleCloseModal}>Cancelar</button>
                        <button type="submit" className="btn btn-primary" disabled={isSaving}>
                            {isSaving ? 'Salvando...' : 'Salvar Visitante'}
                        </button>
                    </div>
                </form>
            </Modal>

            {/* AI Generation Modal */}
            <Modal isOpen={isAiModalOpen} onClose={() => setIsAiModalOpen(false)} title={<span style={{ display: 'flex', alignItems: 'center' }}><Bot size={20} style={{ marginRight: '8px', color: 'var(--primary-color)' }} /> Gerador de Boas-vindas IA</span>} maxWidth="500px">
                <div className="admin-form" style={{ gap: '1rem', display: 'flex', flexDirection: 'column' }}>
                    {isGeneratingAi ? (
                        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                            <Bot size={48} style={{ marginBottom: '1rem', opacity: 0.5, animation: 'pulse 2s infinite' }} />
                            <p>A Inteligência Artificial está escrevendo sua mensagem de boas-vindas...</p>
                        </div>
                    ) : (
                        <>
                            <p style={{ margin: 0, fontSize: '0.95rem', color: 'var(--text-secondary)' }}>
                                Abaixo está uma sugestão de mensagem gerada pela IA para acolher este visitante. Sinta-se à vontade para alterá-la antes de enviar.
                            </p>
                            <textarea
                                value={aiGeneratedText}
                                onChange={(e) => setAiGeneratedText(e.target.value)}
                                rows={8}
                                style={{ width: '100%', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', resize: 'vertical', fontFamily: 'inherit', lineHeight: '1.5' }}
                            />
                            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
                                <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setIsAiModalOpen(false)}>
                                    Cancelar
                                </button>
                                <button
                                    className="btn btn-primary"
                                    style={{ flex: 1, backgroundColor: '#25D366' }}
                                    onClick={() => {
                                        handleWhatsAppDirect(currentVisitorPhone, aiGeneratedText);
                                        setIsAiModalOpen(false);
                                    }}
                                >
                                    <MessageSquare size={18} /> Enviar via WhatsApp
                                </button>
                            </div>
                        </>
                    )}
                </div>
            </Modal>

            {/* Visitor Details Viewer Modal */}
            {selectedVisitor && (
                <Modal 
                    isOpen={isVisitorDetailsModalOpen} 
                    onClose={() => setIsVisitorDetailsModalOpen(false)} 
                    title={
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            <span style={{ fontSize: '1.5rem', color: 'var(--primary-color)', fontWeight: 'bold' }}>{selectedVisitor.name}</span>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <span className={`status-badge ${selectedVisitor.contacted_at ? 'active' : 'inactive'}`} style={{ margin: 0 }}>
                                    {selectedVisitor.contacted_at ? 'Contatado' : 'Pendente'}
                                </span>
                            </div>
                        </div>
                    } 
                    headerStyle={{ marginBottom: '1.5rem', alignItems: 'flex-start' }}
                >
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                        {selectedVisitor.phone && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-primary)', backgroundColor: 'var(--bg-body)', padding: '0.75rem', borderRadius: 'var(--radius-md)' }}>
                                <Phone size={20} style={{ color: 'var(--primary-color)' }} />
                                <span><strong>Telefone/WhatsApp:</strong> {selectedVisitor.phone}</span>
                            </div>
                        )}

                        {selectedVisitor.address && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-primary)', backgroundColor: 'var(--bg-body)', padding: '0.75rem', borderRadius: 'var(--radius-md)' }}>
                                <MapPin size={20} style={{ color: 'var(--primary-color)' }} />
                                <span><strong>Endereço:</strong> {selectedVisitor.address}</span>
                            </div>
                        )}

                        {selectedVisitor.observations && (
                            <div style={{ marginTop: '0.5rem' }}>
                                <strong style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Observações:</strong>
                                <p style={{ lineHeight: '1.6', color: 'var(--text-primary)', whiteSpace: 'pre-wrap', margin: 0, fontSize: '1rem', backgroundColor: 'var(--bg-body)', padding: '0.75rem', borderRadius: 'var(--radius-md)' }}>
                                    {selectedVisitor.observations}
                                </p>
                            </div>
                        )}

                        {selectedVisitor.contacted_at && (
                            <div style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                                <strong><CheckSquare size={16} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '4px' }} /> Contatado por:</strong> {selectedVisitor.contacted_by} em {
                                    (() => {
                                        try {
                                            return format(new Date(selectedVisitor.contacted_at), "dd/MM/yyyy HH:mm");
                                        } catch (e) {
                                            return selectedVisitor.contacted_at;
                                        }
                                    })()
                                }
                            </div>
                        )}

                        <div className="form-actions" style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                            {!selectedVisitor.contacted_at && !permissions?.readonly && (
                                <>
                                    <button onClick={() => { setIsVisitorDetailsModalOpen(false); handleWhatsAppDirect(selectedVisitor.phone); }} className="btn btn-outline" style={{ flex: 1, minWidth: '140px', color: '#25D366', borderColor: '#25D366' }}>
                                        <MessageSquare size={16} /> WhatsApp
                                    </button>
                                    <button onClick={() => { setIsVisitorDetailsModalOpen(false); handleGenerateAIPost(selectedVisitor); }} className="btn btn-outline" style={{ flex: 1, minWidth: '140px', color: 'var(--primary-color)', borderColor: 'var(--primary-color)' }}>
                                        <Bot size={16} /> IA P/ Conversa
                                    </button>
                                    <button onClick={() => { setIsVisitorDetailsModalOpen(false); markAsContacted(selectedVisitor.id); }} className="btn btn-outline" style={{ width: '100%', color: '#2e7d32', borderColor: '#2e7d32' }}>
                                        <CheckSquare size={18} /> Marcar Contatado
                                    </button>
                                </>
                            )}
                            {selectedVisitor.contacted_at && !permissions?.readonly && (isAdmin || user?.full_name === selectedVisitor.contacted_by || user?.username === selectedVisitor.contacted_by) && (
                                <button onClick={() => { setIsVisitorDetailsModalOpen(false); unmarkAsContacted(selectedVisitor.id); }} className="btn btn-outline" style={{ width: '100%', color: '#d32f2f', borderColor: '#d32f2f' }}>
                                    <X size={18} /> Desmarcar Contato
                                </button>
                            )}

                        </div>
                    </div>
                </Modal>
            )}
        </>
    );
}
