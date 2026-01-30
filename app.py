"""
IEQ Gestão - Sistema Integrado de Gestão Eclesiástica
VERSÃO COM FEEDBACKS VISUAIS COMPLETOS E CORREÇÕES
"""
import flet as ft
import sqlite3
import json
import requests
import time
import urllib.parse
from datetime import datetime
from typing import Optional, Dict

# ==============================================================================
# CONFIGURAÇÕES E UTILITÁRIOS
# ==============================================================================

APP_TITLE = "IEQ - Gestão Integrada"
DB_NAME = "igrejajdportugal.db" 
THEME_COLOR = "#1976D2"  # Azul IEQ

# ==============================================================================
# FUNÇÕES DE FEEDBACK VISUAL
# ==============================================================================

def show_success(page, message):
    """Exibe mensagem de sucesso"""
    page.snack_bar = ft.SnackBar(
        content=ft.Row([
            ft.Icon(ft.Icons.CHECK_CIRCLE, color="white"),
            ft.Text(message, color="white")
        ]),
        bgcolor="green"
    )
    page.snack_bar.open = True
    page.update()

def show_error(page, message):
    """Exibe mensagem de erro"""
    page.snack_bar = ft.SnackBar(
        content=ft.Row([
            ft.Icon(ft.Icons.ERROR, color="white"),
            ft.Text(message, color="white")
        ]),
        bgcolor="red"
    )
    page.snack_bar.open = True
    page.update()

def show_warning(page, message):
    """Exibe mensagem de aviso"""
    page.snack_bar = ft.SnackBar(
        content=ft.Row([
            ft.Icon(ft.Icons.WARNING, color="white"),
            ft.Text(message, color="white")
        ]),
        bgcolor="orange"
    )
    page.snack_bar.open = True
    page.update()

def show_info(page, message):
    """Exibe mensagem informativa"""
    page.snack_bar = ft.SnackBar(
        content=ft.Row([
            ft.Icon(ft.Icons.INFO, color="white"),
            ft.Text(message, color="white")
        ]),
        bgcolor="blue"
    )
    page.snack_bar.open = True
    page.update()

def show_loading(page, message="Processando..."):
    """Mostra um indicador de carregamento"""
    loading_container = ft.Container(
        content=ft.Column([
            ft.ProgressRing(),
            ft.Text(message, color="white")
        ], 
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=20),
        bgcolor="black54",
        expand=True
    )
    page.overlay.append(loading_container)
    page.update()
    return loading_container

def hide_loading(page, loading_container):
    """Remove o indicador de carregamento"""
    if loading_container in page.overlay:
        page.overlay.remove(loading_container)
    page.update()

