import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { useAuthStore } from '../state/auth';
import { BarChart3, TrendingUp, Users, CalendarDays, Key } from 'lucide-react';
import { subDays } from 'date-fns';
import { getBrasiliaTimestampString } from '../utils/timezone';
import './Analytics.css';

interface StatCardProps {
    title: string;
    value: string | number;
    icon: any;
    color: string;
}

function StatCard({ title, value, icon: Icon, color }: StatCardProps) {
    return (
        <div className="stat-card glass-effect animate-scale-in">
            <div className="stat-icon-wrapper" style={{ backgroundColor: `${color}15`, color }}>
                <Icon size={24} />
            </div>
            <div className="stat-info">
                <h3>{title}</h3>
                <span className="stat-value">{value}</span>
            </div>
        </div>
    );
}

export default function Analytics() {
    const { permissions } = useAuthStore();
    const [stats, setStats] = useState({ today: 0, week: 0, month: 0, total: 0 });
    const [loading, setLoading] = useState(true);

    if (!permissions?.is_admin) {
        return <div className="page-container"><h2>Acesso Negado</h2><p>Você não tem permissão para ver estas métricas.</p></div>;
    }

    useEffect(() => {
        fetchStats();
    }, []);

    const fetchStats = async () => {
        try {
            const now = new Date();
            const formatIso = (d: Date) => getBrasiliaTimestampString(d);
            const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());

            const { count: todayCount } = await supabase.from('page_views').select('*', { count: 'exact', head: true }).gte('viewed_at', formatIso(startOfDay));
            const { count: weekCount } = await supabase.from('page_views').select('*', { count: 'exact', head: true }).gte('viewed_at', formatIso(subDays(now, 7)));
            const { count: monthCount } = await supabase.from('page_views').select('*', { count: 'exact', head: true }).gte('viewed_at', formatIso(subDays(now, 30)));
            const { count: totalCount } = await supabase.from('page_views').select('*', { count: 'exact', head: true });

            setStats({
                today: todayCount || 0,
                week: weekCount || 0,
                month: monthCount || 0,
                total: totalCount || 0
            });
        } catch (err) {
            console.error('Erro no Analytics:', err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="page-container animate-fade-in analytics-page">
            <div className="page-header">
                <h2>Painel de Analytics</h2>
                <p className="subtitle">Visão geral dos acessos à plataforma</p>
            </div>

            {loading ? (
                <div className="loading-state">Carregando métricas...</div>
            ) : (
                <>
                    <div className="stats-grid">
                        <StatCard title="Acessos Hoje" value={stats.today} icon={TrendingUp} color="#1976d2" />
                        <StatCard title="Últimos 7 dias" value={stats.week} icon={CalendarDays} color="#388e3c" />
                        <StatCard title="Últimos 30 dias" value={stats.month} icon={Users} color="#f57c00" />
                        <StatCard title="Total Acumulado" value={stats.total} icon={BarChart3} color="#7b1fa2" />
                    </div>

                    <div className="analytics-notes glass-effect">
                        <div className="notes-header">
                            <Key size={20} color="var(--primary-color)" />
                            <h3>Integração com Logs DB</h3>
                        </div>
                        <p>Os contadores acima operam baseados na tabela <code>page_views</code>, acompanhando as visibilidade através das rotas e sessões persistidas nos dados Supabase. Esta seção pode ser expandida no futuro com bibliotecas de Chart (ex: Recharts) para montagem de gráficos visuais.</p>
                    </div>
                </>
            )}
        </div>
    );
}
