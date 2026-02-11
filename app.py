"""
IEQ Jd Portugal - App de Gestão
VERSÃO: Home com Logo YouTube + Responsividade
"""
import flet as ft
import json
import requests
import time
import threading
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional, Dict
import os
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
from gallery_module import add_gallery_methods_to_database, gallery_view
import warnings

# Ignorar avisos de depreciação
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Carregar variáveis de ambiente
load_dotenv()

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================

APP_TITLE_DEFAULT = "IEQ - Jd Portugal"
THEME_COLOR = "#1976D2"

# Configurações via .env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")

# ==============================================================================
# UTILITÁRIOS
# ==============================================================================

def show_top_message(page, message, color, icon):
    snack_content = ft.Container(
        content=ft.Row([
            ft.Icon(icon, color="white"),
            ft.Text(message, color="white", weight="bold", size=14, expand=True)
        ], alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=color, padding=15, border_radius=10,
        shadow=ft.BoxShadow(blur_radius=15, color="black26"),
        left=10, right=10, top=-100, opacity=0,
        animate_position=ft.animation.Animation(500, ft.AnimationCurve.ELASTIC_OUT),
        animate_opacity=ft.animation.Animation(300, ft.AnimationCurve.EASE_IN),
        on_click=lambda e: close_snack(page, e.control)
    )
    page.overlay.append(snack_content)
    page.update()
    snack_content.top = 10; snack_content.opacity = 1; page.update()
    def auto_close():
        time.sleep(4)
        try: close_snack(page, snack_content)
        except: pass
    threading.Thread(target=auto_close, daemon=True).start()

def close_snack(page, container):
    try:
        container.top = -100; container.opacity = 0; page.update()
        time.sleep(0.5)
        if container in page.overlay: page.overlay.remove(container); page.update()
    except: pass

def show_success(page, message): show_top_message(page, message, "green", ft.Icons.CHECK_CIRCLE)
def show_error(page, message): show_top_message(page, message, "red", ft.Icons.ERROR)
def show_warning(page, message): show_top_message(page, message, "orange", ft.Icons.WARNING)
def show_loading(page, message="Processando..."):
    loading = ft.Container(content=ft.Column([ft.ProgressRing(), ft.Text(message, color="white")], horizontal_alignment="center", alignment="center"), bgcolor="black54", expand=True, alignment=ft.alignment.center)
    page.overlay.append(loading); page.update(); return loading
def hide_loading(page, loading):
    if loading in page.overlay: page.overlay.remove(loading); page.update()

def get_youtube_thumbnail(channel_id):
    if not channel_id: return None
    clean_id = channel_id.strip().replace('"', '').replace("'", "")
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={clean_id}"
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            ns = {'yt': 'http://www.youtube.com/xml/schemas/2015', 'atom': 'http://www.w3.org/2005/Atom'}
            entry = root.find('atom:entry', ns)
            if entry is not None:
                vid = entry.find('yt:videoId', ns).text
                return f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg"
    except: pass
    return None

class ViaCEPService:
    BASE_URL = "https://viacep.com.br/ws"
    @staticmethod
    def clean_cep(cep: str) -> str: return ''.join(filter(str.isdigit, cep)) if cep else ""
    @staticmethod
    def format_cep(cep: str) -> str:
        clean = ViaCEPService.clean_cep(cep)
        return f"{clean[:5]}-{clean[5:]}" if len(clean) == 8 else cep
    @staticmethod
    def search_by_cep(cep: str) -> Optional[Dict[str, str]]:
        try:
            clean = ViaCEPService.clean_cep(cep)
            if len(clean) != 8: return None
            response = requests.get(f"{ViaCEPService.BASE_URL}/{clean}/json/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data if 'erro' not in data else None
            return None
        except: return None

def open_whatsapp(phone, name):
    if not phone: return ""
    clean = ''.join(filter(str.isdigit, phone))
    if len(clean) <= 11 and not clean.startswith("55"): clean = "55" + clean
    msg = urllib.parse.quote(f"Olá {name}, paz! Sou da IEQ.")
    return f"https://wa.me/{clean}?text={msg}"

# ==============================================================================
# DATABASE
# ==============================================================================

class Database:
    def __init__(self):
        if SUPABASE_URL and SUPABASE_KEY:
            self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            add_gallery_methods_to_database(Database)
        else:
            self.supabase = None

    # --- Auth & Users ---
    def check_login(self, username, password):
        try:
            response = self.supabase.table('users').select('*').eq('username', username).eq('password', password).execute()
            if response.data:
                user = response.data[0]
                try:
                    self.supabase.table('users').update({'last_login': datetime.now().isoformat()}).eq('id', user['id']).execute()
                except: pass
                return user
            return None
        except: return None

    def get_user_permissions(self, username):
        try:
            res = self.supabase.table('users').select('permissions, is_admin').eq('username', username).execute()
            if res.data:
                u = res.data[0]
                is_admin = u.get('is_admin', False)
                perms = u.get('permissions', {})
                if isinstance(perms, str): perms = json.loads(perms)
                
                perms['is_admin'] = is_admin
                perms['readonly'] = not is_admin
                
                # Módulos PÚBLICOS
                perms['home'] = True 
                perms['galeria'] = True
                perms['celulas'] = True
                
                # Módulo RESTRITO (Visitantes)
                if is_admin:
                    perms['visitantes'] = True
                else:
                    perms['visitantes'] = perms.get('visitantes', False)

                perms['usuarios'] = is_admin
                return perms
            return {'readonly': True}
        except: return {'readonly': True}

    def add_user(self, username, password, is_admin, perms, full_name, email, phone):
        try:
            data = {'username': username, 'password': password, 'full_name': full_name, 'email': email, 'phone': phone, 'is_admin': is_admin, 'permissions': perms if isinstance(perms, dict) else json.loads(perms), 'is_google_auth': False}
            self.supabase.table('users').insert(data).execute()
            return True
        except: return False
    
    def update_user(self, uid, username, password, is_admin, perms, full_name, email, phone):
        try:
            data = {'username': username, 'full_name': full_name, 'email': email, 'phone': phone, 'is_admin': is_admin, 'permissions': perms if isinstance(perms, dict) else json.loads(perms)}
            if password and password.strip(): data['password'] = password
            self.supabase.table('users').update(data).eq('id', uid).execute()
            return True
        except: return False

    def delete_user(self, uid):
        if uid == 1: return False 
        try:
            self.supabase.table('users').delete().eq('id', uid).execute()
            return True
        except: return False

    def get_all_users(self):
        try:
            res = self.supabase.table('users').select('id, username, full_name, email, is_admin, permissions, created_at, last_login').order('full_name').execute()
            result = []
            for u in res.data:
                perms = u['permissions']
                if isinstance(perms, str): perms = json.loads(perms)
                
                # CORREÇÃO FUSO HORÁRIO USUÁRIOS
                created = u.get('created_at')
                last = u.get('last_login')
                # Se houver data, converte UTC -> Local
                # O .astimezone() sem argumentos usa o horário do sistema (Brasil)
                
                result.append((
                    u['id'], 
                    u['username'], 
                    u.get('full_name', ''), 
                    u.get('email', ''), 
                    u['is_admin'], 
                    json.dumps(perms),
                    created,
                    last
                ))
            return result
        except: return []

    def get_user_by_id(self, uid):
        try: return self.supabase.table('users').select('*').eq('id', uid).execute().data[0]
        except: return None

    # --- VISITANTES (CORRIGIDO) ---
    def add_visitor(self, name, phone, email, address, obs):
        try:
            # Força o envio da data/hora local atual para garantir precisão
            data = {
                'name': name, 
                'phone': phone, 
                'email': email, 
                'address': address, 
                'observations': obs,
                'date_visit': datetime.now().isoformat() # <--- Grava a hora exata do seu PC
            }
            self.supabase.table('visitors').insert(data).execute()
            return True
        except: return False

    def get_all_visitors(self):
        try:
            res = self.supabase.table('visitors').select('*').order('date_visit', desc=True).execute()
            result = []
            for v in res.data:
                dv = v.get('date_visit', '')
                dt_visit = None
                if dv:
                    try: 
                        # CORREÇÃO CRÍTICA DE DATA:
                        # 1. replace('Z', '+00:00'): Diz que a data original é UTC
                        # 2. .astimezone(): Converte para o horário do seu PC (Brasil)
                        dt_visit = datetime.fromisoformat(dv.replace('Z', '+00:00')).astimezone()
                    except: pass
                
                # Correção também para a data de contato
                contact_at = v.get('contacted_at')
                
                result.append((
                    v['id'], 
                    v['name'], 
                    v.get('phone'), 
                    v.get('email'), 
                    v.get('address'), 
                    dt_visit, # Data corrigida
                    v.get('observations'),
                    v.get('contacted_by'),
                    contact_at
                ))
            return result
        except: return []

    def update_visitor(self, vid, name, phone, email, address, obs):
        try:
            data = {'name': name, 'phone': phone, 'email': email, 'address': address, 'observations': obs}
            self.supabase.table('visitors').update(data).eq('id', vid).execute()
            return True
        except: return False

    def delete_visitor(self, vid):
        try:
            self.supabase.table('visitors').delete().eq('id', vid).execute()
            return True
        except: return False

    def get_visitor_by_id(self, vid):
        try:
            res = self.supabase.table('visitors').select('*').eq('id', vid).execute()
            if res.data:
                v = res.data[0]
                try: dv = datetime.fromisoformat(v.get('date_visit', '').replace('Z', '+00:00')).strftime("%d/%m/%Y %H:%M")
                except: dv = ""
                return (v['id'], v['name'], v.get('phone'), v.get('email'), v.get('address'), dv, v.get('observations'))
            return None
        except: return None
        
    def mark_visitor_contacted(self, visitor_id, user_name):
        try:
            data = {
                'contacted_by': user_name,
                'contacted_at': datetime.now().isoformat()
            }
            self.supabase.table('visitors').update(data).eq('id', visitor_id).execute()
            return True
        except Exception as e:
            print(f"Erro ao marcar contato: {e}")
            return False

    # --- CELULAS ---
    def add_cell(self, name, leader, host, address, day, time, obs):
        try:
            data = {'name': name, 'leader_name': leader, 'host_name': host, 'address': address, 'meeting_day': day, 'meeting_time': time, 'observations': obs, 'active': True}
            self.supabase.table('cells').insert(data).execute()
            return True
        except: return False

    def get_all_cells(self):
        try:
            res = self.supabase.table('cells').select('*').order('active', desc=True).order('name').execute()
            return [(c['id'], c['name'], c['leader_name'], c.get('host_name'), c.get('address'), c.get('meeting_day'), c.get('meeting_time'), c.get('observations'), c.get('active')) for c in res.data]
        except: return []

    def deactivate_cell(self, cid):
        try:
            self.supabase.table('cells').update({'active': False}).eq('id', cid).execute()
            return True
        except: return False

    def activate_cell(self, cid):
        try:
            self.supabase.table('cells').update({'active': True}).eq('id', cid).execute()
            return True
        except: return False

    def delete_cell_permanent(self, cid):
        try:
            self.supabase.table('cells').delete().eq('id', cid).execute()
            return True
        except: return False

    # --- AGENDA & HOME ---
    def add_event(self, title, desc, date, time, loc, is_recurring):
        try:
            if len(time) == 5: time += ":00"
            data = {'title': title, 'description': desc, 'event_date': date, 'event_time': time, 'location': loc, 'is_recurring': is_recurring}
            self.supabase.table('agenda').insert(data).execute()
            return True
        except Exception as e:
            print(f"Erro add_event: {e}")
            return False

    def update_event(self, eid, title, desc, date, time, loc, is_recurring):
        try:
            if len(time) == 5: time += ":00"
            data = {'title': title, 'description': desc, 'event_date': date, 'event_time': time, 'location': loc, 'is_recurring': is_recurring}
            self.supabase.table('agenda').update(data).eq('id', eid).execute()
            return True
        except Exception as e:
            print(f"Erro update_event: {e}")
            return False

    def sync_agenda(self):
        try:
            res = self.supabase.table('agenda').select('*').execute()
            events = res.data
            if not events: return

            today = datetime.now().date()
            
            for ev in events:
                try:
                    ev_date_obj = datetime.strptime(ev['event_date'], "%Y-%m-%d").date()
                    if ev_date_obj < today:
                        if ev.get('is_recurring'):
                            new_date = ev_date_obj
                            while new_date < today:
                                new_date += timedelta(days=7)
                            self.supabase.table('agenda').update({'event_date': new_date.strftime("%Y-%m-%d")}).eq('id', ev['id']).execute()
                        else:
                            self.delete_event(ev['id'])
                except Exception as e:
                    continue
        except Exception as e:
            print(f"Erro geral sync_agenda: {e}")

    def get_upcoming_events(self):
        try:
            self.sync_agenda()
            today = datetime.now().strftime("%Y-%m-%d")
            return self.supabase.table('agenda').select('*').gte('event_date', today).order('event_date').order('event_time').execute().data
        except: return []

    def delete_event(self, eid):
        try:
            self.supabase.table('agenda').delete().eq('id', eid).execute()
            return True
        except: return False
        
    def get_recent_photos(self, limit=15):
        try:
            res = self.supabase.table('photos').select('storage_path').order('created_at', desc=True).limit(limit).execute()
            return [self.get_photo_url(p['storage_path']) for p in res.data]
        except: return []

# ==============================================================================
# UI COMPONENTS
# ==============================================================================

def get_logo(size=80):
    return ft.Container(
        content=ft.Image(src="logoieq.png", fit="cover", width=size, height=size, error_content=ft.Icon(ft.Icons.CHURCH, size=size*0.6, color="white")),
        width=size, height=size, border_radius=size//2, bgcolor=THEME_COLOR,
        shadow=ft.BoxShadow(blur_radius=10, color="black26"), clip_behavior=ft.ClipBehavior.HARD_EDGE
    )

def address_form_fields(page):
    cep = ft.TextField(label="CEP", keyboard_type=ft.KeyboardType.NUMBER, max_length=9, col={"sm": 6, "md": 3})
    status = ft.Text("", size=12, col={"sm": 6, "md": 9})
    logra = ft.TextField(label="Logradouro", col={"sm": 12, "md": 8})
    num = ft.TextField(label="Nº", col={"sm": 12, "md": 4})
    bairro = ft.TextField(label="Bairro", col={"sm": 12, "md": 4})
    cid = ft.TextField(label="Cidade", col={"sm": 8, "md": 6})
    uf = ft.TextField(label="UF", col={"sm": 4, "md": 2})

    def on_cep_change(e):
        if len(ViaCEPService.clean_cep(cep.value)) < 8: return
        status.value = "Buscando..."; status.color = "blue"; page.update()
        data = ViaCEPService.search_by_cep(cep.value)
        if data:
            logra.value, bairro.value, cid.value, uf.value = data.get('logradouro',''), data.get('bairro',''), data.get('localidade',''), data.get('uf','')
            cep.value = ViaCEPService.format_cep(cep.value)
            status.value = "✓ Encontrado!"; status.color = "green"
        else: status.value = "✗ Inválido"; status.color = "red"
        page.update()

    cep.on_change = on_cep_change
    ui = ft.ResponsiveRow([cep, status, logra, num, bairro, cid, uf], vertical_alignment=ft.CrossAxisAlignment.CENTER)
    return {"ui": ui, "get_full_address": lambda: f"{logra.value}, {num.value} - {bairro.value}, {cid.value}/{uf.value} CEP: {cep.value}", 
            "cep": cep, "logradouro": logra, "numero": num, "bairro": bairro, "cidade": cid, "uf": uf, "status": status}

# ==============================================================================
# VIEWS
# ==============================================================================

def login_view(page, db, on_success):
    # 1. Criamos os campos primeiro
    user = ft.TextField(label="Usuário", col=12)
    pwd = ft.TextField(label="Senha", password=True, can_reveal_password=True, col=12)
    
    # 2. Definimos a função de login
    def try_login(e):
        if not user.value or not pwd.value:
            show_warning(page, "Preencha tudo!")
            return
            
        loading = show_loading(page, "Entrando...")
        time.sleep(0.5) # Simula um tempinho para ver o loading
        
        if db.check_login(user.value, pwd.value):
            hide_loading(page, loading)
            on_success(user.value)
        else:
            hide_loading(page, loading)
            show_error(page, "Dados inválidos.")

    # 3. Agora vinculamos o "Enter" (on_submit) à função
    user.on_submit = try_login
    pwd.on_submit = try_login

    login_card = ft.Container(
        content=ft.Column([
            ft.Text("Login", size=20, weight="bold", color=THEME_COLOR),
            ft.ResponsiveRow([user, pwd]),
            ft.Button("Entrar", on_click=try_login, width=300, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"))
        ], horizontal_alignment="center", spacing=20),
        padding=20, width=400, border=ft.border.all(1, "grey"), border_radius=10, bgcolor="white"
    )

    return ft.Container(
        content=ft.Column([
            get_logo(100),
            ft.Text(APP_TITLE_DEFAULT, size=18, weight="bold", color="grey"),
            login_card
        ], horizontal_alignment="center", alignment=ft.alignment.center, spacing=20, scroll="auto"), 
        padding=10, alignment=ft.alignment.center, expand=True
    )

def home_view(page, db, readonly=False):
    carousel_photos = db.get_recent_photos(15)
    if not carousel_photos: carousel_photos = ["https://via.placeholder.com/300x200?text=Bem-vindo"] * 6
    
    carousel_row = ft.Row(spacing=10, alignment=ft.MainAxisAlignment.CENTER)
    current_start_index = [0]

    def open_lightbox_home(src):
        img_full = ft.Image(src=src, fit=ft.ImageFit.CONTAIN, width=page.width, height=page.height)
        stack = ft.Stack([
            ft.Container(bgcolor="black", opacity=0.9, on_click=lambda e: close_lightbox(stack), expand=True),
            ft.Container(content=img_full, alignment=ft.alignment.center),
            ft.Container(content=ft.IconButton(ft.Icons.CLOSE, icon_color="white", icon_size=30, on_click=lambda e: close_lightbox(stack)), top=20, right=20)
        ], expand=True)
        page.overlay.append(stack); page.update()

    def close_lightbox(stack):
        page.overlay.remove(stack); page.update()

    def update_carousel_view(do_update=True):
        w = page.width if page.width else 800
        
        # Ajuste de quantidade de fotos por tamanho de tela
        if w < 600: num_visible = 3
        elif w < 1000: num_visible = 4
        else: num_visible = 6
        
        spacing = 10; total_spacing = (num_visible - 1) * spacing
        available_width = w - 40; img_width = (available_width - total_spacing) / num_visible
        
        visible_images = []
        for i in range(num_visible):
            idx = (current_start_index[0] + i) % len(carousel_photos)
            src = carousel_photos[idx]
            
            # --- ANIMAÇÃO AQUI ---
            # 1. A Imagem precisa de uma KEY única (src) para o Switcher saber que mudou
            img = ft.Image(
                src=src, 
                key=src, # O SEGREDO: A Key avisa que é uma nova foto
                height=160, 
                width=img_width, 
                fit=ft.ImageFit.COVER, 
                border_radius=8, 
                gapless_playback=True # Evita piscar preto na troca
            )
            
            # 2. Envolvemos a imagem no AnimatedSwitcher
            switcher = ft.AnimatedSwitcher(
                content=img,
                transition=ft.AnimatedSwitcherTransition.FADE, # Efeito Fade
                duration=800, # Duração da animação (ms)
                reverse_duration=100,
                switch_in_curve=ft.AnimationCurve.EASE_IN,
                switch_out_curve=ft.AnimationCurve.EASE_OUT
            )
            
            container = ft.Container(
                content=switcher, 
                on_click=lambda e, s=src: open_lightbox_home(s), 
                ink=True, 
                border_radius=8
            )
            visible_images.append(container)
            
        carousel_row.controls = visible_images
        if do_update:
            try:
                if carousel_row.page: carousel_row.update()
            except: pass

    def cycle_carousel():
        while True:
            time.sleep(4)
            try:
                current_start_index[0] = (current_start_index[0] + 1) % len(carousel_photos)
                update_carousel_view(do_update=True)
            except: break

    update_carousel_view(do_update=False)
    if len(carousel_photos) > 1: threading.Thread(target=cycle_carousel, daemon=True).start()

    clean_id = YOUTUBE_CHANNEL_ID.strip().replace('"', '').replace("'", "") if YOUTUBE_CHANNEL_ID else ""
    thumb_src = get_youtube_thumbnail(clean_id)
    if not thumb_src: thumb_src = "https://img.youtube.com/vi/AKw0E0t2k6c/maxresdefault.jpg"
    live_url = f"https://www.youtube.com/channel/{clean_id}/live" if clean_id else "https://www.youtube.com/"
    streams_url = f"https://www.youtube.com/channel/{clean_id}/streams" if clean_id else "https://www.youtube.com/"

    yt_card = ft.Card(content=ft.Container(content=ft.Column([
        ft.Row([
            ft.Icon(ft.Icons.SMART_DISPLAY, color="red", size=28),
            ft.Text("YouTube", size=20, weight="bold", color="red")
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Stack([ft.Image(src=thumb_src, width=float("inf"), height=200, fit=ft.ImageFit.COVER, border_radius=8), ft.Container(bgcolor="black54", width=float("inf"), height=200, border_radius=8), ft.Container(content=ft.IconButton(ft.Icons.PLAY_CIRCLE_FILL, icon_color="red", icon_size=60, on_click=lambda e: page.launch_url(live_url)), alignment=ft.alignment.center), ft.Container(content=ft.Text("Ao vivo", color="white", size=12), bottom=10, right=10)], height=200),
        ft.Row([ft.TextButton("Ver Cultos Anteriores", icon=ft.Icons.VIDEO_LIBRARY, on_click=lambda e: page.launch_url(streams_url), style=ft.ButtonStyle(color=THEME_COLOR))], alignment=ft.MainAxisAlignment.END)
    ], spacing=10), padding=15), elevation=5)

    agenda_col = ft.Column([], spacing=10)
    
    WEEKDAYS = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}

    def refresh_agenda():
        events = db.get_upcoming_events()
        agenda_col.controls.clear()
        if not events: agenda_col.controls.append(ft.Text("Sem eventos próximos.", italic=True))
        
        today_str = datetime.now().strftime("%Y-%m-%d")

        for ev in events:
            d_obj = datetime.strptime(ev['event_date'], "%Y-%m-%d")
            t_obj = datetime.strptime(ev['event_time'], "%H:%M:%S")
            
            day_num = d_obj.day
            month_str = d_obj.strftime("%b").upper()
            weekday_name = WEEKDAYS[d_obj.weekday()]
            time_str = t_obj.strftime("%H:%M")
            
            line1_text = f"{weekday_name} às {time_str}"
            line2_text = f"Local: {ev['location']}"
            
            is_today = (ev['event_date'] == today_str)
            date_box_color = "green" if is_today else THEME_COLOR 
            
            icon_recur = ft.Icon(ft.Icons.REPEAT, size=16, color="blue", tooltip="Evento Semanal") if ev.get('is_recurring') else ft.Container()

            # Ações do Evento
            actions = ft.Container()
            if not readonly:
                actions = ft.Column([
                    ft.IconButton(ft.Icons.EDIT, icon_color=THEME_COLOR, tooltip="Editar", on_click=lambda e, x=ev: edit_ev_dialog(x)),
                    ft.IconButton(ft.Icons.DELETE, icon_color="red", tooltip="Excluir", on_click=lambda e, x=ev['id']: (db.delete_event(x), refresh_agenda(), show_success(page, "Removido!")))
                ], spacing=0)
            
            card = ft.Card(content=ft.Container(content=ft.Row([
                ft.Container(content=ft.Column([
                    ft.Text(str(day_num), size=24, weight="bold", color="white"), 
                    ft.Text(month_str, size=12, color="white")
                ], alignment="center", spacing=0), bgcolor=date_box_color, width=60, height=60, border_radius=8, alignment=ft.alignment.center),
                
                ft.Column([
                    ft.Row([ft.Text(ev['title'], weight="bold", size=16), icon_recur], spacing=5),
                    ft.Text(line1_text, size=14, color="black", weight="bold" if is_today else "normal"), 
                    ft.Text(line2_text, size=12, color="grey"),
                    ft.Text(ev['description'], size=12, italic=True, color="grey")
                ], expand=True, spacing=2),
                
                actions
            ]), padding=10))
            agenda_col.controls.append(card)
        page.update()

    # --- FUNÇÃO DE EDIÇÃO (JÁ EXISTENTE NO CÓDIGO ANTERIOR) ---
    def edit_ev_dialog(ev_data):
        t = ft.TextField(label="Título *", value=ev_data['title'])
        d = ft.TextField(label="Descrição", value=ev_data['description'] or "")
        tm = ft.TextField(label="Hora (HH:MM) *", value=ev_data['event_time'][:5])
        l = ft.TextField(label="Local", value=ev_data['location'])
        rec = ft.Checkbox(label="Recorrente (Semanal)", value=ev_data.get('is_recurring', False))
        
        db_date_str = ev_data['event_date']
        current_date_obj = datetime.strptime(db_date_str, "%Y-%m-%d")
        formatted_date = current_date_obj.strftime("%d-%m-%Y")
        
        dt = ft.TextField(label="Data (DD-MM-AAAA) *", value=formatted_date, read_only=True, expand=True)

        def on_date_change(e):
            if e.control.value:
                dt.value = e.control.value.strftime("%d-%m-%Y")
                dt.update()

        date_picker = ft.DatePicker(
            on_change=on_date_change,
            first_date=datetime(2000, 1, 1),
            last_date=datetime(2050, 12, 31),
            value=current_date_obj, 
            current_date=current_date_obj,
            date_picker_entry_mode=ft.DatePickerEntryMode.CALENDAR_ONLY
        )
        page.overlay.append(date_picker)
        page.update()

        def save_changes(e):
            if not t.value or not dt.value or not tm.value:
                show_warning(page, "Preencha Título, Data e Hora!"); return
            try:
                date_obj = datetime.strptime(dt.value.strip(), "%d-%m-%Y")
                db_date = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                show_error(page, "Data inválida!"); return

            if db.update_event(ev_data['id'], t.value, d.value, db_date, tm.value, l.value, rec.value):
                page.close(dlg)
                try: page.overlay.remove(date_picker)
                except: pass
                refresh_agenda(); show_success(page, "Evento Atualizado!")
            else:
                show_error(page, "Erro ao atualizar.")

        def close_dlg(e):
            page.close(dlg)
            try: page.overlay.remove(date_picker)
            except: pass
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Editar Evento"),
            content=ft.Column([t, d, ft.Row([dt, ft.IconButton(ft.Icons.CALENDAR_MONTH, icon_color=THEME_COLOR, on_click=lambda _: date_picker.pick_date())], alignment="center"), tm, l, rec], height=400, scroll="auto"),
            actions=[ft.TextButton("Cancelar", on_click=close_dlg), ft.TextButton("Salvar", on_click=save_changes)]
        )
        page.open(dlg)

    def add_ev_dialog(e):
        t = ft.TextField(label="Título *")
        d = ft.TextField(label="Descrição", hint_text="Ex: Trazer prato de doce")
        
        today = datetime.now()
        dt = ft.TextField(label="Data (DD-MM-AAAA) *", hint_text="Clique no calendário ->", read_only=True, expand=True)
        
        def on_date_change(e):
            if e.control.value:
                dt.value = e.control.value.strftime("%d-%m-%Y")
                dt.update()
        
        date_picker = ft.DatePicker(
            on_change=on_date_change,
            first_date=datetime(2000, 1, 1),
            last_date=datetime(2050, 12, 31),
            current_date=today,
            value=today,
            date_picker_entry_mode=ft.DatePickerEntryMode.CALENDAR_ONLY
        )
        page.overlay.append(date_picker)
        page.update()
        
        btn_calendar = ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, icon_color=THEME_COLOR, tooltip="Selecionar Data", on_click=lambda _: date_picker.pick_date())

        tm = ft.TextField(label="Hora (HH:MM) *", value="19:30")
        l = ft.TextField(label="Local", value="Igreja")
        rec = ft.Checkbox(label="Evento Recorrente (Repetir toda semana)", value=False)
        
        def save(e):
            if not t.value or not dt.value or not tm.value:
                show_warning(page, "Preencha Título, Data e Hora!"); return
            try:
                date_obj = datetime.strptime(dt.value.strip(), "%d-%m-%Y")
                db_date = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                show_error(page, "Data inválida!")
                return

            if db.add_event(t.value, d.value, db_date, tm.value, l.value, rec.value): 
                page.close(dlg); 
                try: page.overlay.remove(date_picker)
                except: pass
                refresh_agenda(); show_success(page, "Evento Adicionado!")
            else: 
                show_error(page, "Erro ao salvar.")
        
        def close_dlg(e):
            page.close(dlg)
            try: page.overlay.remove(date_picker)
            except: pass
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Novo Evento"), 
            content=ft.Column([t, d, ft.Row([dt, btn_calendar], alignment="center"), tm, l, rec], height=400, scroll="auto"), 
            actions=[ft.TextButton("Cancelar", on_click=close_dlg), ft.TextButton("Salvar", on_click=save)]
        )
        page.open(dlg)

    refresh_agenda()
    
    agenda_toolbar = ft.Row([ft.Container(expand=True), ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color=THEME_COLOR, on_click=add_ev_dialog) if not readonly else ft.Container()], alignment=ft.MainAxisAlignment.END)

    return ft.ListView([
        ft.Container(content=carousel_row, height=160), 
        ft.Divider(),
        yt_card, ft.Divider(),
        ft.Row([ft.Text("Próximos Eventos", weight="bold", size=16), agenda_toolbar], alignment="spaceBetween"),
        agenda_col
    ], padding=10, spacing=20, expand=True)

