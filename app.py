"""
IEQ Gestão - Sistema Integrado de Gestão Eclesiástica
VERSÃO RESPONSIVA (Mobile First + Desktop)
"""
import flet as ft
import json
import requests
import time
import threading
import urllib.parse
from datetime import datetime
from typing import Optional, Dict
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from gallery_module import add_gallery_methods_to_database, gallery_view

# Carregar variáveis de ambiente
load_dotenv()

# ==============================================================================
# CONFIGURAÇÕES E UTILITÁRIOS
# ==============================================================================

APP_TITLE = "IEQ - Gestão Integrada"
THEME_COLOR = "#1976D2"

# Configuração do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("AVISO: SUPABASE_URL e SUPABASE_KEY não encontrados no .env")

# ==============================================================================
# FUNÇÕES DE FEEDBACK VISUAL (ALERTAS NO TOPO)
# ==============================================================================

def show_top_message(page, message, color, icon):
    snack_content = ft.Container(
        content=ft.Row([
            ft.Icon(icon, color="white"),
            ft.Text(message, color="white", weight="bold", size=14, expand=True) # Tamanho 14 melhor para mobile
        ], alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=color,
        padding=15,
        border_radius=10,
        shadow=ft.BoxShadow(blur_radius=15, color="black26"),
        left=10, # Margens menores para mobile
        right=10,
        top=-100,
        opacity=0,
        animate_position=ft.animation.Animation(500, ft.AnimationCurve.ELASTIC_OUT),
        animate_opacity=ft.animation.Animation(300, ft.AnimationCurve.EASE_IN),
        on_click=lambda e: close_snack(page, e.control)
    )

    page.overlay.append(snack_content)
    page.update()

    snack_content.top = 10 # Mais próximo do topo no mobile
    snack_content.opacity = 1
    page.update()

    def auto_close():
        time.sleep(4)
        try:
            close_snack(page, snack_content)
        except:
            pass

    threading.Thread(target=auto_close, daemon=True).start()

def close_snack(page, container):
    try:
        container.top = -100
        container.opacity = 0
        page.update()
        time.sleep(0.5)
        if container in page.overlay:
            page.overlay.remove(container)
            page.update()
    except:
        pass

def show_success(page, message): show_top_message(page, message, "green", ft.Icons.CHECK_CIRCLE)
def show_error(page, message): show_top_message(page, message, "red", ft.Icons.ERROR)
def show_warning(page, message): show_top_message(page, message, "orange", ft.Icons.WARNING)
def show_info(page, message): show_top_message(page, message, "blue", ft.Icons.INFO)

def show_loading(page, message="Processando..."):
    loading_container = ft.Container(
        content=ft.Column([
            ft.ProgressRing(),
            ft.Text(message, color="white")
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
        bgcolor="black54",
        expand=True,
        alignment=ft.alignment.center,
        width=page.width,
        height=page.height,
    )
    page.overlay.append(loading_container)
    page.update()
    return loading_container

def hide_loading(page, loading_container):
    if loading_container in page.overlay:
        page.overlay.remove(loading_container)
        page.update()

class ViaCEPService:
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
    if not phone: return ""
    clean_phone = ''.join(filter(str.isdigit, phone))
    if len(clean_phone) <= 11 and not clean_phone.startswith("55"):
        clean_phone = "55" + clean_phone
    message = f"Olá {name}, paz! Sou da IEQ."
    encoded_message = urllib.parse.quote(message)
    return f"https://wa.me/{clean_phone}?text={encoded_message}"

# ==============================================================================
# CAMADA DE DADOS (SUPABASE) - Mantida idêntica
# ==============================================================================

class Database:
    def __init__(self):
        if SUPABASE_URL and SUPABASE_KEY:
            self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            print("✓ Conectado ao Supabase")
            add_gallery_methods_to_database(Database)
        else:
            self.supabase = None
            print("✗ Erro: Credenciais do Supabase ausentes")

    def check_login(self, username, password):
        if not self.supabase: return None
        try:
            response = self.supabase.table('users').select('*').eq('username', username).eq('password', password).execute()
            if response.data and len(response.data) > 0: return response.data[0]
            return None
        except Exception as e: print(f"Erro no login: {e}"); return None
    
    def check_user_exists(self, username):
        if not self.supabase: return False
        try:
            response = self.supabase.table('users').select('*').eq('username', username).execute()
            return response.data and len(response.data) > 0
        except Exception as e: return False

    def get_user_permissions(self, username):
        if not self.supabase: return {}
        try:
            response = self.supabase.table('users').select('permissions, is_admin').eq('username', username).execute()
            if response.data and len(response.data) > 0:
                user = response.data[0]
                if user.get('is_admin', False):
                    return {"visitantes": True, "celulas": True, "usuarios": True, "voluntários": True, "galeria": True, "readonly": False, "lista_visitantes": True}
                perms = user.get('permissions', {})
                if isinstance(perms, str): perms = json.loads(perms)
                if perms.get("visitantes"): perms["lista_visitantes"] = True
                if 'galeria' not in perms: perms['galeria'] = True
                return perms
            return {}
        except Exception as e: return {}

    def add_user(self, username, password, is_admin, perms, phone=None, is_google=False):
        if not self.supabase: return False
        try:
            data = {'username': username, 'password': password, 'is_admin': is_admin, 'permissions': perms if isinstance(perms, dict) else json.loads(perms), 'phone': phone, 'is_google_auth': is_google}
            self.supabase.table('users').insert(data).execute()
            return True
        except Exception as e: return False
            
    def delete_user(self, user_id):
        if not self.supabase or user_id == 1: return False
        try:
            self.supabase.table('users').delete().eq('id', user_id).execute()
            return True
        except Exception as e: return False
        
    def get_all_users(self):
        if not self.supabase: return []
        try:
            response = self.supabase.table('users').select('id, username, is_admin, permissions').order('username').execute()
            return [(u['id'], u['username'], u['is_admin'], json.dumps(u['permissions'])) for u in response.data]
        except Exception as e: return []

    def add_visitor(self, name, phone, email, address, obs):
        if not self.supabase: return False
        try:
            data = {'name': name, 'phone': phone, 'email': email, 'address': address, 'observations': obs}
            self.supabase.table('visitors').insert(data).execute()
            return True
        except Exception as e: return False

    def get_all_visitors(self):
        if not self.supabase: return []
        try:
            response = self.supabase.table('visitors').select('*').order('date_visit', desc=True).execute()
            result = []
            for v in response.data:
                date_visit = v.get('date_visit', '')
                if date_visit:
                    try:
                        dt = datetime.fromisoformat(date_visit.replace('Z', '+00:00'))
                        date_visit = dt.strftime("%d/%m/%Y %H:%M")
                    except: pass
                result.append((v['id'], v['name'], v.get('phone'), v.get('email'), v.get('address'), date_visit, v.get('observations')))
            return result
        except Exception as e: return []

    def update_visitor(self, visitor_id, name, phone, email, address, obs):
        if not self.supabase: return False
        try:
            data = {'name': name, 'phone': phone, 'email': email, 'address': address, 'observations': obs}
            self.supabase.table('visitors').update(data).eq('id', visitor_id).execute()
            return True
        except Exception as e: return False

    def get_visitor_by_id(self, visitor_id):
        if not self.supabase: return None
        try:
            response = self.supabase.table('visitors').select('*').eq('id', visitor_id).execute()
            if response.data:
                v = response.data[0]
                date_visit = v.get('date_visit', '')
                if date_visit:
                    try:
                        dt = datetime.fromisoformat(date_visit.replace('Z', '+00:00'))
                        date_visit = dt.strftime("%d/%m/%Y %H:%M")
                    except: pass
                return (v['id'], v['name'], v.get('phone'), v.get('email'), v.get('address'), date_visit, v.get('observations'))
            return None
        except Exception as e: return None
        
    def delete_visitor(self, visitor_id):
        """Deleta um visitante pelo ID"""
        if not self.supabase: return False
        try:
            self.supabase.table('visitors').delete().eq('id', visitor_id).execute()
            return True
        except Exception as e:
            print(f"Erro ao deletar visitante: {e}")
            return False

    def add_collaborator(self, name, phone, email, address, role, dept, hire_date, obs):
        if not self.supabase: return False
        try:
            data = {'name': name, 'phone': phone, 'email': email, 'address': address, 'role': role, 'department': dept, 'hire_date': hire_date, 'observations': obs, 'active': True}
            self.supabase.table('volunteers').insert(data).execute()
            return True
        except Exception as e: return False

    def get_all_volunteers(self):
        if not self.supabase: return []
        try:
            response = self.supabase.table('volunteers').select('*').eq('active', True).order('name').execute()
            result = []
            for v in response.data:
                result.append((v['id'], v['name'], v.get('phone'), v.get('email'), v.get('address'), v.get('role'), v.get('department'), v.get('hire_date'), v.get('registration_date'), v.get('observations'), v.get('active', True)))
            return result
        except Exception as e: return []

    def deactivate_collaborator(self, id):
        if not self.supabase: return False
        try:
            self.supabase.table('volunteers').update({'active': False}).eq('id', id).execute()
            return True
        except Exception as e: return False

    def add_cell(self, name, leader, host, address, day, time, obs):
        if not self.supabase: return False
        try:
            data = {'name': name, 'leader_name': leader, 'host_name': host, 'address': address, 'meeting_day': day, 'meeting_time': time, 'observations': obs, 'active': True}
            self.supabase.table('cells').insert(data).execute()
            return True
        except Exception as e: return False

    def get_all_cells(self):
        if not self.supabase: return []
        try:
            response = self.supabase.table('cells').select('*').eq('active', True).order('name').execute()
            result = []
            for c in response.data:
                result.append((c['id'], c['name'], c['leader_name'], c.get('host_name'), c.get('address'), c.get('meeting_day'), c.get('meeting_time'), c.get('observations'), c.get('active', True)))
            return result
        except Exception as e: return []

    def deactivate_cell(self, id):
        if not self.supabase: return False
        try:
            self.supabase.table('cells').update({'active': False}).eq('id', id).execute()
            return True
        except Exception as e: return False

# ==============================================================================
# COMPONENTES UI RESPONSIVOS
# ==============================================================================

def get_logo(size=80):
    return ft.Container(
        content=ft.Image(src="logoieq.png", fit="cover", width=size, height=size, error_content=ft.Icon(ft.Icons.CHURCH, size=size*0.6, color="white")),
        width=size, height=size, border_radius=size//2, bgcolor=THEME_COLOR,
        shadow=ft.BoxShadow(blur_radius=10, color="black26"), clip_behavior=ft.ClipBehavior.HARD_EDGE
    )

def address_form_fields(page):
    # ResponsiveRow: sm (celular) = 12 colunas (full), md (tablet/pc) = dividido
    cep = ft.TextField(label="CEP", keyboard_type=ft.KeyboardType.NUMBER, max_length=9, col={"sm": 6, "md": 3})
    status = ft.Text("", size=12, col={"sm": 6, "md": 9}) # Status ao lado do CEP
    logradouro = ft.TextField(label="Logradouro", col={"sm": 12, "md": 8})
    numero = ft.TextField(label="Nº", col={"sm": 12, "md": 4})
    bairro = ft.TextField(label="Bairro", col={"sm": 12, "md": 4})
    cidade = ft.TextField(label="Cidade", col={"sm": 8, "md": 6})
    uf = ft.TextField(label="UF", col={"sm": 4, "md": 2})

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
            status.value = "✓ Encontrado!"
            status.color = "green"
            show_success(page, "Endereço carregado!")
        else:
            status.value = "✗ Não encontrado."
            status.color = "red"
            show_warning(page, "CEP inválido.")
        page.update()

    cep.on_change = on_cep_change
    
    # Layout responsivo
    fields_ui = ft.ResponsiveRow([
        cep, status,
        logradouro, numero,
        bairro, cidade, uf
    ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
    
    return {
        "ui": fields_ui,
        "get_full_address": lambda: f"{logradouro.value}, {numero.value} - {bairro.value}, {cidade.value}/{uf.value} CEP: {cep.value}",
        "cep": cep, "logradouro": logradouro, "numero": numero,
        "bairro": bairro, "cidade": cidade, "uf": uf, "status": status
    }

# ==============================================================================
# VIEWS (TELAS) - ADAPTADAS PARA RESPONSIVIDADE
# ==============================================================================

def login_view(page: ft.Page, db: Database, on_success):
    # Componentes com largura responsiva (col)
    admin_user = ft.TextField(label="Usuário", prefix_icon=ft.Icons.PERSON, col=12)
    admin_pass = ft.TextField(label="Senha", password=True, can_reveal_password=True, prefix_icon=ft.Icons.LOCK, col=12)
    
    member_user = ft.TextField(label="Nome de Usuário", prefix_icon=ft.Icons.PERSON, col=12)
    member_pass = ft.TextField(label="Senha", password=True, can_reveal_password=True, prefix_icon=ft.Icons.LOCK, col=12)
    
    reg_name = ft.TextField(label="Nome de Usuário", prefix_icon=ft.Icons.PERSON, col=12)
    reg_phone = ft.TextField(label="Telefone", prefix_icon=ft.Icons.PHONE, keyboard_type="phone", col=12)
    reg_pass = ft.TextField(label="Senha (Min 8 dígitos)", password=True, can_reveal_password=True, prefix_icon=ft.Icons.LOCK, col=12)
    
    member_mode = ft.Ref[ft.Column]()

    def attempt_admin_login(e):
        if not admin_user.value or not admin_pass.value:
            show_warning(page, "Preencha todos os campos!")
            return
        loading = show_loading(page, "Entrando...")
        time.sleep(0.5)
        if db.check_login(admin_user.value, admin_pass.value):
            hide_loading(page, loading)
            on_success(admin_user.value)
        else:
            hide_loading(page, loading)
            show_error(page, "Credenciais inválidas!")

    def attempt_member_login(e):
        if not member_user.value or not member_pass.value:
            show_warning(page, "Preencha todos os campos!")
            return
        loading = show_loading(page, "Entrando...")
        time.sleep(0.5)
        if db.check_login(member_user.value, member_pass.value):
            hide_loading(page, loading)
            on_success(member_user.value)
        else:
            hide_loading(page, loading)
            show_error(page, "Credenciais inválidas!")

    def register_member(e):
        if not reg_name.value or not reg_pass.value:
            show_warning(page, "Preencha dados obrigatórios!")
            return
        if len(reg_pass.value) < 8:
            show_warning(page, "Senha muito curta!")
            return
        if db.check_user_exists(reg_name.value):
            show_error(page, "Usuário já existe!")
            return
        loading = show_loading(page, "Criando conta...")
        perms = {"celulas": True, "voluntários": True, "readonly": True}
        if db.add_user(reg_name.value, reg_pass.value, False, perms, phone=reg_phone.value):
            hide_loading(page, loading)
            show_success(page, "Conta criada!")
            toggle_member_mode("login")
        else:
            hide_loading(page, loading)
            show_error(page, "Erro ao criar conta.")

    def toggle_member_mode(mode):
        if mode == "register":
            member_content.controls = [
                ft.Text("Criar Conta", size=20, weight="bold", color=THEME_COLOR),
                ft.ResponsiveRow([reg_name, reg_phone, reg_pass]),
                ft.Button("Cadastrar", on_click=register_member, width=300, height=45, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white")),
                ft.TextButton("Já tenho conta? Entrar", on_click=lambda e: toggle_member_mode("login"))
            ]
        else:
            member_content.controls = [
                ft.Text("Membros", size=20, weight="bold", color=THEME_COLOR),
                ft.ResponsiveRow([member_user, member_pass]),
                ft.Button("Entrar", on_click=attempt_member_login, width=300, height=45, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white")),
                ft.Divider(),
                ft.TextButton("Criar nova conta", on_click=lambda e: toggle_member_mode("register"))
            ]
        page.update()

    member_content = ft.Column(
        spacing=15, horizontal_alignment="center",
        controls=[
            ft.Text("Membros", size=20, weight="bold", color=THEME_COLOR),
            ft.ResponsiveRow([member_user, member_pass]),
            ft.Button("Entrar", on_click=attempt_member_login, width=300, height=45, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white")),
            ft.Divider(),
            ft.TextButton("Criar nova conta", on_click=lambda e: toggle_member_mode("register"))
        ]
    )

    admin_content = ft.Column([
        ft.Text("Voluntários", size=20, weight="bold", color=THEME_COLOR),
        ft.ResponsiveRow([admin_user, admin_pass]),
        ft.Button("Entrar", on_click=attempt_admin_login, width=300, height=45, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"))
    ], horizontal_alignment="center", spacing=15)

    current_content = ft.Container(content=member_content, padding=20)
    
    def switch_tab(e):
        is_member = e.control.data == "member"
        current_content.content = member_content if is_member else admin_content
        btn_member.style = ft.ButtonStyle(bgcolor=THEME_COLOR if is_member else "white", color="white" if is_member else THEME_COLOR)
        btn_admin.style = ft.ButtonStyle(bgcolor=THEME_COLOR if not is_member else "white", color="white" if not is_member else THEME_COLOR)
        page.update()

    btn_member = ft.Button("Membro", on_click=switch_tab, data="member", style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"), expand=True)
    btn_admin = ft.Button("Voluntário", on_click=switch_tab, data="admin", style=ft.ButtonStyle(bgcolor="white", color=THEME_COLOR), expand=True)

    # Container principal responsivo
    return ft.Container(
        content=ft.Column([
            get_logo(100),
            ft.Text(APP_TITLE, size=18, weight="bold", color="grey", text_align="center"),
            ft.Divider(height=10, color="transparent"),
            ft.Container(
                content=ft.Column([ft.Row([btn_member, btn_admin], spacing=0), current_content]),
                # Largura máxima 400, mas adaptável se tela for menor
                width=400,
                border_radius=10,
                border=ft.border.all(1, "grey"),
                clip_behavior=ft.ClipBehavior.HARD_EDGE
            )
        ], horizontal_alignment="center", alignment=ft.alignment.center, scroll="auto"),
        padding=10, alignment=ft.alignment.center, expand=True
    )

def visitors_view(page: ft.Page, db: Database, readonly: bool = False, on_back_callback=None):
    if readonly: return ft.Center(ft.Text("Área restrita a voluntários."))

    # Formulário Responsivo
    name = ft.TextField(label="Nome *", prefix_icon=ft.Icons.PERSON, col=12)
    phone = ft.TextField(label="WhatsApp", prefix_icon=ft.Icons.PHONE, keyboard_type="phone", col={"sm": 12, "md": 6})
    email = ft.TextField(label="E-mail", prefix_icon=ft.Icons.EMAIL, col={"sm": 12, "md": 6})
    obs = ft.TextField(label="Observações", multiline=True, min_lines=2, col=12)
    addr_component = address_form_fields(page)

    def save(e):
        if not name.value:
            show_warning(page, "Nome é obrigatório!")
            return
        loading = show_loading(page, "Salvando...")
        time.sleep(0.3)
        if db.add_visitor(name.value, phone.value, email.value, addr_component["get_full_address"](), obs.value):
            hide_loading(page, loading)
            show_success(page, "Visitante cadastrado!")
            # Se tiver callback de voltar (está dentro da lista), volta pra lista
            if on_back_callback:
                on_back_callback()
            else:
                # Limpa campos se for uso isolado
                name.value = phone.value = email.value = obs.value = ""
                for f in [addr_component["cep"], addr_component["logradouro"], addr_component["numero"], addr_component["bairro"], addr_component["cidade"], addr_component["uf"]]: f.value = ""
                addr_component["status"].value = ""
                page.update()
        else:
            hide_loading(page, loading)
            show_error(page, "Erro ao salvar.")
    
    # Cabeçalho com botão de voltar
    header_row = ft.Row([
        ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: on_back_callback()) if on_back_callback else ft.Container(),
        ft.Text("Novo Visitante", size=20, weight="bold")
    ])

    return ft.ListView([
        header_row,
        ft.Divider(),
        ft.ResponsiveRow([name, phone, email]),
        ft.Divider(),
        ft.Text("Endereço", weight="bold"),
        addr_component["ui"],
        ft.Divider(),
        ft.ResponsiveRow([obs]),
        ft.Container(ft.Button("Salvar Visitante", icon=ft.Icons.SAVE, on_click=save, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white")), padding=10)
    ], expand=True, padding=10)

def visitor_edit_view(page: ft.Page, db: Database, visitor_id: int, on_back_callback):
    visitor_data = db.get_visitor_by_id(visitor_id)
    if not visitor_data:
        show_error(page, "Não encontrado!")
        on_back_callback()
        return ft.Container()
    
    v_id, v_name, v_phone, v_email, v_address, v_date, v_obs = visitor_data
    
    def parse_address(address_str):
        if not address_str: return {"cep": "", "logradouro": "", "numero": "", "bairro": "", "cidade": "", "uf": ""}
        try:
            parts = address_str.split(" CEP: ")
            cep = parts[1] if len(parts) > 1 else ""
            main = parts[0].split(" - ")
            bairro_cidade = main[1].split(", ") if len(main) > 1 else ["", ""]
            logra_num = main[0].split(", ") if len(main) > 0 else ["", ""]
            cid_uf = bairro_cidade[1].split("/") if len(bairro_cidade) > 1 else ["", ""]
            return {"cep": cep, "logradouro": logra_num[0], "numero": logra_num[1] if len(logra_num)>1 else "", "bairro": bairro_cidade[0], "cidade": cid_uf[0], "uf": cid_uf[1] if len(cid_uf)>1 else ""}
        except: return {"cep": "", "logradouro": "", "numero": "", "bairro": "", "cidade": "", "uf": ""}
    
    addr = parse_address(v_address)
    
    name = ft.TextField(label="Nome *", value=v_name, prefix_icon=ft.Icons.PERSON, col=12)
    phone = ft.TextField(label="WhatsApp", value=v_phone or "", prefix_icon=ft.Icons.PHONE, col={"sm": 12, "md": 6})
    email = ft.TextField(label="E-mail", value=v_email or "", prefix_icon=ft.Icons.EMAIL, col={"sm": 12, "md": 6})
    obs = ft.TextField(label="Observações", value=v_obs or "", multiline=True, col=12)
    
    # Endereço Editável Responsivo
    cep = ft.TextField(label="CEP", value=addr["cep"], col={"sm": 6, "md": 3})
    status = ft.Text("", size=12, col={"sm": 6, "md": 9})
    logra = ft.TextField(label="Logradouro", value=addr["logradouro"], col={"sm": 12, "md": 8})
    num = ft.TextField(label="Nº", value=addr["numero"], col={"sm": 12, "md": 4})
    bairro = ft.TextField(label="Bairro", value=addr["bairro"], col={"sm": 12, "md": 4})
    cid = ft.TextField(label="Cidade", value=addr["cidade"], col={"sm": 8, "md": 6})
    uf = ft.TextField(label="UF", value=addr["uf"], col={"sm": 4, "md": 2})

    def on_cep_change(e):
        if len(ViaCEPService.clean_cep(cep.value)) < 8: return
        data = ViaCEPService.search_by_cep(cep.value)
        if data:
            logra.value = data.get('logradouro', '')
            bairro.value = data.get('bairro', '')
            cid.value = data.get('localidade', '')
            uf.value = data.get('uf', '')
            cep.value = ViaCEPService.format_cep(cep.value)
            page.update()

    cep.on_change = on_cep_change
    
    def save_changes(e):
        if not name.value:
            show_warning(page, "Nome obrigatório!")
            return
        loading = show_loading(page, "Atualizando...")
        time.sleep(0.3)
        full_addr = f"{logra.value}, {num.value} - {bairro.value}, {cid.value}/{uf.value} CEP: {cep.value}"
        if db.update_visitor(visitor_id, name.value, phone.value, email.value, full_addr, obs.value):
            hide_loading(page, loading)
            show_success(page, "Atualizado!")
            on_back_callback()
        else:
            hide_loading(page, loading)
            show_error(page, "Erro ao atualizar.")
    
    return ft.ListView([
        ft.Row([ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: on_back_callback()), ft.Text("Editar", size=20, weight="bold")]),
        ft.Divider(),
        ft.ResponsiveRow([name, phone, email]),
        ft.Divider(),
        ft.Text("Endereço", weight="bold"),
        ft.ResponsiveRow([cep, status, logra, num, bairro, cid, uf]),
        ft.Divider(),
        ft.ResponsiveRow([obs]),
        ft.Row([ft.ElevatedButton("Salvar", on_click=save_changes, icon=ft.Icons.SAVE, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"))])
    ], expand=True, padding=10)

def visitors_list_view(page: ft.Page, db: Database, readonly: bool = False, on_edit_visitor=None, on_add_visitor=None):
    if readonly: return ft.Center(ft.Text("Área restrita."))
    list_col = ft.Column([], scroll="auto", expand=True)
    
    # --- Lógica de Exclusão ---
    def delete_visitor_click(v_id, v_name):
        def confirm_delete(e):
            page.close(dlg)
            loading = show_loading(page, "Excluindo...")
            time.sleep(0.3)
            
            if db.delete_visitor(v_id):
                hide_loading(page, loading)
                show_success(page, f"Visitante '{v_name}' excluído!")
                refresh_list() # Recarrega a lista
            else:
                hide_loading(page, loading)
                show_error(page, "Erro ao excluir visitante.")

        dlg = ft.AlertDialog(
            title=ft.Text("Confirmar Exclusão"),
            content=ft.Text(f"Tem certeza que deseja apagar o visitante '{v_name}'?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.close(dlg)),
                ft.TextButton("Excluir", on_click=confirm_delete, style=ft.ButtonStyle(color="red"))
            ]
        )
        page.open(dlg)

    # --- Carregamento da Lista ---
    def refresh_list(e=None):
        items = db.get_all_visitors()
        list_controls = []
        if not items:
            list_controls.append(ft.Container(content=ft.Column([ft.Icon(ft.Icons.PERSON_REMOVE, size=50, color="grey"), ft.Text("Nenhum visitante.", color="grey")], horizontal_alignment="center"), padding=20))
        
        for v in items:
            v_id, v_name, v_phone, _, _, v_date, _ = v
            
            # Botões de Ação
            btns = []
            
            # 1. Botão WhatsApp
            if v_phone:
                btns.append(ft.IconButton(icon=ft.Icons.MESSAGE, icon_color="green", tooltip="WhatsApp", url=open_whatsapp(v_phone, v_name)))
            
            # 2. Botão Editar
            if on_edit_visitor:
                btns.append(ft.IconButton(icon=ft.Icons.EDIT, icon_color=THEME_COLOR, tooltip="Editar", data=v_id, on_click=lambda e: on_edit_visitor(e.control.data)))
            
            # 3. Botão Deletar (NOVO)
            if not readonly:
                btns.append(ft.IconButton(
                    icon=ft.Icons.DELETE, 
                    icon_color="red", 
                    tooltip="Excluir", 
                    on_click=lambda e, x=v_id, n=v_name: delete_visitor_click(x, n)
                ))

            # Card do Visitante
            list_controls.append(
                ft.Card(ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.PERSON, color=THEME_COLOR, size=30),
                        ft.Column([
                            ft.Text(v_name, weight="bold"), 
                            ft.Text(f"{v_date}", size=12, color="grey")
                        ], expand=True),
                        ft.Row(btns, spacing=0) # Barra de botões alinhada à direita
                    ]), padding=10
                ))
            )
        list_col.controls = list_controls
        page.update()
    
    refresh_list()
    
    # Cabeçalho
    header_controls = [ft.Text("Visitantes", size=20, weight="bold")]
    if not readonly and on_add_visitor:
        header_controls.append(
            ft.IconButton(ft.Icons.ADD, on_click=lambda e: on_add_visitor(), bgcolor=THEME_COLOR, icon_color="white", tooltip="Novo Visitante")
        )
    elif not readonly:
         header_controls.append(ft.IconButton(ft.Icons.REFRESH, on_click=refresh_list))

    return ft.Container(
        content=ft.Column([
            ft.Row(header_controls, alignment="spaceBetween"), 
            ft.Divider(), 
            list_col
        ], expand=True), 
        padding=10, expand=True
    )
    
def volunteers_view(page: ft.Page, db: Database, readonly: bool = False):
    current_view = ft.Ref[ft.Column]()
    
    name = ft.TextField(label="Nome *", col=12)
    role = ft.TextField(label="Cargo *", col={"sm": 12, "md": 6})
    dept = ft.Dropdown(label="Departamento", options=[ft.dropdown.Option(x) for x in ["Pastor(a)", "Adm", "Louvor", "Infantil", "Mídia", "Diácono"]], col={"sm": 12, "md": 6})
    phone = ft.TextField(label="Tel", col={"sm": 12, "md": 4})
    email = ft.TextField(label="Email", col={"sm": 12, "md": 4})
    hire_date = ft.TextField(label="Data", value=datetime.now().strftime("%d/%m/%Y"), col={"sm": 12, "md": 4})
    addr_component = address_form_fields(page)
    obs = ft.TextField(label="Obs", multiline=True, col=12)

    def show_list(e=None):
        items = db.get_all_volunteers()
        list_controls = []
        for i in items:
            c_id, c_name, _, _, _, c_role, c_dept = i[0], i[1], i[2], i[3], i[4], i[5], i[6]
            trailing = ft.IconButton(ft.Icons.DELETE, icon_color="red", on_click=lambda e, x=c_id: delete_collab(x)) if not readonly else None
            list_controls.append(ft.Card(ft.ListTile(leading=ft.Icon(ft.Icons.BADGE, color=THEME_COLOR), title=ft.Text(c_name, weight="bold"), subtitle=ft.Text(f"{c_role} - {c_dept}"), trailing=trailing)))
        
        header = [ft.Text("Equipe", size=20, weight="bold")]
        if not readonly: header.append(ft.IconButton(ft.Icons.ADD, on_click=show_form, bgcolor=THEME_COLOR, icon_color="white"))
        
        content = ft.Column([ft.Row(header, alignment="spaceBetween"), ft.Divider(), ft.Column(list_controls, scroll="auto", expand=True)], expand=True)
        current_view.current.controls = [content]
        page.update()

    def delete_collab(id):
        if db.deactivate_collaborator(id): show_success(page, "Desativado!"); show_list()
        else: show_error(page, "Erro.")

    def save(e):
        if not name.value or not role.value: show_warning(page, "Preencha Nome e Cargo!"); return
        if db.add_collaborator(name.value, phone.value, email.value, addr_component["get_full_address"](), role.value, dept.value, hire_date.value, obs.value): show_success(page, "Salvo!"); show_list()
        else: show_error(page, "Erro.")

    def show_form(e=None):
        content = ft.Column([
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=show_list), ft.Text("Novo", size=20, weight="bold")]),
            ft.ResponsiveRow([name, role, dept, phone, email, hire_date]),
            ft.Divider(), addr_component["ui"], ft.ResponsiveRow([obs]),
            ft.Button("Salvar", on_click=save, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"))
        ], scroll="auto", expand=True)
        current_view.current.controls = [content]
        page.update()

    col = ft.Column(expand=True, ref=current_view)
    show_list()
    return col

def cells_view(page: ft.Page, db: Database, readonly: bool = False):
    current_view = ft.Ref[ft.Column]()
    name = ft.TextField(label="Nome Célula *", col=12)
    leader = ft.TextField(label="Líder *", prefix_icon=ft.Icons.PERSON, col={"sm": 12, "md": 6})
    host = ft.TextField(label="Anfitrião", prefix_icon=ft.Icons.HOME, col={"sm": 12, "md": 6})
    day = ft.Dropdown(label="Dia", options=[ft.dropdown.Option(x) for x in ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]], col={"sm": 6, "md": 4})
    time_f = ft.TextField(label="Horário", value="20:00", col={"sm": 6, "md": 4})
    addr_component = address_form_fields(page)
    obs = ft.TextField(label="Obs", col=12)

    def show_list(e=None):
        items = db.get_all_cells()
        list_controls = []
        for c in items:
            c_id, c_name, c_lead, c_day, c_time = c[0], c[1], c[2], c[5], c[6]
            trailing = ft.IconButton(ft.Icons.DELETE, icon_color="red", on_click=lambda e, x=c_id: delete(x)) if not readonly else None
            list_controls.append(ft.Card(ft.ListTile(leading=ft.Icon(ft.Icons.GROUPS, color=THEME_COLOR), title=ft.Text(c_name, weight="bold"), subtitle=ft.Text(f"Líder: {c_lead}\n{c_day} às {c_time}"), trailing=trailing)))
        
        header = [ft.Text("Células", size=20, weight="bold")]
        if not readonly: header.append(ft.IconButton(ft.Icons.ADD, on_click=show_form, bgcolor=THEME_COLOR, icon_color="white"))
        content = ft.Column([ft.Row(header, alignment="spaceBetween"), ft.Divider(), ft.Column(list_controls, scroll="auto", expand=True)], expand=True)
        current_view.current.controls = [content]
        page.update()

    def delete(id):
        if db.deactivate_cell(id): show_success(page, "Desativada!"); show_list()
        else: show_error(page, "Erro.")

    def save(e):
        if not name.value or not leader.value: show_warning(page, "Preencha Nome e Líder!"); return
        if db.add_cell(name.value, leader.value, host.value, addr_component["get_full_address"](), day.value, time_f.value, obs.value): show_success(page, "Salvo!"); show_list()
        else: show_error(page, "Erro.")

    def show_form(e=None):
        content = ft.Column([
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=show_list), ft.Text("Nova Célula", size=20, weight="bold")]),
            ft.ResponsiveRow([name, leader, host, day, time_f]),
            ft.Divider(), addr_component["ui"], ft.ResponsiveRow([obs]),
            ft.Button("Salvar", on_click=save, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"))
        ], scroll="auto", expand=True)
        current_view.current.controls = [content]
        page.update()

    col = ft.Column(expand=True, ref=current_view)
    show_list()
    return col

def users_view(page: ft.Page, db: Database, readonly: bool = False):
    if readonly: return ft.Center(ft.Text("Negado"))
    current_view = ft.Ref[ft.Column]()
    u_name = ft.TextField(label="User", col=12)
    u_pass = ft.TextField(label="Senha", password=True, col=12)
    u_admin = ft.Checkbox(label="Admin", col=12)
    p_visit = ft.Checkbox(label="Visitantes", value=True, col=4)
    p_cell = ft.Checkbox(label="Células", col=4)
    p_collab = ft.Checkbox(label="Equipe", col=4)

    def show_list(e=None):
        users = db.get_all_users()
        controls = []
        for u in users:
            uid, uname, is_admin = u[0], u[1], u[2]
            controls.append(ft.ListTile(leading=ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS if is_admin else ft.Icons.PERSON), title=ft.Text(uname), trailing=ft.IconButton(ft.Icons.DELETE, disabled=(uid==1), on_click=lambda e, x=uid: delete(x))))
        
        content = ft.Column([
            ft.Row([ft.Text("Usuários", size=20, weight="bold"), ft.IconButton(ft.Icons.ADD, on_click=show_form, bgcolor=THEME_COLOR, icon_color="white")], alignment="spaceBetween"),
            ft.Divider(), ft.Column(controls, scroll="auto", expand=True)
        ], expand=True)
        current_view.current.controls = [content]
        page.update()

    def delete(id):
        if db.delete_user(id): show_success(page, "Deletado!"); show_list()
        else: show_error(page, "Erro.")

    def save(e):
        if not u_name.value or not u_pass.value: show_warning(page, "Preencha tudo!"); return
        perms = {"visitantes": p_visit.value, "celulas": p_cell.value, "voluntários": p_collab.value}
        if db.add_user(u_name.value, u_pass.value, u_admin.value, perms): show_success(page, "Criado!"); show_list()
        else: show_error(page, "Erro.")

    def show_form(e=None):
        content = ft.Column([
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=show_list), ft.Text("Novo User")]),
            ft.ResponsiveRow([u_name, u_pass, u_admin]),
            ft.Text("Permissões:"), ft.ResponsiveRow([p_visit, p_cell, p_collab]),
            ft.Button("Criar", on_click=save, bgcolor=THEME_COLOR, color="white")
        ], scroll="auto")
        current_view.current.controls = [content]
        page.update()

    col = ft.Column(expand=True, ref=current_view)
    show_list()
    return col

