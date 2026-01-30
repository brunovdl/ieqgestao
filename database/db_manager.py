"""
Módulo de gerenciamento do banco de dados
"""
import sqlite3
from datetime import datetime
import json


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
        
        # Tabela de usuários com campos de permissão
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                permissions TEXT DEFAULT '{}'
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
        
        # Tabela de colaboradores
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collaborators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                address TEXT,
                role TEXT,
                department TEXT,
                hire_date TEXT,
                registration_date TEXT,
                observations TEXT,
                active INTEGER DEFAULT 1
            )
        ''')
        
        # Inserir usuário admin padrão com permissões totais
        cursor.execute(
            """INSERT OR IGNORE INTO users (id, username, password, is_admin, permissions) 
               VALUES (1, 'admin', 'admin123', 1, '{}')"""
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
    
    def add_collaborator(self, name, phone, email, address, role, department, hire_date, observations):
        """
        Adiciona um novo colaborador ao banco de dados
        
        Args:
            name (str): Nome do colaborador
            phone (str): Telefone/WhatsApp
            email (str): E-mail
            address (str): Endereço
            role (str): Cargo/Função
            department (str): Departamento
            hire_date (str): Data de contratação
            observations (str): Observações
            
        Returns:
            bool: True se sucesso, False se erro
        """
        try:
            cursor = self.conn.cursor()
            date_now = datetime.now().strftime("%d/%m/%Y %H:%M")
            cursor.execute(
                """INSERT INTO collaborators (name, phone, email, address, role, department, 
                   hire_date, registration_date, observations, active) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, phone, email, address, role, department, hire_date, date_now, observations, 1)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao adicionar colaborador: {e}")
            return False

    def get_all_collaborators(self, active_only=True):
        """
        Retorna todos os colaboradores cadastrados
        
        Args:
            active_only (bool): Se True, retorna apenas ativos
            
        Returns:
            list: Lista de tuplas com os dados dos colaboradores
        """
        cursor = self.conn.cursor()
        if active_only:
            cursor.execute("SELECT * FROM collaborators WHERE active = 1 ORDER BY name")
        else:
            cursor.execute("SELECT * FROM collaborators ORDER BY name")
        return cursor.fetchall()

    def update_collaborator(self, collab_id, **kwargs):
        """
        Atualiza dados de um colaborador
        
        Args:
            collab_id (int): ID do colaborador
            **kwargs: Campos a atualizar
            
        Returns:
            bool: True se sucesso, False se erro
        """
        try:
            cursor = self.conn.cursor()
            updates = []
            params = []
            
            allowed_fields = ['name', 'phone', 'email', 'address', 'role', 
                            'department', 'hire_date', 'observations', 'active']
            
            for field, value in kwargs.items():
                if field in allowed_fields:
                    updates.append(f"{field} = ?")
                    params.append(value)
            
            if not updates:
                return False
            
            params.append(collab_id)
            query = f"UPDATE collaborators SET {', '.join(updates)} WHERE id = ?"
            
            cursor.execute(query, params)
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao atualizar colaborador: {e}")
            return False

    def deactivate_collaborator(self, collab_id):
        """
        Desativa um colaborador (não deleta)
        
        Args:
            collab_id (int): ID do colaborador
            
        Returns:
            bool: True se sucesso, False se erro
        """
        return self.update_collaborator(collab_id, active=0)

    def get_user_by_username(self, username):
        """
        Busca usuário pelo username
        
        Args:
            username (str): Nome de usuário
            
        Returns:
            tuple ou None: Dados do usuário
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        return cursor.fetchone()

    def add_user(self, username, password, is_admin=False, permissions=None):
        """
        Adiciona um novo usuário ao sistema
        
        Args:
            username (str): Nome de usuário
            password (str): Senha
            is_admin (bool): Se é administrador
            permissions (dict): Permissões
            
        Returns:
            bool: True se sucesso, False se erro
        """
        try:
            cursor = self.conn.cursor()
            # Converte permissões para JSON string
            perms_json = json.dumps(permissions) if permissions else json.dumps({})
            
            cursor.execute(
                """INSERT INTO users (username, password, is_admin, permissions) 
                   VALUES (?, ?, ?, ?)""",
                (username, password, 1 if is_admin else 0, perms_json)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao adicionar usuário: {e}")
            return False

    def get_all_users(self):
        """
        Retorna todos os usuários cadastrados
        
        Returns:
            list: Lista de tuplas com dados dos usuários
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, username, is_admin, permissions FROM users ORDER BY username")
        return cursor.fetchall()

    def update_user(self, user_id, username=None, password=None, is_admin=None, permissions=None):
        """
        Atualiza dados de um usuário
        
        Args:
            user_id (int): ID do usuário
            username (str): Novo nome de usuário
            password (str): Nova senha
            is_admin (bool): Se é admin
            permissions (dict): Permissões
            
        Returns:
            bool: True se sucesso, False se erro
        """
        try:
            cursor = self.conn.cursor()
            
            updates = []
            params = []
            
            if username is not None:
                updates.append("username = ?")
                params.append(username)
            
            if password is not None:
                updates.append("password = ?")
                params.append(password)
            
            if is_admin is not None:
                updates.append("is_admin = ?")
                params.append(1 if is_admin else 0)
            
            if permissions is not None:
                updates.append("permissions = ?")
                params.append(json.dumps(permissions))
            
            if not updates:
                return False
            
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            
            cursor.execute(query, params)
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao atualizar usuário: {e}")
            return False

    def delete_user(self, user_id):
        """
        Remove um usuário
        
        Args:
            user_id (int): ID do usuário
            
        Returns:
            bool: True se sucesso, False se erro
        """
        try:
            # Não permite deletar o admin principal
            if user_id == 1:
                return False
            
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao deletar usuário: {e}")
            return False

    def get_user_permissions(self, username):
        """
        Retorna as permissões de um usuário
        
        Args:
            username (str): Nome de usuário
            
        Returns:
            dict: Dicionário com permissões
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT permissions, is_admin FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        
        if result:
            permissions_json, is_admin = result
            # Se é admin, tem todas as permissões
            if is_admin:
                return {
                    "visitantes": True,
                    "celulas": True,
                    "usuarios": True,
                    "relatorios": True
                }
            # Caso contrário, retorna as permissões específicas
            try:
                return json.loads(permissions_json) if permissions_json else {}
            except:
                return {}
        
        return {}

    def close(self):
        """Fecha a conexão com o banco de dados"""
        self.conn.close()