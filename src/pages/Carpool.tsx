import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { useAuthStore } from '../state/auth';
import { CarFront, Calendar, Users, Phone, Plus } from 'lucide-react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import './Carpool.css';

interface Ride {
    id: number;
    driver_name: string;
    origin: string;
    destination: string;
    ride_datetime: string;
    event_datetime: string;
    available_seats: number;
    whatsapp: string;
    passengers: string;
}

export default function Carpool() {
    const { permissions, user } = useAuthStore();
    const [rides, setRides] = useState<Ride[]>([]);
    const [loading, setLoading] = useState(true);

    if (!permissions?.carona) {
        return <div className="page-container"><h2>Acesso Negado</h2><p>Você não tem permissão para ver esta página.</p></div>;
    }

    useEffect(() => {
        fetchRides();
    }, []);

    const fetchRides = async () => {
        try {
            const now = new Date().toISOString();
            const { data, error } = await supabase
                .from('rides')
                .select('*')
                .gte('ride_datetime', now)
                .order('ride_datetime', { ascending: true });

            if (error) throw error;
            setRides(data || []);
        } catch (err) {
            console.error('Erro ao buscar caronas:', err);
        } finally {
            setLoading(false);
        }
    };

    const joinRide = async (ride: Ride) => {
        if (ride.available_seats <= 0) return alert('Carona lotada!');
        const passengerName = user?.full_name?.split(' ')[0] || user?.username || 'Passageiro';

        // Check if already in passengers
        const passengersList = ride.passengers ? ride.passengers.split(',').map(p => p.trim()) : [];
        if (passengersList.includes(passengerName)) return alert('Você já está nesta carona!');

        const newPassengers = ride.passengers ? `${ride.passengers}, ${passengerName}` : passengerName;
        const newSeats = ride.available_seats - 1;

        try {
            const { error } = await supabase
                .from('rides')
                .update({ passengers: newPassengers, available_seats: newSeats })
                .eq('id', ride.id);

            if (error) throw error;
            fetchRides();
            alert('Vaga garantida com sucesso!');
        } catch (err) {
            console.error('Erro ao entrar na carona:', err);
            alert('Erro ao reservar carona.');
        }
    };

    const leaveRide = async (ride: Ride) => {
        const passengerName = user?.full_name?.split(' ')[0] || user?.username || 'Passageiro';
        let passengersList = ride.passengers ? ride.passengers.split(',').map(p => p.trim()) : [];

        if (!passengersList.includes(passengerName)) return;

        passengersList = passengersList.filter(p => p !== passengerName);
        const newPassengers = passengersList.join(', ');
        const newSeats = ride.available_seats + 1;

        try {
            const { error } = await supabase
                .from('rides')
                .update({ passengers: newPassengers, available_seats: newSeats })
                .eq('id', ride.id);

            if (error) throw error;
            fetchRides();
            alert('Você saiu da carona.');
        } catch (err) {
            console.error('Erro ao sair da carona:', err);
        }
    };

    return (
        <div className="page-container animate-fade-in carpool-page">
            <div className="page-header" style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h2>Carona Solidária</h2>
                    <p className="subtitle">Ofereça ou encontre uma carona para os eventos</p>
                </div>
                {!permissions.readonly && (
                    <button className="btn btn-primary">
                        <Plus size={20} /> Oferecer Carona
                    </button>
                )}
            </div>

            {loading ? (
                <div className="loading-state">Carregando caronas...</div>
            ) : (
                <div className="rides-grid">
                    {rides.length > 0 ? (
                        rides.map(ride => {
                            const passengerName = user?.full_name?.split(' ')[0] || user?.username || '';
                            const isPassenger = ride.passengers && ride.passengers.includes(passengerName);
                            const isDriver = ride.driver_name === user?.full_name;

                            return (
                                <div key={ride.id} className="ride-card glass-effect">
                                    <div className="ride-header">
                                        <div className="driver-info">
                                            <CarFront size={24} color="var(--primary-color)" />
                                            <h3>{ride.driver_name}</h3>
                                        </div>
                                        <div className={`seats-badge ${ride.available_seats > 0 ? 'available' : 'full'}`}>
                                            {ride.available_seats} {ride.available_seats === 1 ? 'vaga' : 'vagas'}
                                        </div>
                                    </div>

                                    <div className="ride-body">
                                        <div className="ride-route">
                                            <div className="route-point">
                                                <div className="route-dot origin" />
                                                <span>{ride.origin}</span>
                                            </div>
                                            <div className="route-line" />
                                            <div className="route-point">
                                                <div className="route-dot destination" />
                                                <span>{ride.destination}</span>
                                            </div>
                                        </div>

                                        <div className="ride-details">
                                            <div className="detail-row">
                                                <Calendar size={16} className="detail-icon" />
                                                <span>Saída: {format(new Date(ride.ride_datetime), "dd/MM 'às' HH:mm", { locale: ptBR })}</span>
                                            </div>
                                            <div className="detail-row">
                                                <Phone size={16} className="detail-icon" />
                                                <span>{ride.whatsapp || 'Não informado'}</span>
                                            </div>
                                            {ride.passengers && (
                                                <div className="passengers-list">
                                                    <Users size={16} className="detail-icon" />
                                                    <span><strong>Passageiros:</strong> {ride.passengers}</span>
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    <div className="ride-actions">
                                        {isDriver ? (
                                            <span className="driver-label">Sua carona</span>
                                        ) : isPassenger ? (
                                            <button onClick={() => leaveRide(ride)} className="btn btn-outline" style={{ width: '100%', color: '#d32f2f', borderColor: '#d32f2f' }}>
                                                Sair da Carona
                                            </button>
                                        ) : (
                                            <button
                                                onClick={() => joinRide(ride)}
                                                className="btn btn-primary"
                                                style={{ width: '100%' }}
                                                disabled={ride.available_seats <= 0}
                                            >
                                                {ride.available_seats > 0 ? 'Garantir Vaga' : 'Lotada'}
                                            </button>
                                        )}
                                    </div>
                                </div>
                            );
                        })
                    ) : (
                        <div className="empty-state">Nenhuma carona disponível para os próximos dias.</div>
                    )}
                </div>
            )}
        </div>
    );
}