# ==============================================================================
# MAIN APP LOGIC - RESPONSIVIDADE TOTAL
# ==============================================================================

def main(page: ft.Page):
    page.title = APP_TITLE
    page.theme = ft.Theme(color_scheme_seed=THEME_COLOR)
    # Configuração responsiva inicial
    page.padding = 0 
    
    db = Database()
    current_user = {"username": None, "permissions": {}, "readonly": False}
    
    def logout(e=None):
        current_user["username"] = None
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
        
        # Área de conteúdo central
        content_area = ft.Container(expand=True, padding=10)
        
        # Itens de navegação (usados tanto no Rail quanto no Drawer)
        destinations = []
        pages_map = []
        perms = current_user["permissions"]
        
        # Mapa de navegação
        # NOTA: Removi o "Cadastro Visitante" (visitors_view) daqui pois ele agora é acessado pela lista
        nav_items = [
            ("lista_visitantes", ft.Icons.PEOPLE, "Visitantes", visitors_list_view), # Mudei icone e nome
            ("celulas", ft.Icons.GROUPS, "Células", cells_view),
            ("voluntários", ft.Icons.BADGE, "Equipe", volunteers_view),
            ("galeria", ft.Icons.PHOTO_LIBRARY, "Galeria", lambda p, d, readonly: gallery_view(
                p, d, current_user, show_success, show_error, show_warning, show_loading, hide_loading, readonly
            )),
            ("usuarios", ft.Icons.SECURITY, "Usuários", users_view)
        ]

        for perm_key, icon, label, func in nav_items:
            # Verifica se tem permissão (usa 'visitantes' para a lista agora)
            if perms.get(perm_key) or (perm_key == "lista_visitantes" and perms.get("visitantes")):
                destinations.append(ft.NavigationRailDestination(icon=icon, label=label))
                pages_map.append(func)
        
        # Adicionar Logout
        destinations.append(ft.NavigationRailDestination(icon=ft.Icons.LOGOUT, label="Sair"))

        # --- CONTROLES DE NAVEGAÇÃO ---
        rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100, min_extended_width=200,
            leading=ft.Container(get_logo(50), padding=10),
            group_alignment=-0.9,
            destinations=destinations,
            on_change=lambda e: change_page(e.control.selected_index),
            visible=True
        )
        
        drawer = ft.NavigationDrawer(
            controls=[
                ft.Container(height=12),
                ft.Column([get_logo(60), ft.Text(APP_TITLE, weight="bold")], horizontal_alignment="center"),
                ft.Divider(thickness=2),
            ] + [
                ft.NavigationDrawerDestination(icon=d.icon, label=d.label) for d in destinations
            ],
            on_change=lambda e: change_page_drawer(e.control.selected_index)
        )
        page.drawer = drawer

        app_bar = ft.AppBar(
            leading=ft.IconButton(ft.Icons.MENU, on_click=lambda e: page.open(drawer)),
            leading_width=40,
            title=ft.Text(APP_TITLE, size=16),
            center_title=True,
            bgcolor=THEME_COLOR,
            color="white",
            visible=False
        )
        
        # Lógica de troca de telas internas (Novo e Editar)
        def open_visitor_edit(visitor_id):
            # Passa a função change_page(0) como callback para voltar para a lista (índice 0 assumindo que Visitantes é o primeiro)
            # Precisamos saber o índice atual para voltar corretamente
            current_idx = rail.selected_index if rail.selected_index is not None else 0
            content_area.content = visitor_edit_view(page, db, visitor_id, lambda: change_page(current_idx))
            page.update()

        def open_visitor_add():
            current_idx = rail.selected_index if rail.selected_index is not None else 0
            # Abre o formulário de cadastro passando o callback para voltar
            content_area.content = visitors_view(page, db, readonly=False, on_back_callback=lambda: change_page(current_idx))
            page.update()

        def change_page(index):
            if index == len(destinations) - 1: # Logout
                logout()
                return
            
            rail.selected_index = index
            drawer.selected_index = index
            
            view_func = pages_map[index]
            
            # Se for a lista de visitantes, injeta as funções de Adicionar e Editar
            if view_func == visitors_list_view:
                content_area.content = view_func(
                    page, db, 
                    readonly=current_user["readonly"], 
                    on_edit_visitor=open_visitor_edit,
                    on_add_visitor=open_visitor_add # Passa a função de adicionar
                )
            else:
                content_area.content = view_func(page, db, readonly=current_user["readonly"])
            
            page.close(drawer)
            page.update()

        def change_page_drawer(index):
            change_page(index)

        layout_row = ft.Row([rail, ft.VerticalDivider(width=1, visible=True), content_area], expand=True, spacing=0)
        page.add(app_bar, layout_row)

        def handle_resize(e):
            if page.width < 800:
                rail.visible = False
                layout_row.controls[1].visible = False
                app_bar.visible = True
            else:
                rail.visible = True
                layout_row.controls[1].visible = True
                app_bar.visible = False
            page.update()

        page.on_resized = handle_resize
        handle_resize(None)
        
        if pages_map: change_page(0)

    # Iniciar App
    page.add(login_view(page, db, login_success))

if __name__ == "__main__":
    ft.app(main, assets_dir="assets")