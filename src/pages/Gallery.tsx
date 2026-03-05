import { useEffect, useState, useRef } from 'react';
import { supabase } from '../lib/supabase';
import { useAuthStore } from '../state/auth';
import { Camera, Calendar, ArrowLeft, Plus, X, Upload, Trash2 } from 'lucide-react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import './Gallery.css';

interface Album {
    id: number;
    name: string;
    description: string;
    event_date: string;
    cover_url?: string;
}

interface Photo {
    id: number;
    album_id: number;
    storage_path: string;
}

export default function Gallery() {
    const { permissions } = useAuthStore();
    const isAdmin = permissions?.is_admin || false;

    const [albums, setAlbums] = useState<Album[]>([]);
    const [selectedAlbum, setSelectedAlbum] = useState<Album | null>(null);
    const [photos, setPhotos] = useState<Photo[]>([]);
    const [loading, setLoading] = useState(true);

    // Modal State
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [formData, setFormData] = useState<Partial<Album>>({
        name: '', description: '', event_date: new Date().toISOString().split('T')[0]
    });

    // Upload State
    const [isUploading, setIsUploading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        fetchAlbums();
    }, []);

    const fetchAlbums = async () => {
        try {
            setLoading(true);
            const { data, error } = await supabase
                .from('albums')
                .select('*')
                .order('event_date', { ascending: false });

            if (error) throw error;

            let loadedAlbums = data || [];

            // Auto-fix legacy albums that have photos but no cover_url
            const updatedAlbums = await Promise.all(
                loadedAlbums.map(async (album) => {
                    if (!album.cover_url) {
                        const { data: firstPhoto } = await supabase
                            .from('photos')
                            .select('storage_path')
                            .eq('album_id', album.id)
                            .order('created_at', { ascending: true })
                            .limit(1)
                            .single();

                        if (firstPhoto?.storage_path) {
                            // Update DB silently
                            supabase.from('albums').update({ cover_url: firstPhoto.storage_path }).eq('id', album.id).then();
                            return { ...album, cover_url: firstPhoto.storage_path };
                        }
                    }
                    return album;
                })
            );

            setAlbums(updatedAlbums);
        } catch (err) {
            console.error('Erro ao buscar álbuns:', err);
        } finally {
            setLoading(false);
        }
    };

    const openAlbum = async (album: Album) => {
        setSelectedAlbum(album);
        try {
            setLoading(true);
            const { data, error } = await supabase
                .from('photos')
                .select('*')
                .eq('album_id', album.id)
                .order('created_at', { ascending: false });

            if (error) throw error;
            setPhotos(data || []);
        } catch (err) {
            console.error('Erro ao buscar fotos:', err);
        } finally {
            setLoading(false);
        }
    };

    const closeAlbum = () => {
        setSelectedAlbum(null);
        setPhotos([]);
    };

    const getPhotoUrl = (path: string) => {
        const { data } = supabase.storage.from('gallery').getPublicUrl(path);
        return data.publicUrl;
    };

    // Admin Functions
    const handleDeleteAlbum = async (albumId: number) => {
        if (!window.confirm("Certeza que deseja excluir este álbum? Todas as fotos serão perdidas.")) return;
        try {
            // First get all photos
            const { data: albumPhotos } = await supabase.from('photos').select('storage_path').eq('album_id', albumId);
            if (albumPhotos && albumPhotos.length > 0) {
                const paths = albumPhotos.map(p => p.storage_path);
                await supabase.storage.from('gallery').remove(paths);
            }
            // Delete album (this will cascade delete photos if FK allows, but doing it manually is safe)
            await supabase.from('photos').delete().eq('album_id', albumId);
            await supabase.from('albums').delete().eq('id', albumId);

            closeAlbum();
            fetchAlbums();
        } catch (err) {
            console.error("Erro ao excluir álbum", err);
            alert("Erro ao excluir álbum.");
        }
    };

    const handleDeletePhoto = async (photo: Photo) => {
        if (!window.confirm("Excluir esta foto?")) return;
        try {
            await supabase.storage.from('gallery').remove([photo.storage_path]);
            await supabase.from('photos').delete().eq('id', photo.id);

            const remainingPhotos = photos.filter(p => p.id !== photo.id);
            setPhotos(remainingPhotos);

            // If the deleted photo was the cover, update the cover to the next available photo
            if (selectedAlbum?.cover_url === photo.storage_path) {
                const newCoverPath = remainingPhotos.length > 0 ? remainingPhotos[remainingPhotos.length - 1].storage_path : null;

                await supabase.from('albums').update({ cover_url: newCoverPath }).eq('id', selectedAlbum.id);

                setSelectedAlbum({ ...selectedAlbum, cover_url: newCoverPath || undefined });
                setAlbums(prev => prev.map(a => a.id === selectedAlbum.id ? { ...a, cover_url: newCoverPath || undefined } : a));
            }
        } catch (err) {
            console.error("Erro ao excluir foto", err);
        }
    };

    const handleOpenModal = () => {
        setFormData({ name: '', description: '', event_date: new Date().toISOString().split('T')[0] });
        setIsModalOpen(true);
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSaveAlbum = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);
        try {
            const { error } = await supabase.from('albums').insert([formData]);
            if (error) throw error;
            await fetchAlbums();
            setIsModalOpen(false);
        } catch (err) {
            console.error('Erro ao salvar álbum:', err);
            alert('Falha ao criar álbum.');
        } finally {
            setIsSaving(false);
        }
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0 || !selectedAlbum) return;
        setIsUploading(true);

        const files = Array.from(e.target.files);
        let firstUploadPath = '';

        try {
            for (const file of files) {
                const fileExt = file.name.split('.').pop();
                const fileName = `${selectedAlbum.id}/${Math.random().toString(36).substring(2, 15)}_${Date.now()}.${fileExt}`;

                // Upload to storage
                const { error: uploadError } = await supabase.storage
                    .from('gallery')
                    .upload(fileName, file);

                if (uploadError) throw uploadError;

                if (!firstUploadPath) firstUploadPath = fileName;

                // Insert into DB
                const { error: dbError } = await supabase.from('photos').insert([{
                    album_id: selectedAlbum.id,
                    storage_path: fileName
                }]);

                if (dbError) throw dbError;
            }

            // If album has no cover, use the first uploaded photo as cover
            if (!selectedAlbum.cover_url && firstUploadPath) {
                await supabase.from('albums').update({ cover_url: firstUploadPath }).eq('id', selectedAlbum.id);
                // Also update local state so if we go back, we see the cover
                setAlbums(prev => prev.map(a => a.id === selectedAlbum.id ? { ...a, cover_url: firstUploadPath } : a));
                setSelectedAlbum(prev => prev ? { ...prev, cover_url: firstUploadPath } : prev);
            }

            // Refresh photos
            await openAlbum(selectedAlbum);
            alert('Fotos enviadas com sucesso!');
        } catch (err) {
            console.error('Erro ao enviar fotos:', err);
            alert('Erro durante o upload das fotos.');
        } finally {
            setIsUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    return (
        <div className="page-container animate-fade-in gallery-page">
            {!selectedAlbum ? (
                <>
                    <div className="page-header" style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-start', gap: '2rem', width: '100%', textAlign: 'left' }}>
                        <div>
                            <h2 style={{ margin: 0, textAlign: 'left' }}>Galeria</h2>
                            <p className="subtitle" style={{ margin: 0, textAlign: 'left' }}>Lembranças e eventos da IEQ Jd Portugal</p>
                        </div>
                        {isAdmin && (
                            <button className="btn btn-primary" onClick={handleOpenModal}>
                                <Plus size={18} /> Novo Álbum
                            </button>
                        )}
                    </div>

                    {loading ? (
                        <div className="loading-state">Carregando álbuns...</div>
                    ) : (
                        <div className="albums-grid">
                            {albums.length > 0 ? (
                                albums.map(album => (
                                    <div key={album.id} className="album-card glass-effect" onClick={() => openAlbum(album)}>
                                        <div className="album-cover">
                                            {album.cover_url ? (
                                                <img src={getPhotoUrl(album.cover_url)} alt={album.name} loading="lazy" />
                                            ) : (
                                                <div className="album-cover-placeholder">
                                                    <Camera size={48} color="var(--primary-color)" opacity={0.3} />
                                                </div>
                                            )}
                                        </div>
                                        <div className="album-info">
                                            <h3>{album.name}</h3>
                                            <div className="album-date">
                                                <Calendar size={14} />
                                                <span>{album.event_date ? format(new Date(`${album.event_date}T00:00:00`), "dd 'de' MMMM, yyyy", { locale: ptBR }) : 'Data não definida'}</span>
                                            </div>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div className="empty-state">Nenhum álbum encontrado no momento.</div>
                            )}
                        </div>
                    )}

                    {/* Admin Add Album Modal */}
                    {isModalOpen && (
                        <div className="admin-modal-backdrop fadeIn" onClick={() => setIsModalOpen(false)}>
                            <div className="admin-modal-content scaleIn" onClick={(e) => e.stopPropagation()}>
                                <div className="admin-modal-header">
                                    <h3>Criar Novo Álbum</h3>
                                    <button className="close-btn" onClick={() => setIsModalOpen(false)}><X size={24} /></button>
                                </div>
                                <form className="admin-form" onSubmit={handleSaveAlbum}>
                                    <div className="form-group">
                                        <label>Nome do Álbum*</label>
                                        <input required type="text" name="name" value={formData.name || ''} onChange={handleChange} placeholder="Ex: Acampamento de Verão" />
                                    </div>
                                    <div className="form-group">
                                        <label>Descrição</label>
                                        <input type="text" name="description" value={formData.description || ''} onChange={handleChange} placeholder="Breve descrição do evento" />
                                    </div>
                                    <div className="form-group">
                                        <label>Data do Evento*</label>
                                        <input required type="date" name="event_date" value={formData.event_date || ''} onChange={handleChange} />
                                    </div>

                                    <div className="form-actions">
                                        <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>Cancelar</button>
                                        <button type="submit" className="btn btn-primary" disabled={isSaving}>
                                            {isSaving ? 'Salvando...' : 'Criar Álbum'}
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    )}
                </>
            ) : (
                <div className="album-view animate-fade-in">
                    <div className="album-view-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', flexWrap: 'wrap', gap: '1rem' }}>
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                            <button onClick={closeAlbum} className="btn btn-outline back-btn">
                                <ArrowLeft size={18} /> Voltar
                            </button>
                            <div className="album-view-title" style={{ marginLeft: '1rem', textAlign: 'left' }}>
                                <h2 style={{ margin: 0 }}>{selectedAlbum.name}</h2>
                                {selectedAlbum.description && <p style={{ margin: 0, color: 'var(--text-secondary)' }}>{selectedAlbum.description}</p>}
                            </div>
                        </div>

                        {isAdmin && (
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <input
                                    type="file"
                                    multiple
                                    accept="image/*"
                                    style={{ display: 'none' }}
                                    ref={fileInputRef}
                                    onChange={handleFileChange}
                                />
                                <button
                                    className="btn btn-outline"
                                    onClick={() => handleDeleteAlbum(selectedAlbum.id)}
                                    style={{ color: '#c62828', borderColor: '#c62828' }}
                                >
                                    <Trash2 size={18} /> Excluir Álbum
                                </button>
                                <button
                                    className="btn btn-primary"
                                    onClick={() => fileInputRef.current?.click()}
                                    disabled={isUploading}
                                >
                                    {isUploading ? 'Enviando...' : <><Upload size={18} /> Adicionar Fotos</>}
                                </button>
                            </div>
                        )}
                    </div>

                    {loading ? (
                        <div className="loading-state">Carregando fotos...</div>
                    ) : (
                        <div className="photos-masonry">
                            {photos.length > 0 ? (
                                photos.map(photo => (
                                    <div key={photo.id} className="photo-item" style={{ position: 'relative' }}>
                                        <img
                                            src={getPhotoUrl(photo.storage_path)}
                                            alt="Moment"
                                            loading="lazy"
                                        />
                                        {isAdmin && (
                                            <button
                                                onClick={(e) => { e.stopPropagation(); handleDeletePhoto(photo); }}
                                                style={{ position: 'absolute', top: '10px', right: '10px', background: 'rgba(220, 38, 38, 0.9)', color: 'white', border: 'none', borderRadius: '50%', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', zIndex: 20 }}
                                                title="Excluir Foto"
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        )}
                                    </div>
                                ))
                            ) : (
                                <div className="empty-state">Este álbum ainda não possui fotos.</div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
