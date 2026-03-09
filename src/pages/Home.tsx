import { useEffect, useState } from 'react';
import { getBrasiliaDateString } from '../utils/timezone';
import { supabase } from '../lib/supabase';
import { useAuthStore } from '../state/auth';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { MapPin, Clock, ChevronLeft, ChevronRight, Plus, X, Trash2, Edit, Bot, Copy, Calendar } from 'lucide-react';
import './Home.css';

interface AgendaEvent {
    id: number;
    title: string;
    description: string;
    event_date: string;
    event_time: string;
    location: string;
}

export default function Home() {
    const { permissions } = useAuthStore();
    const isAdmin = permissions?.is_admin || false;

    const [events, setEvents] = useState<AgendaEvent[]>([]);
    const [photos, setPhotos] = useState<string[]>([]);
    const [loadingEvents, setLoadingEvents] = useState(true);
    const [loadingPhotos, setLoadingPhotos] = useState(true);
    const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0);

    // Admin Modal State
    const [isEventModalOpen, setIsEventModalOpen] = useState(false);
    const [isSavingEvent, setIsSavingEvent] = useState(false);
    const [eventFormData, setEventFormData] = useState<Partial<AgendaEvent>>({
        title: '', description: '', event_date: getBrasiliaDateString(), event_time: '19:30', location: 'IEQ Jd Portugal'
    });

    // AI Modal State
    const [aiPostText, setAiPostText] = useState('');
    const [isAiModalOpen, setIsAiModalOpen] = useState(false);
    const [isGeneratingAi, setIsGeneratingAi] = useState(false);

    // Event Details Modal State
    const [selectedEvent, setSelectedEvent] = useState<AgendaEvent | null>(null);
    const [isEventDetailsModalOpen, setIsEventDetailsModalOpen] = useState(false);

    useEffect(() => {
        fetchAgenda();
        fetchPhotos();
    }, []);

    // Auto-slide effect for carousel
    useEffect(() => {
        if (photos.length === 0) return;

        const interval = setInterval(() => {
            setCurrentPhotoIndex((prev) => (prev + 1) % photos.length);
        }, 5000);

        return () => clearInterval(interval);
    }, [photos]);

    const fetchAgenda = async () => {
        try {
            const today = getBrasiliaDateString();
            const { data, error } = await supabase
                .from('agenda')
                .select('*')
                .gte('event_date', today)
                .order('event_date', { ascending: true })
                .order('event_time', { ascending: true })
                .limit(5);

            if (error) throw error;
            setEvents(data || []);
        } catch (err) {
            console.error('Erro ao buscar agenda', err);
        } finally {
            setLoadingEvents(false);
        }
    };

    const fetchPhotos = async () => {
        try {
            const { data, error } = await supabase
                .from('photos')
                .select('storage_path')
                .order('created_at', { ascending: false })
                .limit(15);

            if (error) throw error;

            const urls = (data || []).map(p => {
                return supabase.storage.from('gallery').getPublicUrl(p.storage_path).data.publicUrl;
            });
            setPhotos(urls);
        } catch (err) {
            console.error('Erro ao buscar fotos recentes', err);
        } finally {
            setLoadingPhotos(false);
        }
    };

    const nextPhoto = () => setCurrentPhotoIndex((prev) => (prev + 1) % photos.length);
    const prevPhoto = () => setCurrentPhotoIndex((prev) => (prev - 1 + photos.length) % photos.length);

    // Admin Functions
    const handleOpenEventModal = (event?: AgendaEvent) => {
        if (event) {
            setEventFormData(event);
        } else {
            setEventFormData({ title: '', description: '', event_date: getBrasiliaDateString(), event_time: '19:30', location: 'IEQ Jd Portugal' });
        }
        setIsEventModalOpen(true);
    };

    const handleInputEventChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setEventFormData({ ...eventFormData, [e.target.name]: e.target.value });
    };

    const handleSaveEvent = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSavingEvent(true);
        try {
            if (eventFormData.id) {
                const { error } = await supabase.from('agenda').update(eventFormData).eq('id', eventFormData.id);
                if (error) throw error;
            } else {
                const { error } = await supabase.from('agenda').insert([eventFormData]);
                if (error) throw error;
            }
            await fetchAgenda();
            setIsEventModalOpen(false);
        } catch (err) {
            console.error('Erro ao salvar evento', err);
            alert('Falha ao adicionar evento.');
        } finally {
            setIsSavingEvent(false);
        }
    };

    const handleDeleteEvent = async (id: number) => {
        if (!window.confirm('Excluir este evento da agenda?')) return;
        try {
            const { error } = await supabase.from('agenda').delete().eq('id', id);
            if (error) throw error;
            fetchAgenda();
        } catch (err) {
            console.error('Erro ao deletar evento', err);
            alert('Falha ao excluir.');
        }
    };

    const handleGenerateAIPost = async (event: AgendaEvent) => {
        setIsAiModalOpen(true);
        setIsGeneratingAi(true);
        setAiPostText('A IA está a criar o convite. Aguarde um instante...');

        try {
            const apiKey = import.meta.env.VITE_GROQ_API_KEY;
            if (!apiKey) {
                setAiPostText('Erro: Chave da API (VITE_GROQ_API_KEY) não encontrada no ficheiro .env');
                setIsGeneratingAi(false);
                return;
            }

            const prompt = `Crie um texto convidativo, curto e caloroso para o WhatsApp convidando as pessoas para o evento '${event.title}'. Detalhes: Dia ${format(new Date(`${event.event_date}T00:00:00`), 'dd/MM/yyyy')}, às ${event.event_time}, Local: ${event.location}. Descrição do evento: ${event.description || 'Um momento especial de comunhão'}. Não use aspas no início, seja direto, use a linguagem do Brasil num tom amigável para igreja, e inclua emojis.`;

            const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${apiKey}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    model: "llama-3.3-70b-versatile",
                    messages: [{ role: "user", content: prompt }],
                    temperature: 0.7,
                    max_tokens: 300
                })
            });

            const data = await response.json();

            if (data.choices && data.choices.length > 0) {
                setAiPostText(data.choices[0].message.content);
            } else {
                setAiPostText('Não foi possível gerar o texto. Tente novamente.');
            }
        } catch (error) {
            console.error('Erro na IA:', error);
            setAiPostText('Ocorreu um erro ao comunicar com a IA.');
        } finally {
            setIsGeneratingAi(false);
        }
    };

    const copyToClipboard = () => {
        navigator.clipboard.writeText(aiPostText);
        alert('Texto copiado para a área de transferência!');
    };

    return (
        <div className="home-container animate-fade-in">
            {/* Top Carousel and Welcome Banner */}
            <div className="home-header-section">

                {/* Photo Carousel Auto Slider */}
                <div className="carousel-container glass-effect">
                    {loadingPhotos ? (
                        <div className="loading-state">A carregar fotos...</div>
                    ) : photos.length > 0 ? (
                        <div className="slider-wrapper">
                            <button className="slider-btn left" onClick={prevPhoto}><ChevronLeft size={24} /></button>
                            <div className="slider-photos-row">
                                {[0, 1, 2].map((offset) => {
                                    const photoIndex = (currentPhotoIndex + offset) % photos.length;
                                    return (
                                        <div key={`${photoIndex}-${offset}`} className="slider-img-container">
                                            <img src={photos[photoIndex]} alt={`Carousel ${photoIndex}`} className="slider-img animate-fade-in" />
                                        </div>
                                    );
                                })}
                            </div>
                            <button className="slider-btn right" onClick={nextPhoto}><ChevronRight size={24} /></button>

                            <div className="slider-dots">
                                {photos.map((_, idx) => (
                                    <div key={idx} className={`dot ${idx === currentPhotoIndex ? 'active' : ''}`} onClick={() => setCurrentPhotoIndex(idx)} />
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="empty-state">Nenhuma foto recente.</div>
                    )}
                </div>
            </div>

            <div className="home-grid">
                {/* Última Transmissão -> YouTube Uploads Playlist */}
                <div className="video-section glass-effect">
                    <h2>Última Transmissão</h2>
                    <div className="video-wrapper">
                        <iframe
                            src="https://www.youtube.com/embed/videoseries?list=UU9ZL_0IXufvG7iM6F8-FUXQ"
                            title="IEQ Culto Ao Vivo"
                            frameBorder="0"
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                            allowFullScreen
                        ></iframe>
                    </div>
                </div>

                {/* Agenda */}
                <div className="agenda-section glass-effect">
                    <div className="agenda-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h2>Agenda</h2>
                        {(isAdmin || permissions?.eventos) && !permissions?.readonly && (
                            <button className="btn btn-outline" style={{ display: 'flex', alignItems: 'center', gap: '5px', padding: '0.4rem 0.8rem', fontSize: '0.85rem' }} onClick={() => handleOpenEventModal()}>
                                <Plus size={16} /> Novo
                            </button>
                        )}
                    </div>
                    {loadingEvents ? (
                        <div className="loading-state">A carregar agenda...</div>
                    ) : (
                        <div className="agenda-list">
                            {events.map(ev => {
                                const isToday = ev.event_date === getBrasiliaDateString();
                                return (
                                    <div key={ev.id} className={`agenda-card ${isToday ? 'today' : ''}`} onClick={() => { setSelectedEvent(ev); setIsEventDetailsModalOpen(true); }} style={{ cursor: 'pointer' }}>
                                        <div className="agenda-date-box">
                                            <span className="agenda-day">{format(new Date(`${ev.event_date}T00:00:00`), 'dd')}</span>
                                            <span className="agenda-month">{format(new Date(`${ev.event_date}T00:00:00`), 'MMM', { locale: ptBR })}</span>
                                        </div>
                                        <div className="agenda-details">
                                            <h3>{ev.title}</h3>
                                            {ev.description && <p className="agenda-desc">{ev.description}</p>}
                                            <div className="agenda-meta">
                                                <span className="meta-item"><Clock size={14} /> {ev.event_time.slice(0, 5)}</span>
                                                {ev.location && <span className="meta-item"><MapPin size={14} /> {ev.location}</span>}
                                            </div>
                                        </div>
                                        {(isAdmin || permissions?.eventos) && !permissions?.readonly && (
                                            <div style={{ display: 'flex', gap: '0.2rem', marginLeft: '0.5rem', alignSelf: 'flex-start' }}>
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); handleGenerateAIPost(ev); }}
                                                    style={{ background: 'none', border: 'none', color: '#1976d2', cursor: 'pointer', padding: '0.5rem' }}
                                                    title="Gerar Post via IA"
                                                >
                                                    <Bot size={16} />
                                                </button>
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); handleOpenEventModal(ev); }}
                                                    style={{ background: 'none', border: 'none', color: '#f57c00', cursor: 'pointer', padding: '0.5rem' }}
                                                    title="Editar Evento"
                                                >
                                                    <Edit size={16} />
                                                </button>
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); handleDeleteEvent(ev.id); }}
                                                    style={{ background: 'none', border: 'none', color: '#c62828', cursor: 'pointer', padding: '0.5rem' }}
                                                    title="Excluir Evento"
                                                >
                                                    <Trash2 size={16} />
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                )
                            })}
                            {events.length === 0 && <div className="empty-state">Sem eventos para os próximos dias.</div>}
                        </div>
                    )}
                </div>
            </div>

            {/* Admin Add Agenda Event Modal */}
            {(isAdmin || permissions?.eventos) && !permissions?.readonly && isEventModalOpen && (
                <div className="admin-modal-backdrop fadeIn" onClick={() => setIsEventModalOpen(false)}>
                    <div className="admin-modal-content scaleIn" onClick={(e) => e.stopPropagation()}>
                        <div className="admin-modal-header">
                            <h3>Adicionar Evento na Agenda</h3>
                            <button className="close-btn" onClick={() => setIsEventModalOpen(false)}><X size={24} /></button>
                        </div>
                        <form className="admin-form" onSubmit={handleSaveEvent}>
                            <div className="form-group">
                                <label>Título do Culto/Evento*</label>
                                <input required type="text" name="title" value={eventFormData.title || ''} onChange={handleInputEventChange} placeholder="Ex: Culto de Celebração" />
                            </div>
                            <div className="form-group">
                                <label>Descrição</label>
                                <input type="text" name="description" value={eventFormData.description || ''} onChange={handleInputEventChange} placeholder="Ex: Culto da Família" />
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                                <div className="form-group">
                                    <label>Data*</label>
                                    <input required type="date" name="event_date" value={eventFormData.event_date || ''} onChange={handleInputEventChange} />
                                </div>
                                <div className="form-group">
                                    <label>Horário*</label>
                                    <input required type="time" name="event_time" value={eventFormData.event_time || ''} onChange={handleInputEventChange} />
                                </div>
                            </div>
                            <div className="form-group">
                                <label>Local</label>
                                <input type="text" name="location" value={eventFormData.location || ''} onChange={handleInputEventChange} placeholder="Onde ocorrerá o evento" />
                            </div>

                            <div className="form-actions">
                                <button type="button" className="btn btn-secondary" onClick={() => setIsEventModalOpen(false)}>Cancelar</button>
                                <button type="submit" className="btn btn-primary" disabled={isSavingEvent}>
                                    {isSavingEvent ? 'Salvando...' : 'Salvar Evento'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* AI Post Modal */}
            {(isAdmin || permissions?.eventos) && !permissions?.readonly && isAiModalOpen && (
                <div className="admin-modal-backdrop fadeIn" onClick={() => setIsAiModalOpen(false)}>
                    <div className="admin-modal-content scaleIn" onClick={(e) => e.stopPropagation()}>
                        <div className="admin-modal-header">
                            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Bot size={20} /> Gerador de Convite (IA)</h3>
                            <button className="close-btn" onClick={() => setIsAiModalOpen(false)}><X size={24} /></button>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <textarea
                                value={aiPostText}
                                onChange={(e) => setAiPostText(e.target.value)}
                                rows={8}
                                style={{
                                    width: '100%',
                                    padding: '1rem',
                                    borderRadius: 'var(--radius-sm)',
                                    border: '1px solid var(--border-color)',
                                    fontFamily: 'inherit',
                                    resize: 'vertical',
                                    fontSize: '0.95rem',
                                    lineHeight: '1.5'
                                }}
                            />

                            <div className="form-actions">
                                <button type="button" className="btn btn-secondary" onClick={() => setIsAiModalOpen(false)}>Fechar</button>
                                <button type="button" className="btn btn-primary" onClick={copyToClipboard} disabled={isGeneratingAi}>
                                    <Copy size={16} /> Copiar Texto
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
            {/* Event Details Viewer Modal */}
            {isEventDetailsModalOpen && selectedEvent && (
                <div className="admin-modal-backdrop fadeIn" onClick={() => setIsEventDetailsModalOpen(false)}>
                    <div className="admin-modal-content scaleIn" onClick={(e) => e.stopPropagation()}>
                        <div className="admin-modal-header" style={{ marginBottom: '1.5rem' }}>
                            <h3 style={{ fontSize: '1.5rem', margin: 0, color: 'var(--primary-color)' }}>{selectedEvent.title}</h3>
                            <button className="close-btn" onClick={() => setIsEventDetailsModalOpen(false)}><X size={24} /></button>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', color: 'var(--text-secondary)', fontSize: '0.95rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1.25rem' }}>
                                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                    <Calendar size={18} /> {format(new Date(`${selectedEvent.event_date}T00:00:00`), "dd 'de' MMMM 'de' yyyy", { locale: ptBR })}
                                </span>
                                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                    <Clock size={18} /> {selectedEvent.event_time.slice(0, 5)}
                                </span>
                            </div>

                            {selectedEvent.location && (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-primary)', backgroundColor: 'var(--bg-body)', padding: '0.75rem', borderRadius: 'var(--radius-md)' }}>
                                    <MapPin size={20} style={{ color: 'var(--primary-color)' }} />
                                    <span><strong>Localização:</strong> {selectedEvent.location}</span>
                                </div>
                            )}

                            <div style={{ marginTop: '0.5rem' }}>
                                <strong style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Detalhes do Evento:</strong>
                                {selectedEvent.description ? (
                                    <p style={{ lineHeight: '1.6', color: 'var(--text-primary)', whiteSpace: 'pre-wrap', margin: 0, fontSize: '1rem' }}>
                                        {selectedEvent.description}
                                    </p>
                                ) : (
                                    <p style={{ color: 'var(--text-secondary)', fontStyle: 'italic', margin: 0 }}>
                                        Nenhuma informação extra fornecida.
                                    </p>
                                )}
                            </div>

                            <div className="form-actions" style={{ marginTop: '1rem' }}>
                                <button type="button" className="btn btn-primary" onClick={() => setIsEventDetailsModalOpen(false)} style={{ width: '100%' }}>
                                    Fechar
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