def visitors_view(page, db, readonly=False, on_back_callback=None):
    if readonly: return ft.Center(ft.Text("Restrito"))
    
    # --- 1. Definição dos Campos ---
    n = ft.TextField(label="Nome Completo *", prefix_icon=ft.Icons.PERSON, col=12)
    
    # Telefone e Email na mesma linha em telas maiores
    p = ft.TextField(label="WhatsApp / Telefone", prefix_icon=ft.Icons.PHONE, keyboard_type=ft.KeyboardType.PHONE, col={"sm": 12, "md": 6})
    em = ft.TextField(label="E-mail", prefix_icon=ft.Icons.EMAIL, col={"sm": 12, "md": 6})
    
    obs = ft.TextField(label="Observações", multiline=True, min_lines=3, col=12)
    
    # Componente de Endereço (Reaproveitado)
    addr = address_form_fields(page)

    # --- 2. Lógica de Salvar ---
    def save(e):
        if not n.value:
            show_warning(page, "Nome obrigatório!")
            return
            
        loading = show_loading(page, "Salvando...")
        time.sleep(0.3)
        
        if db.add_visitor(n.value, p.value, em.value, addr["get_full_address"](), obs.value):
            hide_loading(page, loading)
            show_success(page, "Visitante salvo com sucesso!")
            
            if on_back_callback:
                on_back_callback()
            else:
                # Limpa o formulário se não tiver callback de voltar
                n.value = ""
                p.value = ""
                em.value = ""
                obs.value = ""
                addr["cep"].value = ""
                addr["logradouro"].value = ""
                addr["numero"].value = ""
                addr["bairro"].value = ""
                addr["cidade"].value = ""
                addr["uf"].value = ""
                addr["status"].value = ""
                page.update()
        else:
            hide_loading(page, loading)
            show_error(page, "Erro ao salvar no banco de dados.")

    header = ft.Row([
        ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: on_back_callback()) if on_back_callback else ft.Container(),
        ft.Text("Novo Visitante", size=20, weight="bold")
    ])

    content = ft.Column([
        header,
        ft.Divider(),
        
        # Dados Pessoais
        ft.ResponsiveRow([n]),
        ft.ResponsiveRow([p, em]),
        
        # Seção Endereço
        ft.Container(height=10), # Espaçamento
        ft.Text("Endereço", weight="bold", size=16),
        addr["ui"],
        
        ft.Divider(),
        
        # Observações e Botão
        ft.ResponsiveRow([obs]),
        ft.Container(
            ft.Button("Salvar Visitante", icon=ft.Icons.SAVE, on_click=save, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"), height=50),
            padding=20,
            alignment=ft.alignment.center
        )
    ], scroll="auto", expand=True)

    return ft.Container(content=content, padding=10, expand=True)

def visitor_edit_view(page, db, vid, back_cb):
    # 1. Busca os dados atuais do visitante
    v = db.get_visitor_by_id(vid)
    if not v:
        show_error(page, "Visitante não encontrado")
        back_cb()
        return ft.Container()

    # 2. Lógica para "desmontar" o endereço salvo (Parsing)
    # Formato esperado: "Rua X, 123 - Centro, Cidade/SP CEP: 12345-678"
    full_address = v[4] if v[4] else ""
    cep_val, log_val, num_val, bai_val, cid_val, uf_val = "", "", "", "", "", ""

    try:
        if " CEP: " in full_address:
            parts = full_address.split(" CEP: ")
            cep_val = parts[1]
            address_part = parts[0] # "Rua X, 123 - Centro, Cidade/SP"
            
            if " - " in address_part:
                street_part, loc_part = address_part.split(" - ", 1)
                
                # Rua e Número
                if ", " in street_part:
                    log_s, num_s = street_part.rsplit(", ", 1) # rsplit pega o último
                    log_val = log_s
                    num_val = num_s
                else:
                    log_val = street_part

                # Bairro e Cidade/UF
                if ", " in loc_part:
                    bai_s, city_uf = loc_part.split(", ", 1)
                    bai_val = bai_s
                    if "/" in city_uf:
                        cid_s, uf_s = city_uf.split("/")
                        cid_val = cid_s
                        uf_val = uf_s
                else:
                    bai_val = loc_part
    except:
        pass # Se falhar o parsing, os campos ficam vazios para o usuário preencher

    # 3. Definição dos Campos com Valores Iniciais
    n = ft.TextField(label="Nome Completo *", value=v[1], prefix_icon=ft.Icons.PERSON, col=12)
    p = ft.TextField(label="WhatsApp / Telefone", value=v[2], prefix_icon=ft.Icons.PHONE, keyboard_type=ft.KeyboardType.PHONE, col={"sm": 12, "md": 6})
    em = ft.TextField(label="E-mail", value=v[3], prefix_icon=ft.Icons.EMAIL, col={"sm": 12, "md": 6})
    obs = ft.TextField(label="Observações", value=v[6], multiline=True, min_lines=3, col=12)

    # Componente de Endereço (Preenchido)
    addr = address_form_fields(page)
    addr["cep"].value = cep_val
    addr["logradouro"].value = log_val
    addr["numero"].value = num_val
    addr["bairro"].value = bai_val
    addr["cidade"].value = cid_val
    addr["uf"].value = uf_val

    # 4. Função Salvar (Atualizar)
    def save(e):
        if not n.value:
            show_warning(page, "Nome obrigatório!")
            return
            
        full_addr_str = addr["get_full_address"]()
        
        if db.update_visitor(vid, n.value, p.value, em.value, full_addr_str, obs.value):
            show_success(page, "Visitante atualizado!")
            back_cb()
        else:
            show_error(page, "Erro ao atualizar.")

    # 5. Layout Padronizado
    header = ft.Row([
        ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: back_cb()),
        ft.Text("Editar Visitante", size=20, weight="bold")
    ])

    content = ft.Column([
        header,
        ft.Divider(),
        
        ft.ResponsiveRow([n]),
        ft.ResponsiveRow([p, em]),
        
        ft.Container(height=10),
        ft.Text("Endereço", weight="bold", size=16),
        addr["ui"],
        
        ft.Divider(),
        
        ft.ResponsiveRow([obs]),
        ft.Container(
            ft.Button("Salvar Alterações", icon=ft.Icons.SAVE, on_click=save, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"), height=50),
            padding=20,
            alignment=ft.alignment.center
        )
    ], scroll="auto", expand=True)

    return ft.Container(content=content, padding=10, expand=True)

def visitors_list_view(page, db, user_state, readonly=False, on_edit_visitor=None, on_add_visitor=None):
    view = ft.Ref[ft.Column]()
    
    # Campo de busca (Estilizado para o Cabeçalho)
    search_field = ft.TextField(
        hint_text="Buscar visitante...",
        prefix_icon=ft.Icons.SEARCH,
        width=250,
        height=40,
        text_size=14,
        content_padding=10,
        border_radius=20,
        on_change=lambda e: show_list(e.control.value)
    )

    WEEKDAYS = {0: "Segunda", 1: "Terça", 2: "Quarta", 3: "Quinta", 4: "Sexta", 5: "Sábado", 6: "Domingo"}

    def format_visit_date(dt_obj):
        if not dt_obj: return "-"
        try:
            day_str = dt_obj.strftime("%d/%m")
            weekday = WEEKDAYS[dt_obj.weekday()]
            return f"{day_str}\n({weekday})"
        except: return "-"

    def format_contact_info(name, date_iso):
        if not name or not date_iso: return None
        try:
            dt = datetime.fromisoformat(date_iso.replace('Z', '+00:00'))
            fmt = dt.strftime("%d/%m %H:%M")
            return f"{name}\n{fmt}"
        except: return f"{name}"

    def register_contact(vid):
        current_user = user_state.get("user", "Desconhecido")
        if db.mark_visitor_contacted(vid, current_user):
            show_success(page, "Contato registrado!")
            show_list(search_field.value)
        else:
            show_error(page, "Erro ao registrar.")

    def delete_v(vid, name):
        def conf(e):
            if db.delete_visitor(vid): page.close(dlg); show_success(page, "Deletado!"); show_list(search_field.value)
        dlg = ft.AlertDialog(title=ft.Text("Excluir?"), content=ft.Text(f"Apagar {name}?"), actions=[ft.TextButton("Não", on_click=lambda e: page.close(dlg)), ft.TextButton("Sim", on_click=conf)])
        page.open(dlg)

    def show_list(search_term=""):
        items = db.get_all_visitors()
        
        if search_term:
            st = search_term.lower()
            items = [v for v in items if st in v[1].lower()]

        columns = [
            ft.DataColumn(ft.Text("Data Visita")),
            ft.DataColumn(ft.Text("Nome / Tel")),
            ft.DataColumn(ft.Text("Status do Contato")),
            ft.DataColumn(ft.Text("Ações")),
        ]
        
        rows = []
        for v in items:
            vid, name, phone, email, addr, date_obj, obs, c_by, c_at = v
            
            date_cell = ft.Text(format_visit_date(date_obj), size=12, text_align="center")

            name_col = ft.Column([
                ft.Text(name, weight="bold"),
                ft.Text(phone if phone else "Sem telefone", size=12, color="grey")
            ], spacing=2, alignment="center")

            contact_info = format_contact_info(c_by, c_at)
            
            if contact_info:
                status_cell = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color="green", size=16),
                        ft.Text(contact_info, size=11, color="green")
                    ], spacing=5),
                    padding=5, border=ft.border.all(1, "green"), border_radius=8
                )
            else:
                status_cell = ft.ElevatedButton(
                    "Marcar Contato", 
                    icon=ft.Icons.HOW_TO_REG, 
                    icon_color="white",
                    color="white",
                    bgcolor="orange",
                    height=30,
                    style=ft.ButtonStyle(padding=10),
                    on_click=lambda e, x=vid: register_contact(x)
                )

            btns = []
            if phone: 
                btns.append(ft.IconButton(
                    content=ft.Image(src="https://img.icons8.com/color/48/whatsapp--v1.png", width=28, height=28),
                    tooltip="Abrir WhatsApp", 
                    url=open_whatsapp(phone, name)
                ))
            
            if not readonly:
                if on_edit_visitor: 
                    btns.append(ft.IconButton(ft.Icons.EDIT, icon_color=THEME_COLOR, tooltip="Editar", on_click=lambda e, x=vid: on_edit_visitor(x)))
                btns.append(ft.IconButton(ft.Icons.DELETE, icon_color="red", tooltip="Excluir", on_click=lambda e, x=vid, n=name: delete_v(x, n)))

            rows.append(ft.DataRow(cells=[
                ft.DataCell(date_cell),
                ft.DataCell(name_col),
                ft.DataCell(status_cell),
                ft.DataCell(ft.Row(btns, spacing=0)),
            ]))

        table = ft.DataTable(
            columns=columns, 
            rows=rows, 
            heading_row_color=ft.colors.GREY_200, 
            column_spacing=20,
            data_row_min_height=60
        )
        
        if not view.current.controls:
            add_btn = ft.Container() 
            if not readonly and on_add_visitor:
                add_btn = ft.ElevatedButton(
                    "Novo", 
                    icon=ft.Icons.ADD, 
                    on_click=lambda e: on_add_visitor(), 
                    style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white")
                )
            
            header_row = ft.Row(
                controls=[
                    add_btn,
                    search_field 
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            )
            
            view.current.controls = [
                header_row,
                ft.Divider(),
                # AQUI ESTÁ A CORREÇÃO: vertical_alignment=START
                ft.Row([table], scroll="always", expand=True, vertical_alignment=ft.CrossAxisAlignment.START)
            ]
        else:
            view.current.controls[-1] = ft.Row([table], scroll="always", expand=True, vertical_alignment=ft.CrossAxisAlignment.START)
            
        page.update()
    
    col = ft.Column(expand=True, ref=view)
    show_list()
    return ft.Container(col, padding=10, expand=True)

def cells_view(page, db, readonly=False):
    view = ft.Ref[ft.Column]()
    
    filter_dd = ft.Dropdown(
        width=120,
        text_size=13,
        content_padding=10,
        options=[ft.dropdown.Option("Todas"), ft.dropdown.Option("Ativas"), ft.dropdown.Option("Inativas")],
        value="Todas",
        on_change=lambda e: show_list(),
        visible=not readonly
    )
    
    def open_google_maps(address):
        if not address: show_warning(page, "Endereço não cadastrado."); return
        page.launch_url(f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(address)}")

    def confirm_hard_delete(cid, cname):
        def delete(e):
            page.close(dlg)
            if db.delete_cell_permanent(cid): show_success(page, "Registro apagado!"); show_list()
            else: show_error(page, "Erro.")
        dlg = ft.AlertDialog(title=ft.Text("Exclusão Permanente"), content=ft.Text(f"Apagar '{cname}' do banco?"), actions=[ft.TextButton("Cancelar", on_click=lambda e: page.close(dlg)), ft.TextButton("Apagar", on_click=delete, style=ft.ButtonStyle(color="red"))]); page.open(dlg)

    def show_list():
        items = db.get_all_cells()
        if readonly: current_filter = "Ativas"
        else: current_filter = filter_dd.value
        filtered_items = []
        for c in items:
            c_active = c[8]
            if current_filter == "Todas": filtered_items.append(c)
            elif current_filter == "Ativas" and c_active: filtered_items.append(c)
            elif current_filter == "Inativas" and not c_active: filtered_items.append(c)
        if not filtered_items: content = ft.Text("Nenhum registro.", color="grey")
        else:
            cell_cards = []
            for c in filtered_items:
                c_id, c_name, c_leader, c_host, c_address, c_day, c_time, c_obs, c_active = c
                card_bg = THEME_COLOR if c_active else ft.colors.GREY_700
                status_icon = ft.Icons.HOME_FILLED if c_active else ft.Icons.HOME_WORK_OUTLINED
                opacity = 1.0 if c_active else 0.8
                admin_actions = ft.Container()
                if not readonly:
                    if c_active: admin_actions = ft.IconButton(ft.Icons.DELETE, icon_color="red", tooltip="Desativar", on_click=lambda e, x=c_id: (db.deactivate_cell(x), show_list()))
                    else: admin_actions = ft.Row([ft.IconButton(ft.Icons.RESTORE, icon_color="green", tooltip="Reativar", on_click=lambda e, x=c_id: (db.activate_cell(x), show_list())), ft.IconButton(ft.Icons.DELETE_FOREVER, icon_color="red", tooltip="Excluir", on_click=lambda e, x=c_id, n=c_name: confirm_hard_delete(x, n))], spacing=0)
                
                # Card Ajustado
                card = ft.Card(content=ft.Container(content=ft.Column([
                    ft.Container(content=ft.Column([ft.Icon(status_icon, size=40, color="white"), ft.Text(c_day.upper(), weight="bold", color="white", size=12), ft.Text(c_time, weight="bold", color="white", size=20), ft.Text("INATIVA" if not c_active else "", color="white", size=10, weight="bold")], horizontal_alignment="center", spacing=2), bgcolor=card_bg, height=130, alignment=ft.alignment.center, border_radius=ft.border_radius.only(top_left=10, top_right=10), clip_behavior=ft.ClipBehavior.HARD_EDGE),
                    ft.Container(content=ft.Column([
                        # Título agora é o nome gerado (Ex: Casa de João)
                        ft.Text(c_name, weight="bold", size=18, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS), 
                        ft.Divider(height=10, color="transparent"),
                        ft.Row([ft.Icon(ft.Icons.PERSON, size=16, color="grey"), ft.Text(f"Líder: {c_leader}", size=13, color="grey", expand=True)]),
                        ft.Row([ft.Icon(ft.Icons.REAL_ESTATE_AGENT, size=16, color="grey"), ft.Text(f"Anfitrião: {c_host}", size=13, color="grey", expand=True)]),
                        ft.Row([ft.Icon(ft.Icons.LOCATION_ON, size=16, color="red"), ft.Text(c_address if c_address else "Sem endereço", size=12, color="grey", expand=True, no_wrap=True)]) if c_address else ft.Container(),
                        ft.Divider(),
                        ft.Row([ft.ElevatedButton("Abrir Mapa", icon=ft.Icons.MAP, icon_color="white", bgcolor="green", color="white", style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)), on_click=lambda e, addr=c_address: open_google_maps(addr), visible=bool(c_address)), admin_actions], alignment="spaceBetween")
                    ], spacing=5), padding=15)
                ], spacing=0), opacity=opacity), col={"sm": 12, "md": 6, "lg": 4, "xl": 3}, elevation=4)
                cell_cards.append(card)
            content = ft.ResponsiveRow(cell_cards)
        
        toolbar = ft.Row([
            filter_dd,
            ft.IconButton(ft.Icons.ADD, on_click=show_form, bgcolor=THEME_COLOR, icon_color="white") if not readonly else ft.Container()
        ], alignment=ft.MainAxisAlignment.END)

        view.current.controls = [toolbar, ft.Divider(), ft.Column([content], scroll="auto", expand=True)]
        page.update()

    def show_form(e):
        # CAMPO NOME REMOVIDO
        # Anfitrião e Líder agora são os principais
        h = ft.TextField(label="Anfitrião (Dono da Casa) *", col={"sm":12,"md":6})
        l = ft.TextField(label="Líder *", col={"sm":12,"md":6})
        
        t = ft.TextField(label="Horário", col={"sm":12,"md":6})
        o = ft.TextField(label="Obs", multiline=True, col=12)
        d = ft.Dropdown(label="Dia", options=[ft.dropdown.Option(x) for x in ["Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira","Sexta-feira","Sábado","Domingo"]], col={"sm":12,"md":6})
        addr = address_form_fields(page)

        def save(e):
            if not l.value or not h.value: # Valida os dois campos
                show_warning(page, "Preencha Líder e Anfitrião!"); return
            
            # GERA O NOME AUTOMATICAMENTE: "Casa de [Anfitrião]"
            generated_name = f"Casa de {h.value}"
            
            if db.add_cell(generated_name, l.value, h.value, addr["get_full_address"](), d.value, t.value, o.value): 
                show_success(page, "Salvo!"); show_list()
            else: 
                show_error(page, "Erro.")

        view.current.controls = [ft.Column([
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: show_list()), ft.Text("Nova Casa", size=20, weight="bold")]), 
            ft.Divider(), 
            ft.ResponsiveRow([h, l]), # Primeira linha: Anfitrião e Líder
            ft.ResponsiveRow([d, t]), # Segunda linha: Dia e Hora
            ft.Text("Endereço", weight="bold"), 
            addr["ui"], 
            ft.Divider(), 
            ft.ResponsiveRow([o]), 
            ft.Container(ft.Button("Salvar", on_click=save, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white")), padding=10)
        ], scroll="auto", expand=True)]
        page.update()

    col = ft.Column(expand=True, ref=view); show_list(); return col

