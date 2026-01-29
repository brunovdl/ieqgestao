"""
Módulo de gerenciamento do banco de dados
"""
import sqlite3
from datetime import datetime


class Database:
    """Classe para gerenciar todas as operações do banco de dados"""
    
    def __init__(self, db_name="igreja.db"):
        """
        Inicializa a conexão com o banco de dados
        
        Args:
            db_name (str): Nome do arquivo do banco de dados
        """
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        """Cria as tabelas necessárias no banco de dados"""
        cursor = self.conn.cursor()
        
        # Tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        
        # Tabela de visitantes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS visitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                address TEXT,
                date_visit TEXT,
                observations TEXT
            )
        ''')
        
        # Inserir usuário admin padrão
        cursor.execute(
            "INSERT OR IGNORE INTO users (id, username, password) VALUES (1, 'admin', 'admin123')"
        )
        self.conn.commit()

    def check_login(self, username, password):
        """
        Verifica as credenciais de login
        
        Args:
            username (str): Nome de usuário
            password (str): Senha
            
        Returns:
            tuple ou None: Dados do usuário se credenciais válidas, None caso contrário
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        )
        return cursor.fetchone()

    def add_visitor(self, name, phone, email, address, observations):
        """
        Adiciona um novo visitante ao banco de dados
        
        Args:
            name (str): Nome do visitante
            phone (str): Telefone/WhatsApp
            email (str): E-mail
            address (str): Endereço
            observations (str): Observações
            
        Returns:
            bool: True se sucesso, False se erro
        """
        try:
            cursor = self.conn.cursor()
            date_now = datetime.now().strftime("%d/%m/%Y %H:%M")
            cursor.execute(
                """INSERT INTO visitors (name, phone, email, address, date_visit, observations) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, phone, email, address, date_now, observations)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao adicionar visitante: {e}")
            return False

    def get_all_visitors(self):
        """
        Retorna todos os visitantes cadastrados
        
        Returns:
            list: Lista de tuplas com os dados dos visitantes
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM visitors ORDER BY date_visit DESC")
        return cursor.fetchall()

    def close(self):
        """Fecha a conexão com o banco de dados"""
        self.conn.close()