class ViaCEPService:
    """Serviço para buscar endereços via CEP"""
    BASE_URL = "https://viacep.com.br/ws"
    
    @staticmethod
    def clean_cep(cep: str) -> str:
        if not cep: return ""
        return ''.join(filter(str.isdigit, cep))
    
    @staticmethod
    def format_cep(cep: str) -> str:
        clean = ViaCEPService.clean_cep(cep)
        if len(clean) == 8:
            return f"{clean[:5]}-{clean[5:]}"
        return cep
    
    @staticmethod
    def search_by_cep(cep: str) -> Optional[Dict[str, str]]:
        try:
            clean_cep = ViaCEPService.clean_cep(cep)
            if len(clean_cep) != 8: return None
            
            response = requests.get(f"{ViaCEPService.BASE_URL}/{clean_cep}/json/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'erro' not in data: return data
            return None
        except Exception as e:
            print(f"Erro CEP: {e}")
            return None

def open_whatsapp(phone, name):
    """Gera a URL do WhatsApp Web/App com uma mensagem inicial"""
    if not phone:
        return ""
    
    # Limpa o número (apenas dígitos)
    clean_phone = ''.join(filter(str.isdigit, phone))
    
    # Adiciona código do país se não tiver (assumindo Brasil +55)
    if len(clean_phone) <= 11 and not clean_phone.startswith("55"):
        clean_phone = "55" + clean_phone
        
    message = f"Olá {name}, paz! Sou da IEQ."
    encoded_message = urllib.parse.quote(message)
    url = f"https://wa.me/{clean_phone}?text={encoded_message}"
    return url

# ==============================================================================
# CAMADA DE DADOS (DATABASE)
# ==============================================================================

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT,
                phone TEXT,
                is_admin INTEGER DEFAULT 0,
                permissions TEXT DEFAULT '{}',
                is_google_auth INTEGER DEFAULT 0
            )
        ''')
        
        # Visitantes
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
        
        # Voluntários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS volunteers (
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

        # Casa de Cornélio
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cells (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                leader_name TEXT NOT NULL,
                host_name TEXT,
                address TEXT,
                meeting_day TEXT,
                meeting_time TEXT,
                observations TEXT,
                active INTEGER DEFAULT 1
            )
        ''')
        
        # Admin Padrão
        cursor.execute("SELECT count(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO users (username, password, is_admin, permissions) VALUES (?, ?, ?, ?)",
                ('admin', 'admin123', 1, '{}')
            )
            
        self.conn.commit()

    # --- Auth ---
    def check_login(self, username, password):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        return cursor.fetchone()
    
    def check_user_exists(self, username):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        return cursor.fetchone()

    def get_user_permissions(self, username):
        cursor = self.conn.cursor()
        cursor.execute("SELECT permissions, is_admin FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        if result:
            perms_json, is_admin = result
            if is_admin:
                return {
                    "visitantes": True, "celulas": True, 
                    "usuarios": True, "voluntários": True, 
                    "readonly": False, "lista_visitantes": True
                }
            try:
                perms = json.loads(perms_json) if perms_json else {}
                if perms.get("visitantes"):
                    perms["lista_visitantes"] = True
                return perms
            except:
                return {}
        return {}

    # --- Cadastro ---
    def add_user(self, username, password, is_admin, perms, phone=None, is_google=False):
        try:
            self.conn.execute(
                """INSERT INTO users (username, password, is_admin, permissions, phone, is_google_auth) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (username, password, 1 if is_admin else 0, json.dumps(perms), phone, 1 if is_google else 0)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao criar usuário: {e}")
            return False
            
    def delete_user(self, user_id):
        if user_id == 1: return False
        try:
            self.conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            self.conn.commit()
            return True
        except: return False
        
    def get_all_users(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, username, is_admin, permissions FROM users ORDER BY username")
        return cursor.fetchall()

    # --- Visitantes ---
    def add_visitor(self, name, phone, email, address, obs):
        try:
            date_now = datetime.now().strftime("%d/%m/%Y %H:%M")
            self.conn.execute(
                "INSERT INTO visitors (name, phone, email, address, date_visit, observations) VALUES (?, ?, ?, ?, ?, ?)",
                (name, phone, email, address, date_now, obs)
            )
            self.conn.commit()
            return True
        except: return False

    def get_all_visitors(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM visitors ORDER BY date_visit DESC")
        return cursor.fetchall()

    def update_visitor(self, visitor_id, name, phone, email, address, obs):
        try:
            self.conn.execute(
                """UPDATE visitors SET name = ?, phone = ?, email = ?, address = ?, observations = ? 
                   WHERE id = ?""",
                (name, phone, email, address, obs, visitor_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao atualizar visitante: {e}")
            return False

    def get_visitor_by_id(self, visitor_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM visitors WHERE id = ?", (visitor_id,))
        return cursor.fetchone()

    # --- Voluntários ---
    def add_collaborator(self, name, phone, email, address, role, dept, hire_date, obs):
        try:
            date_now = datetime.now().strftime("%d/%m/%Y %H:%M")
            self.conn.execute(
                """INSERT INTO volunteers (name, phone, email, address, role, department, 
                   hire_date, registration_date, observations, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, phone, email, address, role, dept, hire_date, date_now, obs, 1)
            )
            self.conn.commit()
            return True
        except: return False

    def get_all_volunteers(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM volunteers WHERE active = 1 ORDER BY name")
        return cursor.fetchall()

    def deactivate_collaborator(self, id):
        try:
            self.conn.execute("UPDATE volunteers SET active = 0 WHERE id = ?", (id,))
            self.conn.commit()
            return True
        except: return False

    # --- Casa de Cornélio ---
    def add_cell(self, name, leader, host, address, day, time, obs):
        try:
            self.conn.execute(
                """INSERT INTO cells (name, leader_name, host_name, address, meeting_day, 
                   meeting_time, observations, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, leader, host, address, day, time, obs, 1)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(e)
            return False

    def get_all_cells(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM cells WHERE active = 1 ORDER BY name")
        return cursor.fetchall()

    def deactivate_cell(self, id):
        try:
            self.conn.execute("UPDATE cells SET active = 0 WHERE id = ?", (id,))
            self.conn.commit()
            return True
        except: return False


# ==============================================================================
# COMPONENTES UI REUTILIZÁVEIS
# ==============================================================================

def get_logo(size=80):
    return ft.Container(
        content=ft.Image(
            src="logoieq.png", 
            fit="cover",
            width=size,
            height=size,
            error_content=ft.Icon(ft.Icons.CHURCH, size=size*0.6, color="white")
        ),
        width=size, height=size,
        border_radius=size//2,
        bgcolor=THEME_COLOR,
        shadow=ft.BoxShadow(blur_radius=10, color="black26"),
        clip_behavior=ft.ClipBehavior.HARD_EDGE
    )

def address_form_fields(page):
    cep = ft.TextField(label="CEP", width=150, keyboard_type=ft.KeyboardType.NUMBER, max_length=9)
    logradouro = ft.TextField(label="Logradouro", expand=True)
    numero = ft.TextField(label="Nº", width=100)
    bairro = ft.TextField(label="Bairro", expand=True)
    cidade = ft.TextField(label="Cidade", expand=True)
    uf = ft.TextField(label="UF", width=80)
    status = ft.Text("", size=12)

    def on_cep_change(e):
        if len(ViaCEPService.clean_cep(cep.value)) < 8: return
        status.value = "Buscando..."
        status.color = "blue"
        page.update()
        
        data = ViaCEPService.search_by_cep(cep.value)
        if data:
            logradouro.value = data.get('logradouro', '')
            bairro.value = data.get('bairro', '')
            cidade.value = data.get('localidade', '')
            uf.value = data.get('uf', '')
            cep.value = ViaCEPService.format_cep(cep.value)
            status.value = "✓ Endereço encontrado!"
            status.color = "green"
            show_success(page, "Endereço carregado com sucesso!")
        else:
            status.value = "✗ CEP não encontrado."
            status.color = "red"
            show_warning(page, "CEP não encontrado. Verifique o número.")
        page.update()

    cep.on_change = on_cep_change
    
    fields_ui = ft.Column([
        ft.Row([cep, status]),
        ft.Row([logradouro, numero]),
        ft.Row([bairro, cidade, uf])
    ])
    
    return {
        "ui": fields_ui,
        "get_full_address": lambda: f"{logradouro.value}, {numero.value} - {bairro.value}, {cidade.value}/{uf.value} CEP: {cep.value}",
        "cep": cep, "logradouro": logradouro, "numero": numero,
        "bairro": bairro, "cidade": cidade, "uf": uf, "status": status
    }

# ==============================================================================
# VIEWS (TELAS)
# ==============================================================================

def login_view(page: ft.Page, db: Database, on_success):
    # --- Componentes voluntários ---
    admin_user = ft.TextField(label="Usuário", prefix_icon=ft.Icons.PERSON)
    admin_pass = ft.TextField(label="Senha", password=True, can_reveal_password=True, prefix_icon=ft.Icons.LOCK)
    
    # --- Componentes Membro ---
    member_user = ft.TextField(label="Nome de Usuário", prefix_icon=ft.Icons.PERSON)
    member_pass = ft.TextField(label="Senha", password=True, can_reveal_password=True, prefix_icon=ft.Icons.LOCK)
    
    # --- Componentes Cadastro Membro ---
    reg_name = ft.TextField(label="Nome de Usuário", prefix_icon=ft.Icons.PERSON)
    reg_phone = ft.TextField(label="Telefone", prefix_icon=ft.Icons.PHONE, keyboard_type="phone")
    reg_pass = ft.TextField(label="Senha (Min 8 dígitos)", password=True, can_reveal_password=True, prefix_icon=ft.Icons.LOCK)
    
    member_mode = ft.Ref[ft.Column]()

    def attempt_admin_login(e):
        # Validação
        if not admin_user.value or not admin_pass.value:
            show_warning(page, "Preencha todos os campos!")
            return
            
        loading = show_loading(page, "Verificando credenciais...")
        
        time.sleep(0.5)  # Simula processamento
        
        if db.check_login(admin_user.value, admin_pass.value):
            hide_loading(page, loading)
            show_success(page, f"Bem-vindo(a), {admin_user.value}!")
            time.sleep(0.3)
            on_success(admin_user.value)
        else:
            hide_loading(page, loading)
            show_error(page, "Usuário ou senha incorretos!")

    def attempt_member_login(e):
        # Validação
        if not member_user.value or not member_pass.value:
            show_warning(page, "Preencha todos os campos!")
            return
        
        loading = show_loading(page, "Verificando credenciais...")
        
        time.sleep(0.5)
        
        if db.check_login(member_user.value, member_pass.value):
            hide_loading(page, loading)
            show_success(page, f"Bem-vindo(a), {member_user.value}!")
            time.sleep(0.3)
            on_success(member_user.value)
        else:
            hide_loading(page, loading)
            show_error(page, "Usuário ou senha incorretos!")

    def google_login_simulation(e):
        loading = show_loading(page, "Conectando ao Google...")
        
        time.sleep(1.5)
        
        google_user = "Membro Google"
        if not db.check_user_exists(google_user):
            perms = {"celulas": True, "voluntários": True, "readonly": True}
            db.add_user(google_user, None, False, perms, is_google=True)
        
        hide_loading(page, loading)
        show_success(page, "Login com Google realizado com sucesso!")
        time.sleep(0.3)
        on_success(google_user)

    def register_member(e):
        if not reg_name.value or not reg_pass.value:
            show_warning(page, "Preencha nome de usuário e senha!")
            return
            
        if len(reg_pass.value) < 8:
            show_warning(page, "A senha deve ter no mínimo 8 caracteres!")
            reg_pass.error_text = "Senha deve ter no mínimo 8 dígitos"
            page.update()
            return
            
        if db.check_user_exists(reg_name.value):
            show_error(page, "Este nome de usuário já está em uso!")
            reg_name.error_text = "Usuário já existe"
            page.update()
            return

        loading = show_loading(page, "Criando conta...")
        
        perms = {"celulas": True, "voluntários": True, "readonly": True}
        
        if db.add_user(reg_name.value, reg_pass.value, False, perms, phone=reg_phone.value):
            hide_loading(page, loading)
            show_success(page, f"Conta criada com sucesso! Bem-vindo(a), {reg_name.value}!")
            time.sleep(0.5)
            toggle_member_mode("login")
        else:
            hide_loading(page, loading)
            show_error(page, "Erro ao criar conta. Tente novamente.")

    def toggle_member_mode(mode):
        if mode == "register":
            member_content.controls = [
                ft.Text("Criar Conta de Membro", size=20, weight="bold", color=THEME_COLOR),
                reg_name, reg_phone, reg_pass,
                ft.Button("Cadastrar", on_click=register_member, width=300, height=45, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white")),
                ft.TextButton("Já tenho conta? Entrar", on_click=lambda e: toggle_member_mode("login"))
            ]
        else:
            member_content.controls = [
                ft.Text("Área de Membros", size=20, weight="bold", color=THEME_COLOR),
                member_user, member_pass,
                ft.Button("Entrar", on_click=attempt_member_login, width=300, height=45, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white")),
                ft.Divider(),
                ft.Button(
                    "Entrar com Google", 
                    icon=ft.Icons.G_MOBILEDATA, 
                    style=ft.ButtonStyle(color="black", bgcolor="white"),
                    width=300, 
                    on_click=google_login_simulation
                ),
                ft.TextButton("Não tem conta? Criar conta", on_click=lambda e: toggle_member_mode("register"))
            ]
        page.update()

    # Layout Membro Inicial
    member_content = ft.Column(
        spacing=15, 
        horizontal_alignment="center",
        controls=[
            ft.Text("Área de Membros", size=20, weight="bold", color=THEME_COLOR),
            member_user, member_pass,
            ft.Button("Entrar", on_click=attempt_member_login, width=300, height=45, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white")),
            ft.Divider(),
            ft.Button(
                "Entrar com Google", 
                icon=ft.Icons.G_MOBILEDATA, 
                style=ft.ButtonStyle(color="black", bgcolor="white"),
                width=300, 
                on_click=google_login_simulation
            ),
            ft.TextButton("Não tem conta? Criar conta", on_click=lambda e: toggle_member_mode("register"))
        ]
    )

    # Layout voluntários
    admin_content = ft.Column([
        ft.Text("Acesso Restrito", size=20, weight="bold", color=THEME_COLOR),
        admin_user, admin_pass,
        ft.Button("Entrar", on_click=attempt_admin_login, width=300, height=45, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"))
    ], horizontal_alignment="center", spacing=15)

    # Toggle Manual
    current_content = ft.Container(content=member_content, padding=20)
    
    def switch_tab(e):
        is_member = e.control.data == "member"
        current_content.content = member_content if is_member else admin_content
        btn_member.style = ft.ButtonStyle(bgcolor=THEME_COLOR if is_member else "white", color="white" if is_member else THEME_COLOR)
        btn_admin.style = ft.ButtonStyle(bgcolor=THEME_COLOR if not is_member else "white", color="white" if not is_member else THEME_COLOR)
        page.update()

    btn_member = ft.Button("Sou Membro", on_click=switch_tab, data="member", 
                           style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"), expand=True)
    btn_admin = ft.Button("Sou Voluntário", on_click=switch_tab, data="admin", 
                          style=ft.ButtonStyle(bgcolor="white", color=THEME_COLOR), expand=True)

    return ft.Container(
        content=ft.Column([
            get_logo(120),
            ft.Text(APP_TITLE, size=18, weight="bold", color="grey"),
            ft.Divider(height=10, color="transparent"),
            ft.Container(
                content=ft.Column([
                    ft.Row([btn_member, btn_admin], spacing=0),
                    current_content
                ]),
                width=400,
                border=ft.Border(
                    top=ft.BorderSide(1, "grey"),
                    right=ft.BorderSide(1, "grey"),
                    bottom=ft.BorderSide(1, "grey"),
                    left=ft.BorderSide(1, "grey")
                ),
                border_radius=10,
                clip_behavior=ft.ClipBehavior.HARD_EDGE
            )
        ], horizontal_alignment="center", alignment="center"),
        expand=True, 
        padding=20
    )

def visitors_view(page: ft.Page, db: Database, readonly: bool = False):
    if readonly:
        return ft.Center(ft.Text("Área restrita a voluntários."))

    name = ft.TextField(label="Nome *", prefix_icon=ft.Icons.PERSON)
    phone = ft.TextField(label="WhatsApp", prefix_icon=ft.Icons.PHONE, keyboard_type="phone")
    email = ft.TextField(label="E-mail", prefix_icon=ft.Icons.EMAIL)
    obs = ft.TextField(label="Observações", multiline=True, min_lines=2)
    addr_component = address_form_fields(page)

    def save(e):
        # Validação
        if not name.value:
            name.error_text = "Campo obrigatório"
            show_warning(page, "Por favor, preencha o nome do visitante!")
            page.update()
            return
        
        loading = show_loading(page, "Salvando visitante...")
        
        time.sleep(0.3)
        
        if db.add_visitor(name.value, phone.value, email.value, addr_component["get_full_address"](), obs.value):
            hide_loading(page, loading)
            show_success(page, f"Visitante '{name.value}' cadastrado com sucesso!")
            
            # Limpa os campos
            name.value = phone.value = email.value = obs.value = ""
            name.error_text = None
            for field in [addr_component["cep"], addr_component["logradouro"], addr_component["numero"], 
                          addr_component["bairro"], addr_component["cidade"], addr_component["uf"]]:
                field.value = ""
            addr_component["status"].value = ""
        else:
            hide_loading(page, loading)
            show_error(page, "Erro ao salvar visitante. Tente novamente.")
        
        page.update()

    return ft.ListView([
        ft.Text("Novo Visitante", size=20, weight="bold"),
        ft.Divider(),
        name,
        ft.Row([phone, email]),
        ft.Divider(),
        ft.Text("Endereço", weight="bold"),
        addr_component["ui"],
        ft.Divider(),
        obs,
        ft.Button("Salvar Visitante", icon=ft.Icons.SAVE, on_click=save, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"))
    ], expand=True, spacing=15, padding=20)

def visitor_edit_view(page: ft.Page, db: Database, visitor_id: int, on_back_callback):
    """View de edição de visitante"""
    # Busca os dados do visitante
    visitor_data = db.get_visitor_by_id(visitor_id)
    if not visitor_data:
        show_error(page, "Visitante não encontrado!")
        on_back_callback()
        return ft.Container()
    
    v_id, v_name, v_phone, v_email, v_address, v_date, v_obs = visitor_data
    
    # Parse do endereço
    def parse_address(address_str):
        if not address_str:
            return {"cep": "", "logradouro": "", "numero": "", "bairro": "", "cidade": "", "uf": ""}
        try:
            parts = address_str.split(" CEP: ")
            cep = parts[1] if len(parts) > 1 else ""
            main_parts = parts[0].split(" - ")
            bairro_cidade = main_parts[1].split(", ") if len(main_parts) > 1 else ["", ""]
            logradouro_numero = main_parts[0].split(", ") if len(main_parts) > 0 else ["", ""]
            logradouro = logradouro_numero[0] if len(logradouro_numero) > 0 else ""
            numero = logradouro_numero[1] if len(logradouro_numero) > 1 else ""
            bairro = bairro_cidade[0] if len(bairro_cidade) > 0 else ""
            cidade_uf = bairro_cidade[1].split("/") if len(bairro_cidade) > 1 else ["", ""]
            cidade = cidade_uf[0] if len(cidade_uf) > 0 else ""
            uf = cidade_uf[1] if len(cidade_uf) > 1 else ""
            return {"cep": cep, "logradouro": logradouro, "numero": numero, "bairro": bairro, "cidade": cidade, "uf": uf}
        except:
            return {"cep": "", "logradouro": "", "numero": "", "bairro": "", "cidade": "", "uf": ""}
    
    addr_parts = parse_address(v_address)
    
    # Campos do formulário
    name = ft.TextField(label="Nome *", value=v_name, prefix_icon=ft.Icons.PERSON)
    phone = ft.TextField(label="WhatsApp", value=v_phone or "", prefix_icon=ft.Icons.PHONE, keyboard_type="phone")
    email = ft.TextField(label="E-mail", value=v_email or "", prefix_icon=ft.Icons.EMAIL)
    obs = ft.TextField(label="Observações", value=v_obs or "", multiline=True, min_lines=2)
    
    # Campos de endereço
    cep = ft.TextField(label="CEP", value=addr_parts["cep"], width=150, keyboard_type=ft.KeyboardType.NUMBER, max_length=9)
    logradouro = ft.TextField(label="Logradouro", value=addr_parts["logradouro"], expand=True)
    numero = ft.TextField(label="Nº", value=addr_parts["numero"], width=100)
    bairro = ft.TextField(label="Bairro", value=addr_parts["bairro"], expand=True)
    cidade = ft.TextField(label="Cidade", value=addr_parts["cidade"], expand=True)
    uf = ft.TextField(label="UF", value=addr_parts["uf"], width=80)
    status = ft.Text("", size=12)

    def on_cep_change(e):
        if len(ViaCEPService.clean_cep(cep.value)) < 8:
            return
        status.value = "Buscando..."
        status.color = "blue"
        page.update()
        
        data = ViaCEPService.search_by_cep(cep.value)
        if data:
            logradouro.value = data.get('logradouro', '')
            bairro.value = data.get('bairro', '')
            cidade.value = data.get('localidade', '')
            uf.value = data.get('uf', '')
            cep.value = ViaCEPService.format_cep(cep.value)
            status.value = "✓ Endereço encontrado!"
            status.color = "green"
            show_success(page, "Endereço carregado com sucesso!")
        else:
            status.value = "✗ CEP não encontrado."
            status.color = "red"
            show_warning(page, "CEP não encontrado. Verifique o número.")
        page.update()

    cep.on_change = on_cep_change
    
    def save_changes(e):
        if not name.value:
            name.error_text = "Campo obrigatório"
            show_warning(page, "Por favor, preencha o nome do visitante!")
            page.update()
            return
        
        loading = show_loading(page, "Salvando alterações...")
        time.sleep(0.3)
        
        full_address = f"{logradouro.value}, {numero.value} - {bairro.value}, {cidade.value}/{uf.value} CEP: {cep.value}"
        
        if db.update_visitor(visitor_id, name.value, phone.value, email.value, full_address, obs.value):
            hide_loading(page, loading)
            show_success(page, f"Visitante '{name.value}' atualizado com sucesso!")
            time.sleep(0.5)
            on_back_callback()
        else:
            hide_loading(page, loading)
            show_error(page, "Erro ao atualizar visitante.")
    
    def cancel_edit(e):
        on_back_callback()

    return ft.ListView([
        ft.Row([
            ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=cancel_edit, tooltip="Voltar"),
            ft.Text("Editar Visitante", size=20, weight="bold")
        ]),
        ft.Divider(),
        name,
        ft.Row([phone, email]),
        ft.Divider(),
        ft.Text("Endereço", weight="bold"),
        ft.Row([cep, status]),
        ft.Row([logradouro, numero]),
        ft.Row([bairro, cidade, uf]),
        ft.Divider(),
        obs,
        ft.Row([
            ft.OutlinedButton("Cancelar", on_click=cancel_edit, icon=ft.Icons.CANCEL),
            ft.ElevatedButton("Salvar Alterações", on_click=save_changes, icon=ft.Icons.SAVE,
                            style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"))
        ], spacing=10)
    ], expand=True, spacing=15, padding=20)

def visitors_list_view(page: ft.Page, db: Database, readonly: bool = False, on_edit_visitor=None):
    """Lista de Visitantes com botão de WhatsApp e Edição"""
    if readonly:
        return ft.Center(ft.Text("Área restrita."))

    list_column = ft.Column([], scroll="auto", expand=True)
    
    def refresh_list(e=None):
        """Atualiza a lista de visitantes"""
        items = db.get_all_visitors()
        list_controls = []
        
        if not items:
            list_controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.PERSON_REMOVE, size=64, color="grey"),
                        ft.Text("Nenhum visitante cadastrado.", size=16, color="grey")
                    ], horizontal_alignment="center", spacing=10),
                    padding=40
                )
            )
        else:
            show_info(page, f"{len(items)} visitante(s) encontrado(s)")
            
        for v in items:
            v_id = v[0]
            v_name = v[1]
            v_phone = v[2]
            v_email = v[3]
            v_date = v[5]
            
            # Botões de ação
            action_buttons = []
            
            # Botão WhatsApp
            if v_phone:
                whatsapp_url = open_whatsapp(v_phone, v_name)
                action_buttons.append(
                    ft.IconButton(
                        icon=ft.Icons.MESSAGE,
                        icon_color="green",
                        tooltip=f"WhatsApp: {v_phone}",
                        url=whatsapp_url
                    )
                )
            else:
                action_buttons.append(
                    ft.Icon(ft.Icons.PHONE_DISABLED, color="grey", tooltip="Sem telefone")
                )
            
            # Botão Editar - agora com função de callback
            if on_edit_visitor:
                action_buttons.append(
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        icon_color=THEME_COLOR,
                        tooltip="Editar visitante",
                        data=v_id,
                        on_click=lambda e: on_edit_visitor(e.control.data)
                    )
                )

            list_controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.PERSON, color=THEME_COLOR, size=40),
                            ft.Column([
                                ft.Text(v_name, weight="bold", size=16),
                                ft.Text(f"Visita: {v_date}", size=12, color="grey"),
                                ft.Text(v_phone if v_phone else "Sem telefone", size=12, color="grey"),
                            ], spacing=2, expand=True),
                            ft.Row(action_buttons, spacing=5)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=15
                    )
                )
            )
        
        list_column.controls = list_controls
        page.update()
    
    # Inicializa a lista
    refresh_list()

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Lista de Visitantes", size=20, weight="bold"),
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    tooltip="Atualizar lista",
                    on_click=refresh_list
                )
            ], alignment="spaceBetween"),
            ft.Divider(),
            list_column
        ], expand=True, spacing=10),
        padding=20,
        expand=True
    )

def volunteers_view(page: ft.Page, db: Database, readonly: bool = False):
    current_view = ft.Ref[ft.Column]()
    
    name = ft.TextField(label="Nome Completo *")
    role = ft.TextField(label="Cargo/Função *")
    dept = ft.Dropdown(label="Departamento", options=[
        ft.dropdown.Option("Pastoral"), ft.dropdown.Option("Administração"), 
        ft.dropdown.Option("Louvor"), ft.dropdown.Option("Infantil"), 
        ft.dropdown.Option("Mídia"), ft.dropdown.Option("Zeladoria")
    ])
    phone = ft.TextField(label="Telefone")
    email = ft.TextField(label="Email")
    hire_date = ft.TextField(label="Data Início", value=datetime.now().strftime("%d/%m/%Y"), width=150)
    addr_component = address_form_fields(page)
    obs = ft.TextField(label="Obs", multiline=True)

    def show_list(e=None):
        items = db.get_all_volunteers()
        list_controls = []
        
        if not items:
            list_controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.GROUP_REMOVE, size=64, color="grey"),
                        ft.Text("Nenhum voluntário cadastrado.", size=16, color="grey")
                    ], horizontal_alignment="center", spacing=10),
                    padding=40
                )
            )
        
        for i in items:
            c_id, c_name, c_phone, _, _, c_role, c_dept = i[0], i[1], i[2], i[3], i[4], i[5], i[6]
            
            trailing = None
            if not readonly:
                trailing = ft.IconButton(ft.Icons.DELETE, icon_color="red", 
                                        tooltip="Desativar voluntário",
                                        on_click=lambda e, x=c_id, n=c_name: delete_collab(x, n))
            
            list_controls.append(
                ft.Card(ft.ListTile(
                    leading=ft.Icon(ft.Icons.BADGE, color=THEME_COLOR),
                    title=ft.Text(c_name, weight="bold"),
                    subtitle=ft.Text(f"{c_role} - {c_dept}\n{c_phone}"),
                    trailing=trailing
                ))
            )
        
        header_controls = [ft.Text("Equipe e Voluntários", size=20, weight="bold")]
        if not readonly:
            header_controls.append(ft.IconButton(ft.Icons.ADD, on_click=show_form, bgcolor=THEME_COLOR, icon_color="white", tooltip="Adicionar voluntário"))

        content = ft.Column([
            ft.Row(header_controls, alignment="spaceBetween"),
            ft.Divider(),
            ft.Column(list_controls, scroll="auto", expand=True)
        ], expand=True)
        
        current_view.current.controls = [content]
        page.update()

    def delete_collab(id, name):
        if readonly: return
        loading = show_loading(page, "Desativando voluntário...")
        time.sleep(0.3)
        if db.deactivate_collaborator(id):
            hide_loading(page, loading)
            show_success(page, f"Voluntário '{name}' desativado com sucesso!")
            show_list()
        else:
            hide_loading(page, loading)
            show_error(page, "Erro ao desativar voluntário.")

    def save(e):
        if readonly: return
        
        # Validação
        if not name.value or not role.value:
            show_warning(page, "Preencha pelo menos Nome e Cargo!")
            return
        
        loading = show_loading(page, "Salvando voluntário...")
        
        time.sleep(0.3)
        
        if db.add_collaborator(name.value, phone.value, email.value, addr_component["get_full_address"](), 
                            role.value, dept.value, hire_date.value, obs.value):
            hide_loading(page, loading)
            show_success(page, f"Voluntário '{name.value}' cadastrado com sucesso!")
            show_list()
        else:
            hide_loading(page, loading)
            show_error(page, "Erro ao salvar voluntário.")
            page.update()

    def show_form(e=None):
        content = ft.Column([
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=show_list, tooltip="Voltar"), 
                   ft.Text("Novo Voluntário", size=20, weight="bold")]),
            name,
            ft.Row([role, dept]),
            ft.Row([phone, email, hire_date]),
            ft.Divider(),
            addr_component["ui"],
            obs,
            ft.Button("Salvar", on_click=save, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"))
        ], scroll="auto", expand=True)
        current_view.current.controls = [content]
        page.update()

    col = ft.Column(expand=True, ref=current_view)
    show_list()
    return col

def cells_view(page: ft.Page, db: Database, readonly: bool = False):
    current_view = ft.Ref[ft.Column]()
    
    name = ft.TextField(label="Nome da Célula *")
    leader = ft.TextField(label="Líder *", prefix_icon=ft.Icons.PERSON)
    host = ft.TextField(label="Anfitrião", prefix_icon=ft.Icons.HOME)
    day = ft.Dropdown(label="Dia", options=[
        ft.dropdown.Option("Segunda"), ft.dropdown.Option("Terça"), ft.dropdown.Option("Quarta"),
        ft.dropdown.Option("Quinta"), ft.dropdown.Option("Sexta"), ft.dropdown.Option("Sábado"), ft.dropdown.Option("Domingo")
    ], width=150)
    time_field = ft.TextField(label="Horário", value="20:00", width=100)
    addr_component = address_form_fields(page)
    obs = ft.TextField(label="Observações")

    def show_list(e=None):
        items = db.get_all_cells()
        list_controls = []
        
        if not items:
            list_controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.GROUP_OFF, size=64, color="grey"),
                        ft.Text("Nenhuma célula cadastrada.", size=16, color="grey")
                    ], horizontal_alignment="center", spacing=10),
                    padding=40
                )
            )
            
        for c in items:
            c_id = c[0]
            c_name = c[1]
            c_leader = c[2]
            c_host = c[3]
            c_address = c[4] if c[4] else "Endereço não informado"
            c_day = c[5]
            c_time = c[6]
            
            trailing = None
            if not readonly:
                trailing = ft.PopupMenuButton(
                    items=[
                        ft.PopupMenuItem(
                            content=ft.Row([ft.Icon(ft.Icons.DELETE, color="red"), ft.Text("Desativar")]), 
                            on_click=lambda e, x=c_id, n=c_name: deactivate(x, n)
                        )
                    ]
                )
            
            card_content = ft.Container(
                content=ft.Column([
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.GROUPS, color=THEME_COLOR, size=30),
                        title=ft.Text(c_name, weight="bold"),
                        subtitle=ft.Text(f"Líder: {c_leader}\n{c_day} às {c_time}"),
                        trailing=trailing
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.HOME_FILLED, size=16, color="grey"),
                                ft.Text(f"Anfitrião: {c_host}" if c_host else "Anfitrião não informado", size=12, color="grey")
                            ]),
                            ft.Row([
                                ft.Icon(ft.Icons.LOCATION_ON, size=16, color="red"),
                                ft.Text(c_address, size=12, color="grey", expand=True)
                            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
                        ], spacing=5), 
                        padding=ft.padding.only(left=20, bottom=10, right=10, top=0)
                    )
                ]),
                padding=ft.padding.only(top=5, bottom=5)
            )

            list_controls.append(ft.Card(content=card_content))

        header_controls = [ft.Text("Casa de Cornélio", size=20, weight="bold")]
        if not readonly:
            header_controls.append(ft.IconButton(ft.Icons.ADD, on_click=show_form, bgcolor=THEME_COLOR, icon_color="white", tooltip="Adicionar célula"))

        content = ft.Column([
            ft.Row(header_controls, alignment="spaceBetween"),
            ft.Divider(),
            ft.Column(list_controls, scroll="auto", expand=True)
        ], expand=True)
        current_view.current.controls = [content]
        page.update()

    def deactivate(id, name):
        if readonly: return
        loading = show_loading(page, "Desativando célula...")
        time.sleep(0.3)
        if db.deactivate_cell(id):
            hide_loading(page, loading)
            show_success(page, f"Célula '{name}' desativada com sucesso!")
            show_list()
        else:
            hide_loading(page, loading)
            show_error(page, "Erro ao desativar célula.")

    def save(e):
        if readonly: return
        
        # Validação
        if not name.value or not leader.value:
            show_warning(page, "Preencha pelo menos Nome da Célula e Líder!")
            return
        
        loading = show_loading(page, "Salvando célula...")
        
        time.sleep(0.3)
        
        if db.add_cell(name.value, leader.value, host.value, addr_component["get_full_address"](), 
                    day.value, time_field.value, obs.value):
            hide_loading(page, loading)
            show_success(page, f"Célula '{name.value}' cadastrada com sucesso!")
            show_list()
        else:
            hide_loading(page, loading)
            show_error(page, "Erro ao salvar célula.")
            page.update()

    def show_form(e=None):
        content = ft.Column([
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=show_list, tooltip="Voltar"), 
                   ft.Text("Nova Célula", size=20, weight="bold")]),
            name,
            ft.Row([leader, host]),
            ft.Row([day, time_field]),
            ft.Divider(),
            ft.Text("Local de Reunião"),
            addr_component["ui"],
            obs,
            ft.Button("Salvar Célula", on_click=save, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"))
        ], scroll="auto", expand=True)
        current_view.current.controls = [content]
        page.update()

    col = ft.Column(expand=True, ref=current_view)
    show_list()
    return col

def users_view(page: ft.Page, db: Database, readonly: bool = False):
    if readonly: return ft.Center(ft.Text("Acesso Negado"))

    current_view = ft.Ref[ft.Column]()
    
    u_name = ft.TextField(label="Username")
    u_pass = ft.TextField(label="Senha", password=True)
    u_admin = ft.Checkbox(label="Administrador", value=False)
    
    p_visit = ft.Checkbox(label="Visitantes", value=True)
    p_cell = ft.Checkbox(label="Casa de Cornélio")
    p_collab = ft.Checkbox(label="Voluntários")

    def show_list(e=None):
        users = db.get_all_users()
        controls = []
        for u in users:
            uid, uname, is_admin = u[0], u[1], u[2]
            controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS if is_admin else ft.Icons.PERSON),
                    title=ft.Text(uname),
                    subtitle=ft.Text("Administrador" if is_admin else "Usuário"),
                    trailing=ft.IconButton(ft.Icons.DELETE, disabled=(uid==1), 
                                         tooltip="Excluir usuário" if uid != 1 else "Não é possível excluir admin",
                                         on_click=lambda e, x=uid, n=uname: delete(x, n))
                )
            )
        
        content = ft.Column([
            ft.Row([ft.Text("Usuários do Sistema", size=20, weight="bold"), 
                   ft.IconButton(ft.Icons.ADD, on_click=show_form, bgcolor=THEME_COLOR, icon_color="white", tooltip="Adicionar usuário")], 
                   alignment="spaceBetween"),
            ft.Divider(),
            ft.Column(controls, scroll="auto", expand=True)
        ], expand=True)
        current_view.current.controls = [content]
        page.update()

    def delete(id, username):
        loading = show_loading(page, "Excluindo usuário...")
        time.sleep(0.3)
        if db.delete_user(id):
            hide_loading(page, loading)
            show_success(page, f"Usuário '{username}' excluído com sucesso!")
            show_list()
        else:
            hide_loading(page, loading)
            show_error(page, "Não é possível excluir este usuário.")

    def save(e):
        # Validação
        if not u_name.value or not u_pass.value:
            show_warning(page, "Preencha usuário e senha!")
            return
        
        loading = show_loading(page, "Criando usuário...")
        
        time.sleep(0.3)
        
        perms = {"visitantes": p_visit.value, "celulas": p_cell.value, "voluntários": p_collab.value}
        
        if db.add_user(u_name.value, u_pass.value, u_admin.value, perms):
            hide_loading(page, loading)
            show_success(page, f"Usuário '{u_name.value}' criado com sucesso!")
            u_name.value = u_pass.value = ""
            show_list()
        else:
            hide_loading(page, loading)
            show_error(page, "Erro ao criar usuário. Nome pode já existir.")
            page.update()

    def show_form(e=None):
        content = ft.Column([
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=show_list, tooltip="Voltar"), 
                   ft.Text("Novo Usuário")]),
            u_name, u_pass, u_admin,
            ft.Text("Permissões (Se não for Admin):"),
            p_visit, p_cell, p_collab,
            ft.Button("Criar Usuário", on_click=save, bgcolor=THEME_COLOR, color="white")
        ])
        current_view.current.controls = [content]
        page.update()

    col = ft.Column(expand=True, ref=current_view)
    show_list()
    return col

# ==============================================================================
# MAIN APP LOGIC
# ==============================================================================

def main(page: ft.Page):
    page.title = APP_TITLE
    page.theme = ft.Theme(color_scheme_seed=THEME_COLOR)
    page.window.width = 1000
    page.window.height = 800
    
    db = Database()
    
    current_user = {"username": None, "permissions": {}, "readonly": False}
    
    def logout(e=None):
        show_info(page, "Até logo! Sessão encerrada.")
        time.sleep(0.5)
        current_user["username"] = None
        current_user["readonly"] = False
        page.clean()
        page.add(login_view(page, db, login_success))
        page.update()

    def login_success(username):
        current_user["username"] = username
        perms = db.get_user_permissions(username)
        current_user["permissions"] = perms
        current_user["readonly"] = perms.get("readonly", False)
        show_dashboard()

    def show_dashboard():
        page.clean()
        
        # Container para a área de conteúdo
        content_area = ft.Container(expand=True, padding=20)
        
        # Variável para controlar a view de edição
        edit_mode = {"active": False, "visitor_id": None}
        
        rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            leading=ft.Container(get_logo(60), padding=10),
            group_alignment=-0.9,
            destinations=[],
            on_change=lambda e: change_page(e.control.selected_index)
        )
        
        pages_map = [] 
        perms = current_user["permissions"]
        is_readonly = current_user["readonly"]
        
        if perms.get("visitantes"):
            rail.destinations.append(ft.NavigationRailDestination(icon=ft.Icons.PEOPLE_ALT, label="Cadastro Visitante"))
            pages_map.append(visitors_view)
            
        if perms.get("lista_visitantes"):
            rail.destinations.append(ft.NavigationRailDestination(icon=ft.Icons.LIST_ALT, label="Lista Visitantes"))
            pages_map.append(visitors_list_view)

        if perms.get("celulas"):
            rail.destinations.append(ft.NavigationRailDestination(icon=ft.Icons.GROUPS, label="Casa de Cornélio"))
            pages_map.append(cells_view)
            
        if perms.get("voluntários"):
            rail.destinations.append(ft.NavigationRailDestination(icon=ft.Icons.BADGE, label="Equipe"))
            pages_map.append(volunteers_view)
            
        if perms.get("usuarios"):
            rail.destinations.append(ft.NavigationRailDestination(icon=ft.Icons.SECURITY, label="Usuários"))
            pages_map.append(users_view)
            
        rail.destinations.append(ft.NavigationRailDestination(icon=ft.Icons.LOGOUT, label="Sair"))
        
        def open_visitor_edit(visitor_id):
            """Abre a página de edição de visitante"""
            edit_mode["active"] = True
            edit_mode["visitor_id"] = visitor_id
            
            def back_to_list():
                edit_mode["active"] = False
                edit_mode["visitor_id"] = None
                # Volta para a lista de visitantes
                rail.selected_index = 1  # Índice da lista de visitantes
                change_page(1)
            
            content_area.content = visitor_edit_view(page, db, visitor_id, back_to_list)
            rail.selected_index = None  # Desseleciona o rail
            page.update()
        
        def change_page(index):
            if index == len(rail.destinations) - 1:
                logout()
                return
            
            # Reseta o modo de edição
            edit_mode["active"] = False
            edit_mode["visitor_id"] = None
            
            view_func = pages_map[index]
            
            # Se for a lista de visitantes, passa o callback de edição
            if view_func == visitors_list_view:
                content_area.content = view_func(page, db, readonly=is_readonly, on_edit_visitor=open_visitor_edit)
            else:
                content_area.content = view_func(page, db, readonly=is_readonly)
            
            page.update()

        if pages_map:
            # Se for a primeira página e for lista de visitantes, passa o callback
            if pages_map[0] == visitors_list_view:
                content_area.content = pages_map[0](page, db, readonly=is_readonly, on_edit_visitor=open_visitor_edit)
            else:
                content_area.content = pages_map[0](page, db, readonly=is_readonly)
        else:
            content_area.content = ft.Text("Sem permissões de acesso.")

        page.add(
            ft.Row(
                [
                    rail,
                    ft.VerticalDivider(width=1),
                    content_area,
                ],
                expand=True,
            )
        )
        page.update()

    page.add(login_view(page, db, login_success))

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    ft.app(target=main, assets_dir="assets")