def users_view(page, db, readonly=False):
    if readonly: return ft.Center(ft.Text("Negado"))
    view = ft.Ref[ft.Column]()
    
    # Campo de busca (Estilizado igual Visitantes)
    search_field = ft.TextField(
        hint_text="Buscar usuário...", 
        prefix_icon=ft.Icons.SEARCH, 
        width=250,
        height=40,
        text_size=14,
        content_padding=10,
        border_radius=20,
        on_change=lambda e: show_list(e.control.value)
    )

    def format_date(iso_str):
        if not iso_str: return "-"
        try:
            dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
            return dt.strftime("%d/%m/%Y %H:%M")
        except: return iso_str

    def show_list(search_term=""):
        items = db.get_all_users()
        
        if search_term:
            st = search_term.lower()
            items = [u for u in items if st in u[1].lower() or st in u[2].lower()]

        columns = [
            ft.DataColumn(ft.Text("Nome")),
            ft.DataColumn(ft.Text("Usuário")),
            ft.DataColumn(ft.Text("Perfil")),
            ft.DataColumn(ft.Text("Acesso Visitantes")),
            ft.DataColumn(ft.Text("Último Login")),
            ft.DataColumn(ft.Text("Ações")),
        ]
        
        rows = []
        for u in items:
            uid, uname, fname, email, is_adm, perms_json, created, last = u
            
            perms = json.loads(perms_json) if isinstance(perms_json, str) else (perms_json or {})
            has_visitor_access = perms.get('visitantes', False) or is_adm

            role = ft.Container(
                content=ft.Text("ADMIN" if is_adm else "Usuário", size=10, weight="bold", color="white"),
                bgcolor="red" if is_adm else "green", padding=5, border_radius=5
            )
            
            vis_access = ft.Icon(ft.Icons.CHECK_CIRCLE, color="green", size=16) if has_visitor_access else ft.Icon(ft.Icons.CANCEL, color="grey", size=16)

            actions = ft.Row([
                ft.IconButton(ft.Icons.EDIT, icon_color=THEME_COLOR, tooltip="Editar", on_click=lambda e, x=uid: show_edit(x)),
                ft.IconButton(ft.Icons.DELETE, icon_color="red", tooltip="Excluir", disabled=(uid==1), on_click=lambda e, x=uid: (db.delete_user(x), show_list(search_field.value)))
            ], spacing=0)

            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(fname, weight="bold")),
                ft.DataCell(ft.Text(uname)),
                ft.DataCell(role),
                ft.DataCell(vis_access),
                ft.DataCell(ft.Text(format_date(last), size=12)),
                ft.DataCell(actions),
            ]))

        table = ft.DataTable(columns=columns, rows=rows, heading_row_color=ft.colors.GREY_200, column_spacing=20)
        
        # --- LAYOUT PADRONIZADO ---
        if not view.current.controls:
            # Botão Novo
            add_btn = ft.ElevatedButton(
                "Novo", 
                icon=ft.Icons.ADD, 
                on_click=show_form, 
                style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white")
            )
            
            # Cabeçalho Unificado (Botão <--> Busca)
            header_row = ft.Row(
                controls=[add_btn, search_field],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            )
            
            view.current.controls = [
                header_row, 
                ft.Divider(), 
                # Tabela alinhada ao TOPO (START)
                ft.Row([table], scroll="always", expand=True, vertical_alignment=ft.CrossAxisAlignment.START)
            ]
        else:
            # Atualiza apenas a tabela mantendo o alinhamento
            view.current.controls[-1] = ft.Row([table], scroll="always", expand=True, vertical_alignment=ft.CrossAxisAlignment.START)
            
        page.update()
    
    def show_form(e):
        fn, em, ph, u, p = ft.TextField(label="Nome *", col=12), ft.TextField(label="Email", col=6), ft.TextField(label="Tel", col=6), ft.TextField(label="Login *", col=6), ft.TextField(label="Senha *", password=True, col=6)
        adm = ft.Checkbox(label="Administrador (Acesso Total)", col=12)
        v = ft.Checkbox(label="Permitir Acesso a Visitantes", col=12, value=False)
        
        def save(e):
            perms_dict = {"visitantes": v.value, "celulas": True, "galeria": True}
            if db.add_user(u.value, p.value, adm.value, perms_dict, fn.value, em.value, ph.value): 
                view.current.controls.clear(); show_list(); show_success(page, "Criado!")
            else: show_error(page, "Erro.")
            
        view.current.controls = [ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: (view.current.controls.clear(), show_list())), ft.Text("Novo Usuário")]), ft.Column([ft.ResponsiveRow([fn,em,ph,u,p,adm,v]), ft.Container(ft.Button("Criar", on_click=save, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white")), padding=20)], scroll="auto", expand=True)]; page.update()

    def show_edit(uid):
        ud = db.get_user_by_id(uid)
        if not ud: return
        fn, em, ph, u, p = ft.TextField(label="Nome", value=ud['full_name'], col=12), ft.TextField(label="Email", value=ud['email'], col=6), ft.TextField(label="Tel", value=ud['phone'], col=6), ft.TextField(label="Login", value=ud['username'], col=6), ft.TextField(label="Senha (vazio=manter)", password=True, col=6)
        
        adm = ft.Checkbox(label="Administrador", value=ud['is_admin'], col=12)
        perms = ud['permissions'] if isinstance(ud['permissions'], dict) else json.loads(ud['permissions'] or '{}')
        v = ft.Checkbox(label="Permitir Acesso a Visitantes", value=perms.get('visitantes', False), col=12)
        
        def upd(e):
            perms_dict = {"visitantes": v.value, "celulas": True, "galeria": True}
            if db.update_user(uid, u.value, p.value, adm.value, perms_dict, fn.value, em.value, ph.value): 
                view.current.controls.clear(); show_list(); show_success(page, "Atualizado!")
            else: show_error(page, "Erro.")
            
        view.current.controls = [ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: (view.current.controls.clear(), show_list())), ft.Text("Editar Usuário")]), ft.Column([ft.ResponsiveRow([fn,em,ph,u,p,adm,v]), ft.Container(ft.Button("Salvar", on_click=upd, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white")), padding=20)], scroll="auto", expand=True)]; page.update()

    col = ft.Column(expand=True, ref=view); show_list(); return col

# ==============================================================================
# MAIN
# ==============================================================================

def main(page: ft.Page):
    page.title = APP_TITLE_DEFAULT
    page.theme = ft.Theme(color_scheme_seed=THEME_COLOR)
    page.padding = 0
    
    db = Database()
    user_state = {"user": None, "perms": {}, "readonly": False}

    def logout(e=None):
        # 1. Limpa o estado do usuário
        user_state["user"] = None
        
        # 2. IMPORTANTE: Para de ouvir o redimensionamento do dashboard antigo
        page.on_resized = None 
        
        # 3. Limpa qualquer Drawer (menu lateral) aberto
        page.drawer = None
        
        # 4. Limpa overlays (snackbars ou loadings travados)
        page.overlay.clear()
        
        # 5. Limpa a tela e desenha o Login
        page.clean()
        page.add(ft.SafeArea(login_view(page, db, on_login_success), expand=True))
        page.update()

    def on_login_success(username):
        user_state["user"] = username
        perms = db.get_user_permissions(username)
        user_state["perms"] = perms
        user_state["readonly"] = perms.get("readonly", True)
        dashboard()

    def dashboard():
        page.clean()
        page.overlay.clear() # Garante que não sobrou loading do login
        content = ft.Container(expand=True, padding=10)
        
        menu_data = [
            ("home", ft.Icons.HOME, "Início"),
            ("lista_visitantes", ft.Icons.PEOPLE, "Visitantes"),
            ("celulas", ft.Icons.GROUPS, "Casas de Cornélio"),
            ("galeria", ft.Icons.PHOTO_LIBRARY, "Galeria"),
            ("usuarios", ft.Icons.SECURITY, "Gestão de Usuários")
        ]
        
        view_map = {
            "home": home_view,
            "lista_visitantes": visitors_list_view,
            "celulas": cells_view,
            "galeria": lambda p, d, ro: gallery_view(p, d, user_state, show_success, show_error, show_warning, show_loading, hide_loading, ro),
            "usuarios": users_view
        }
        
        destinations = []
        active_pages = []
        
        perms = user_state["perms"]
        
        for k, icon, label in menu_data:
            if k == "home" or perms.get(k) or (k == "lista_visitantes" and perms.get("visitantes")):
                destinations.append(ft.NavigationRailDestination(icon=icon, label=label))
                active_pages.append((k, view_map[k], label, icon))
        
        destinations.append(ft.NavigationRailDestination(icon=ft.Icons.LOGOUT, label="Sair"))

        # Lógica de Saudação
        hour = datetime.now().hour
        current_user_name = user_state["user"].capitalize() if user_state["user"] else "Visitante"
        
        if 5 <= hour < 12:
            greeting_text = f"Bom dia, {current_user_name}"; greeting_icon = ft.Icons.WB_SUNNY; greeting_color = "yellow"
        elif 12 <= hour < 18:
            greeting_text = f"Boa tarde, {current_user_name}"; greeting_icon = ft.Icons.WB_SUNNY; greeting_color = "orange"
        else:
            greeting_text = f"Boa noite, {current_user_name}"; greeting_icon = ft.Icons.NIGHTLIGHT_ROUND; greeting_color = "blue"

        rail = ft.NavigationRail(selected_index=0, label_type=ft.NavigationRailLabelType.ALL, min_width=100, min_extended_width=200, leading=ft.Container(get_logo(50), padding=10), destinations=destinations, on_change=lambda e: nav(e.control.selected_index))
        
        drawer = ft.NavigationDrawer(controls=[
            ft.Container(height=20),
            ft.Column([
                get_logo(80),
                ft.Container(height=10),
                ft.Row([ft.Icon(greeting_icon, color=greeting_color, size=24), ft.Text(greeting_text, weight="bold", size=16)], alignment=ft.MainAxisAlignment.CENTER, spacing=10)
            ], horizontal_alignment="center"),
            ft.Divider(),
        ] + [ft.NavigationDrawerDestination(icon=d.icon, label=d.label) for d in destinations], on_change=lambda e: nav(e.control.selected_index))
        
        page.drawer = drawer
        
        # Header Dinâmico
        header_title = ft.Text(APP_TITLE_DEFAULT, size=20, weight="bold", color="white")
        header_icon = ft.Icon(ft.Icons.HOME, color="white", size=28)
        
        header = ft.Container(
            content=ft.Row([
                ft.IconButton(ft.Icons.MENU, on_click=lambda e: page.open(drawer), icon_color="white"),
                ft.Row([header_icon, header_title], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            ]),
            bgcolor=THEME_COLOR, padding=10, shadow=ft.BoxShadow(blur_radius=5, color="black26")
        )

        def nav(idx):
            if idx == len(destinations)-1: logout(); return
            rail.selected_index = idx; drawer.selected_index = idx
            
            key, func, label, icon = active_pages[idx]
            header_title.value = label; header_icon.name = icon; header.update()
            
            if func == visitors_list_view:
                content.content = func(page, db, user_state, user_state["readonly"], on_edit_visitor=lambda vid: (content.__setattr__("content", visitor_edit_view(page, db, vid, lambda: nav(idx))), page.update()), on_add_visitor=lambda: (content.__setattr__("content", visitors_view(page, db, user_state["readonly"], lambda: nav(idx))), page.update()))
            else: content.content = func(page, db, user_state["readonly"])
            
            page.close(drawer); page.update()

        row = ft.Row([rail, ft.VerticalDivider(width=1), content], expand=True, spacing=0)
        
        page.add(ft.SafeArea(ft.Column([header, ft.Container(row, expand=True)], spacing=0, expand=True), expand=True))

        def resize(e):
            is_mobile = page.width < 800
            rail.visible = not is_mobile; row.controls[1].visible = not is_mobile; header.visible = is_mobile; page.update()
        
        page.on_resized = resize; resize(None); nav(0)

    page.add(ft.SafeArea(login_view(page, db, on_login_success), expand=True))

if __name__ == "__main__":
    ft.app(
        target=main, 
        assets_dir="assets", 
        view=ft.WEB_BROWSER, 
        port=8080, 
        host="0.0.0.0"
    )