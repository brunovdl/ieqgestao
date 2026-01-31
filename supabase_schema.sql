-- ============================================
-- IEQ Gestão - Schema do Banco de Dados Supabase
-- ============================================

-- Habilitar RLS (Row Level Security)
-- Você pode configurar políticas mais tarde conforme necessário

-- Tabela de Usuários
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT,
    phone TEXT,
    is_admin BOOLEAN DEFAULT FALSE,
    permissions JSONB DEFAULT '{}',
    is_google_auth BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Tabela de Visitantes
CREATE TABLE IF NOT EXISTS visitors (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    address TEXT,
    date_visit TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    observations TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Tabela de Voluntários
CREATE TABLE IF NOT EXISTS volunteers (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    address TEXT,
    role TEXT,
    department TEXT,
    hire_date TEXT,
    registration_date TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    observations TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Tabela de Células (Casa de Cornélio)
CREATE TABLE IF NOT EXISTS cells (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    leader_name TEXT NOT NULL,
    host_name TEXT,
    address TEXT,
    meeting_day TEXT,
    meeting_time TEXT,
    observations TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_visitors_name ON visitors(name);
CREATE INDEX IF NOT EXISTS idx_visitors_date ON visitors(date_visit DESC);
CREATE INDEX IF NOT EXISTS idx_volunteers_name ON volunteers(name);
CREATE INDEX IF NOT EXISTS idx_volunteers_active ON volunteers(active);
CREATE INDEX IF NOT EXISTS idx_cells_name ON cells(name);
CREATE INDEX IF NOT EXISTS idx_cells_active ON cells(active);

-- Função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc', NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers para atualizar updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_visitors_updated_at BEFORE UPDATE ON visitors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_volunteers_updated_at BEFORE UPDATE ON volunteers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cells_updated_at BEFORE UPDATE ON cells
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Inserir usuário admin padrão (senha: admin123)
INSERT INTO users (username, password, is_admin, permissions)
VALUES ('admin', 'admin123', TRUE, '{}')
ON CONFLICT (username) DO NOTHING;

-- ============================================
-- Políticas RLS (Row Level Security) - OPCIONAL
-- ============================================
-- Descomente e ajuste conforme necessário

-- Habilitar RLS nas tabelas
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE visitors ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE volunteers ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE cells ENABLE ROW LEVEL SECURITY;

-- Exemplo: Política para permitir leitura pública (ajuste conforme necessário)
-- CREATE POLICY "Enable read access for all users" ON users FOR SELECT USING (true);
-- CREATE POLICY "Enable read access for all users" ON visitors FOR SELECT USING (true);
-- CREATE POLICY "Enable read access for all users" ON volunteers FOR SELECT USING (true);
-- CREATE POLICY "Enable read access for all users" ON cells FOR SELECT USING (true);

-- Exemplo: Política para permitir inserção/atualização/exclusão (ajuste conforme necessário)
-- CREATE POLICY "Enable all access for authenticated users" ON users FOR ALL USING (auth.role() = 'authenticated');