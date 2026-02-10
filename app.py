"""
IEQ Gestão - Sistema Integrado de Gestão Eclesiástica
VERSÃO: Permissões Estritas (Admin vs Usuário Leitura)
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
from supabase import create_client, Client
from dotenv import load_dotenv
from gallery_module import add_gallery_methods_to_database, gallery_view

# Carregar variáveis de ambiente
load_dotenv()

# ==============================================================================
# CONFIGURAÇÕES E UTILITÁRIOS
# ==============================================================================

APP_TITLE = "IEQ Jd Portugal - Araraquara"
THEME_COLOR = "#1976D2"

# Configurações via .env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("AVISO: SUPABASE_URL e SUPABASE_KEY não encontrados no .env")

# ==============================================================================
# FUNÇÕES DE FEEDBACK VISUAL
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
    snack_content.top = 10
    snack_content.opacity = 1
    page.update()
    def auto_close():
        time.sleep(4)
        try: close_snack(page, snack_content)
        except: pass
    threading.Thread(target=auto_close, daemon=True).start()

def close_snack(page, container):
    try:
        container.top = -100
        container.opacity = 0
        page.update()
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

# --- Busca Thumbnail do YouTube ---
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
            if entry:
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
# CAMADA DE DADOS (SUPABASE)
# ==============================================================================

class Database:
    def __init__(self):
        if SUPABASE_URL and SUPABASE_KEY:
            self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            print("✓ Conectado ao Supabase")
            add_gallery_methods_to_database(Database)
        else:
            self.supabase = None
            print("✗ Erro: Credenciais ausentes")

    # --- Auth & Users ---
    def check_login(self, username, password):
        try:
            response = self.supabase.table('users').select('*').eq('username', username).eq('password', password).execute()
            return response.data[0] if response.data else None
        except: return None
    
    def check_user_exists(self, username):
        try: return bool(self.supabase.table('users').select('*').eq('username', username).execute().data)
        except: return False

    def get_user_permissions(self, username):
        """
        Define permissões estritas:
        - Admin: Acesso total (readonly = False)
        - Usuário: Apenas leitura (readonly = True)
        """
        try:
            res = self.supabase.table('users').select('permissions, is_admin').eq('username', username).execute()
            if res.data:
                u = res.data[0]
                is_admin = u.get('is_admin', False)
                
                # Permissões base
                perms = u.get('permissions', {})
                if isinstance(perms, str): perms = json.loads(perms)
                
                # Regra Mestra: Se não for admin, é SOMENTE LEITURA
                perms['readonly'] = not is_admin
                perms['is_admin'] = is_admin
                perms['home'] = True 
                
                # Se for admin, garante acesso a tudo
                if is_admin:
                    perms.update({"visitantes": True, "celulas": True, "usuarios": True, "galeria": True})
                else:
                    # Se for usuário comum, garante que não pode acessar gestão de usuários
                    perms['usuarios'] = False 
                    
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
            res = self.supabase.table('users').select('id, username, full_name, email, is_admin, permissions').order('full_name').execute()
            return [(u['id'], u['username'], u.get('full_name', ''), u.get('email', ''), u['is_admin'], json.dumps(u['permissions'])) for u in res.data]
        except: return []

    def get_user_by_id(self, uid):
        try: return self.supabase.table('users').select('*').eq('id', uid).execute().data[0]
        except: return None

    # --- Visitantes ---
    def add_visitor(self, name, phone, email, address, obs):
        try:
            data = {'name': name, 'phone': phone, 'email': email, 'address': address, 'observations': obs}
            self.supabase.table('visitors').insert(data).execute()
            return True
        except: return False

    def get_all_visitors(self):
        try:
            res = self.supabase.table('visitors').select('*').order('date_visit', desc=True).execute()
            result = []
            for v in res.data:
                dv = v.get('date_visit', '')
                try: dv = datetime.fromisoformat(dv.replace('Z', '+00:00')).strftime("%d/%m/%Y %H:%M")
                except: pass
                result.append((v['id'], v['name'], v.get('phone'), v.get('email'), v.get('address'), dv, v.get('observations')))
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

    # --- Casas de Cornélio ---
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
    def add_event(self, title, desc, date, time, loc):
        try:
            data = {'title': title, 'description': desc, 'event_date': date, 'event_time': time, 'location': loc}
            self.supabase.table('agenda').insert(data).execute()
            return True
        except: return False

    def get_upcoming_events(self):
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            return self.supabase.table('agenda').select('*').gte('event_date', today).order('event_date').execute().data
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
    user = ft.TextField(label="Usuário", col=12)
    pwd = ft.TextField(label="Senha", password=True, can_reveal_password=True, col=12)
    
    def try_login(e):
        if not user.value or not pwd.value: show_warning(page, "Preencha tudo!"); return
        loading = show_loading(page, "Entrando...")
        time.sleep(0.5)
        if db.check_login(user.value, pwd.value):
            hide_loading(page, loading); on_success(user.value)
        else: hide_loading(page, loading); show_error(page, "Dados inválidos.")

    return ft.Container(
        content=ft.Column([
            get_logo(100),
            ft.Text(APP_TITLE, size=18, weight="bold", color="grey"),
            ft.Container(content=ft.Column([
                ft.Text("Login", size=20, weight="bold", color=THEME_COLOR),
                ft.ResponsiveRow([user, pwd]),
                ft.Button("Entrar", on_click=try_login, width=300, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"))
            ], horizontal_alignment="center", spacing=20), padding=20, width=400, border=ft.border.all(1, "grey"), border_radius=10)
        ], horizontal_alignment="center", alignment=ft.alignment.center),
        padding=10, alignment=ft.alignment.center, expand=True
    )

def home_view(page, db, readonly=False):
    # --- 1. Carrossel de Fotos ---
    carousel_photos = db.get_recent_photos(15)
    if not carousel_photos: carousel_photos = ["https://via.placeholder.com/300x200?text=Bem-vindo"] * 6
    
    carousel_row = ft.Row(spacing=10, alignment=ft.MainAxisAlignment.CENTER)
    current_start_index = [0]

    # --- Lightbox ---
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
        if w < 600: num_visible = 3
        elif w < 1000: num_visible = 4
        else: num_visible = 6
        
        spacing = 10
        total_spacing = (num_visible - 1) * spacing
        available_width = w - 40 
        img_width = (available_width - total_spacing) / num_visible
        
        visible_images = []
        for i in range(num_visible):
            idx = (current_start_index[0] + i) % len(carousel_photos)
            src = carousel_photos[idx]
            img = ft.Image(src=src, height=160, width=img_width, fit=ft.ImageFit.COVER, border_radius=8, gapless_playback=True, animate_size=300)
            container = ft.Container(content=img, on_click=lambda e, s=src: open_lightbox_home(s), ink=True, border_radius=8)
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

    # --- YouTube ---
    clean_id = YOUTUBE_CHANNEL_ID.strip().replace('"', '').replace("'", "") if YOUTUBE_CHANNEL_ID else ""
    thumb_src = get_youtube_thumbnail(clean_id)
    if not thumb_src: thumb_src = "https://img.youtube.com/vi/AKw0E0t2k6c/maxresdefault.jpg"
    live_url = f"https://www.youtube.com/channel/{clean_id}/live" if clean_id else "https://www.youtube.com/"
    streams_url = f"https://www.youtube.com/channel/{clean_id}/streams" if clean_id else "https://www.youtube.com/"

    btn_live = ft.Container(content=ft.IconButton(ft.Icons.PLAY_CIRCLE_FILL, icon_color="red", icon_size=60, tooltip="Assistir Agora", on_click=lambda e: page.launch_url(live_url)), alignment=ft.alignment.center)
    btn_all_streams = ft.TextButton("Ver Cultos Anteriores", icon=ft.Icons.VIDEO_LIBRARY, on_click=lambda e: page.launch_url(streams_url), style=ft.ButtonStyle(color=THEME_COLOR))

    yt_card = ft.Card(content=ft.Container(content=ft.Column([
        ft.Row([ft.Icon(ft.Icons.LIVE_TV, color="red"), ft.Text("Transmissões da Igreja", size=16, weight="bold", color="red")]),
        ft.Stack([ft.Image(src=thumb_src, width=float("inf"), height=200, fit=ft.ImageFit.COVER, border_radius=8), ft.Container(bgcolor="black54", width=float("inf"), height=200, border_radius=8), btn_live, ft.Container(content=ft.Text("Clique para assistir ao vivo", color="white", size=12), bottom=10, right=10)], height=200),
        ft.Row([btn_all_streams], alignment=ft.MainAxisAlignment.END)
    ], spacing=10), padding=15), elevation=5)

    # --- Agenda ---
    agenda_col = ft.Column([], spacing=10)
    def refresh_agenda():
        events = db.get_upcoming_events()
        agenda_col.controls.clear()
        if not events: agenda_col.controls.append(ft.Text("Sem eventos próximos.", italic=True))
        for ev in events:
            d = datetime.strptime(ev['event_date'], "%Y-%m-%d")
            # --- PROTEÇÃO VISUAL: Se readonly, esconde botão de deletar ---
            delete_btn = ft.IconButton(ft.Icons.DELETE, icon_color="red", on_click=lambda e, x=ev['id']: (db.delete_event(x), refresh_agenda(), show_success(page, "Removido!")))
            
            card = ft.Card(content=ft.Container(content=ft.Row([
                ft.Container(content=ft.Column([ft.Text(str(d.day), size=24, weight="bold", color="white"), ft.Text(d.strftime("%b").upper(), size=12, color="white")], alignment="center", spacing=0), bgcolor=THEME_COLOR, width=60, height=60, border_radius=8, alignment=ft.alignment.center),
                ft.Column([ft.Text(ev['title'], weight="bold"), ft.Text(f"{ev['event_time']} - {ev['location']}", size=12, color="grey"), ft.Text(ev['description'], size=12, italic=True)], expand=True),
                delete_btn if not readonly else ft.Container() # Oculta botão se readonly
            ]), padding=10))
            agenda_col.controls.append(card)
        page.update()

    def add_ev_dialog(e):
        t, d, dt, tm, l = ft.TextField(label="Título"), ft.TextField(label="Desc"), ft.TextField(label="Data AAAA-MM-DD", value=datetime.now().strftime("%Y-%m-%d")), ft.TextField(label="Hora", value="19:30"), ft.TextField(label="Local", value="Igreja")
        def save(e):
            if db.add_event(t.value, d.value, dt.value, tm.value, l.value): page.close(dlg); refresh_agenda(); show_success(page, "Adicionado!")
            else: show_error(page, "Erro.")
        dlg = ft.AlertDialog(title=ft.Text("Novo Evento"), content=ft.Column([t, d, dt, tm, l], height=300), actions=[ft.TextButton("Cancelar", on_click=lambda e: page.close(dlg)), ft.TextButton("Salvar", on_click=save)])
        page.open(dlg)

    refresh_agenda()
    
    # --- Cabeçalho Agenda ---
    # Se readonly, esconde o botão de adicionar (+)
    agenda_header = ft.Row([ft.Text("Agenda", size=20, weight="bold"), ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color=THEME_COLOR, on_click=add_ev_dialog) if not readonly else ft.Container()], alignment="spaceBetween")

    return ft.ListView([
        ft.Text(APP_TITLE, size=24, weight="bold", color=THEME_COLOR),
        ft.Container(content=carousel_row, height=160), 
        ft.Divider(),
        yt_card, ft.Divider(),
        agenda_header,
        agenda_col
    ], padding=10, spacing=20)

def visitors_view(page, db, readonly=False, on_back_callback=None):
    if readonly: return ft.Center(ft.Text("Restrito"))
    n = ft.TextField(label="Nome Completo *", prefix_icon=ft.Icons.PERSON, col=12)
    p = ft.TextField(label="WhatsApp / Telefone", prefix_icon=ft.Icons.PHONE, keyboard_type="phone", col={"sm":12,"md":6})
    em = ft.TextField(label="E-mail", prefix_icon=ft.Icons.EMAIL, col={"sm":12,"md":6})
    obs = ft.TextField(label="Observações", multiline=True, min_lines=3, col=12)
    addr = address_form_fields(page)
    def save(e):
        if not n.value: show_warning(page, "Nome obrigatório!"); return
        loading = show_loading(page, "Salvando...")
        time.sleep(0.3)
        if db.add_visitor(n.value, p.value, em.value, addr["get_full_address"](), obs.value):
            hide_loading(page, loading); show_success(page, "Salvo!"); 
            if on_back_callback: on_back_callback()
            else: n.value=""; p.value=""; em.value=""; obs.value=""; addr["cep"].value=""; addr["logradouro"].value=""; page.update()
        else: hide_loading(page, loading); show_error(page, "Erro.")
    header = ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: on_back_callback()) if on_back_callback else ft.Container(), ft.Text("Novo Visitante", size=20, weight="bold")])
    return ft.Container(content=ft.Column([header, ft.Divider(), ft.ResponsiveRow([n, p, em], spacing=20), ft.Text("Endereço", weight="bold"), addr["ui"], ft.Divider(), ft.ResponsiveRow([obs]), ft.Container(ft.Button("Salvar Visitante", icon=ft.Icons.SAVE, on_click=save, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"), height=50, width=200), alignment=ft.alignment.center, padding=20)], scroll="auto", spacing=10), padding=20, expand=True)

def visitor_edit_view(page, db, vid, back_cb):
    v = db.get_visitor_by_id(vid)
    if not v: show_error(page, "Não achado"); back_cb(); return ft.Container()
    parts = v[4].split(" CEP: ") if v[4] else ["",""]; main = parts[0].split(" - ") if parts[0] else ["",""]; l_n = main[0].split(", ") if main[0] else ["",""]; b_c = main[1].split(", ") if len(main)>1 else ["",""]; c_u = b_c[1].split("/") if len(b_c)>1 else ["",""]
    n, p, em, obs = ft.TextField(label="Nome", value=v[1], col=12), ft.TextField(label="Zap", value=v[2], col=6), ft.TextField(label="Email", value=v[3], col=6), ft.TextField(label="Obs", value=v[6], multiline=True, col=12)
    cep, log, num = ft.TextField(label="CEP", value=parts[1] if len(parts)>1 else "", col=4), ft.TextField(label="Rua", value=l_n[0], col=8), ft.TextField(label="Nº", value=l_n[1] if len(l_n)>1 else "", col=4)
    bai, cid, uf = ft.TextField(label="Bairro", value=b_c[0], col=4), ft.TextField(label="Cidade", value=c_u[0], col=6), ft.TextField(label="UF", value=c_u[1] if len(c_u)>1 else "", col=2)
    def save(e):
        addr_full = f"{log.value}, {num.value} - {bai.value}, {cid.value}/{uf.value} CEP: {cep.value}"
        if db.update_visitor(vid, n.value, p.value, em.value, addr_full, obs.value): show_success(page, "Atualizado!"); back_cb()
        else: show_error(page, "Erro")
    return ft.ListView([ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: back_cb()), ft.Text("Editar", size=20, weight="bold")]), ft.ResponsiveRow([n,p,em]), ft.ResponsiveRow([cep,log,num,bai,cid,uf]), ft.ResponsiveRow([obs]), ft.Button("Salvar", on_click=save)], padding=10)

def visitors_list_view(page, db, readonly=False, on_edit_visitor=None, on_add_visitor=None):
    if readonly: return ft.Center(ft.Text("Restrito"))
    col = ft.Column([], scroll="auto", expand=True)
    def delete_v(vid, name):
        def conf(e):
            if db.delete_visitor(vid): page.close(dlg); show_success(page, "Deletado!"); refresh()
        dlg = ft.AlertDialog(title=ft.Text("Excluir?"), content=ft.Text(f"Apagar {name}?"), actions=[ft.TextButton("Não", on_click=lambda e: page.close(dlg)), ft.TextButton("Sim", on_click=conf)])
        page.open(dlg)
    def refresh(e=None):
        items = db.get_all_visitors()
        col.controls = []
        if not items: col.controls.append(ft.Text("Nenhum visitante", italic=True))
        for v in items:
            btns = []
            if v[2]: btns.append(ft.IconButton(ft.Icons.MESSAGE, icon_color="green", url=open_whatsapp(v[2], v[1])))
            if on_edit_visitor: btns.append(ft.IconButton(ft.Icons.EDIT, icon_color=THEME_COLOR, on_click=lambda e, x=v[0]: on_edit_visitor(x)))
            if not readonly: btns.append(ft.IconButton(ft.Icons.DELETE, icon_color="red", on_click=lambda e, x=v[0], n=v[1]: delete_v(x, n)))
            col.controls.append(ft.Card(ft.Container(ft.Row([ft.Icon(ft.Icons.PERSON, color=THEME_COLOR), ft.Column([ft.Text(v[1], weight="bold"), ft.Text(v[5], size=12, color="grey")], expand=True), ft.Row(btns)], alignment="spaceBetween"), padding=10)))
        page.update()
    refresh()
    header = [ft.Text("Visitantes", size=20, weight="bold")]
    if on_add_visitor: header.append(ft.IconButton(ft.Icons.ADD, bgcolor=THEME_COLOR, icon_color="white", on_click=lambda e: on_add_visitor()))
    return ft.Container(ft.Column([ft.Row(header, alignment="spaceBetween"), ft.Divider(), col], expand=True), padding=10, expand=True)

def cells_view(page, db, readonly=False):
    view = ft.Ref[ft.Column]()
    
    # --- FILTRO (Só aparece se NÃO for ReadOnly) ---
    filter_dd = ft.Dropdown(
        width=130, label="Exibir", value="Todas", text_size=14, content_padding=10,
        options=[ft.dropdown.Option("Todas"), ft.dropdown.Option("Ativas"), ft.dropdown.Option("Inativas")],
        on_change=lambda e: show_list(),
        visible=not readonly # Se for readonly, esconde o filtro
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
        
        # Lógica de Filtro
        if readonly:
            # Se for ReadOnly (Usuário Comum), FORÇA exibir apenas ativos e ignora o dropdown
            current_filter = "Ativas"
        else:
            current_filter = filter_dd.value

        filtered_items = []
        for c in items:
            c_active = c[8]
            
            if current_filter == "Todas": filtered_items.append(c)
            elif current_filter == "Ativas" and c_active: filtered_items.append(c)
            elif current_filter == "Inativas" and not c_active: filtered_items.append(c)
        
        if not filtered_items:
            content = ft.Text("Nenhum registro.", color="grey")
        else:
            cell_cards = []
            for c in filtered_items:
                c_id, c_name, c_leader, c_host, c_address, c_day, c_time, c_obs, c_active = c
                
                card_bg = THEME_COLOR if c_active else ft.colors.GREY_700
                status_icon = ft.Icons.HOME_FILLED if c_active else ft.Icons.HOME_WORK_OUTLINED
                opacity = 1.0 if c_active else 0.8
                
                # --- BOTÕES DE AÇÃO (Escondidos se ReadOnly) ---
                admin_actions = ft.Container()
                if not readonly:
                    if c_active:
                        admin_actions = ft.IconButton(ft.Icons.DELETE, icon_color="red", tooltip="Desativar", on_click=lambda e, x=c_id: (db.deactivate_cell(x), show_list()))
                    else:
                        admin_actions = ft.Row([
                            ft.IconButton(ft.Icons.RESTORE, icon_color="green", tooltip="Reativar", on_click=lambda e, x=c_id: (db.activate_cell(x), show_list())),
                            ft.IconButton(ft.Icons.DELETE_FOREVER, icon_color="red", tooltip="Excluir", on_click=lambda e, x=c_id, n=c_name: confirm_hard_delete(x, n))
                        ], spacing=0)
                
                card = ft.Card(content=ft.Container(content=ft.Column([
                    ft.Container(content=ft.Column([ft.Icon(status_icon, size=40, color="white"), ft.Text(c_day.upper(), weight="bold", color="white", size=12), ft.Text(c_time, weight="bold", color="white", size=20), ft.Text("INATIVA" if not c_active else "", color="white", size=10, weight="bold")], horizontal_alignment="center", spacing=2), bgcolor=card_bg, height=130, alignment=ft.alignment.center, border_radius=ft.border_radius.only(top_left=10, top_right=10), clip_behavior=ft.ClipBehavior.HARD_EDGE),
                    ft.Container(content=ft.Column([
                        ft.Text(c_name, weight="bold", size=18, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS), ft.Divider(height=10, color="transparent"),
                        ft.Row([ft.Icon(ft.Icons.PERSON, size=16, color="grey"), ft.Text(f"Líder: {c_leader}", size=13, color="grey", expand=True)]),
                        ft.Row([ft.Icon(ft.Icons.REAL_ESTATE_AGENT, size=16, color="grey"), ft.Text(f"Anfitrião: {c_host}", size=13, color="grey", expand=True)]),
                        ft.Row([ft.Icon(ft.Icons.LOCATION_ON, size=16, color="red"), ft.Text(c_address if c_address else "Sem endereço", size=12, color="grey", expand=True, no_wrap=True)]) if c_address else ft.Container(),
                        ft.Divider(),
                        ft.Row([
                            ft.ElevatedButton("Abrir Mapa", icon=ft.Icons.MAP, icon_color="white", bgcolor="green", color="white", style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)), on_click=lambda e, addr=c_address: open_google_maps(addr), visible=bool(c_address)),
                            admin_actions # Botões de admin aqui
                        ], alignment="spaceBetween")
                    ], spacing=5), padding=15)
                ], spacing=0), opacity=opacity), col={"sm": 12, "md": 6, "lg": 4, "xl": 3}, elevation=4)
                cell_cards.append(card)
            content = ft.ResponsiveRow(cell_cards)
        
        # Cabeçalho Casas: Se readonly, esconde botão ADD e filtro Dropdown
        header_row = ft.Row([
            ft.Text("Casas de Cornélio", size=24, weight="bold", color=THEME_COLOR),
            ft.Row([filter_dd, ft.IconButton(ft.Icons.ADD, on_click=show_form, bgcolor=THEME_COLOR, icon_color="white") if not readonly else ft.Container()], spacing=5)
        ], alignment="spaceBetween")

        view.current.controls = [header_row, ft.Divider(), ft.Column([content], scroll="auto", expand=True)]
        page.update()

    def show_form(e):
        n,l,h,t,o = ft.TextField(label="Nome *", col=12), ft.TextField(label="Líder *", col={"sm":12,"md":6}), ft.TextField(label="Anfitrião", col={"sm":12,"md":6}), ft.TextField(label="Horário", col={"sm":12,"md":6}), ft.TextField(label="Obs", multiline=True, col=12)
        d = ft.Dropdown(label="Dia", options=[ft.dropdown.Option(x) for x in ["Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira","Sexta-feira","Sábado","Domingo"]], col={"sm":12,"md":6})
        addr = address_form_fields(page)
        def save(e):
            if not n.value or not l.value: show_warning(page, "Preencha Nome e Líder!"); return
            if db.add_cell(n.value, l.value, h.value, addr["get_full_address"](), d.value, t.value, o.value): show_success(page, "Salvo!"); show_list()
            else: show_error(page, "Erro.")
        view.current.controls = [ft.Column([ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: show_list()), ft.Text("Nova Casa", size=20, weight="bold")]), ft.Divider(), ft.ResponsiveRow([n,l,h,d,t]), ft.Text("Endereço", weight="bold"), addr["ui"], ft.Divider(), ft.ResponsiveRow([o]), ft.Container(ft.Button("Salvar", on_click=save, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white")), padding=10)], scroll="auto", expand=True)]
        page.update()
    col = ft.Column(expand=True, ref=view); show_list(); return col

def users_view(page, db, readonly=False):
    if readonly: return ft.Center(ft.Text("Negado"))
    view = ft.Ref[ft.Column]()
    def show_list():
        items = db.get_all_users()
        lst = []
        for u in items:
            title = u[2] if u[2] else u[1]; sub = f"Login: {u[1]}" + (f" • {u[3]}" if u[3] else "")
            acts = [ft.IconButton(ft.Icons.EDIT, icon_color=THEME_COLOR, on_click=lambda e, x=u[0]: show_edit(x)), ft.IconButton(ft.Icons.DELETE, disabled=u[0]==1, on_click=lambda e,x=u[0]:(db.delete_user(x), show_list()))]
            lst.append(ft.ListTile(title=ft.Text(title, weight="bold"), subtitle=ft.Text(sub, size=12), leading=ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS if u[4] else ft.Icons.PERSON), trailing=ft.Row(acts, alignment=ft.MainAxisAlignment.END, spacing=0, width=100)))
        view.current.controls = [ft.Row([ft.Text("Usuários", size=20), ft.IconButton(ft.Icons.ADD, on_click=show_form)], alignment="spaceBetween"), ft.Column(lst, scroll="auto", expand=True)]; page.update()
    
    def show_form(e):
        fn, em, ph, u, p = ft.TextField(label="Nome *", col=12), ft.TextField(label="Email", col=6), ft.TextField(label="Tel", col=6), ft.TextField(label="Login *", col=6), ft.TextField(label="Senha *", password=True, col=6)
        adm, v, c, g = ft.Checkbox(label="Admin", col=12), ft.Checkbox(label="Visitantes", col=12), ft.Checkbox(label="Casas", col=12), ft.Checkbox(label="Galeria", col=12)
        def save(e):
            if db.add_user(u.value, p.value, adm.value, {"visitantes":v.value,"celulas":c.value,"galeria":g.value}, fn.value, em.value, ph.value): show_list(); show_success(page, "Criado!")
            else: show_error(page, "Erro.")
        view.current.controls = [ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: show_list()), ft.Text("Novo")]), ft.Column([ft.ResponsiveRow([fn,em,ph,u,p,adm]), ft.Divider(), ft.Text("Permissões:"), ft.ResponsiveRow([v,c,g]), ft.Button("Criar", on_click=save, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"))], scroll="auto")]; page.update()

    def show_edit(uid):
        ud = db.get_user_by_id(uid)
        if not ud: return
        fn, em, ph, u, p = ft.TextField(label="Nome", value=ud['full_name'], col=12), ft.TextField(label="Email", value=ud['email'], col=6), ft.TextField(label="Tel", value=ud['phone'], col=6), ft.TextField(label="Login", value=ud['username'], col=6), ft.TextField(label="Senha (vazio=manter)", password=True, col=6)
        adm = ft.Checkbox(label="Admin", value=ud['is_admin'], col=12)
        perms = ud['permissions'] if isinstance(ud['permissions'], dict) else json.loads(ud['permissions'] or '{}')
        v, c, g = ft.Checkbox(label="Visitantes", value=perms.get('visitantes'), col=12), ft.Checkbox(label="Casas", value=perms.get('celulas'), col=12), ft.Checkbox(label="Galeria", value=perms.get('galeria'), col=12)
        def upd(e):
            if db.update_user(uid, u.value, p.value, adm.value, {"visitantes":v.value,"celulas":c.value,"galeria":g.value}, fn.value, em.value, ph.value): show_list(); show_success(page, "Atualizado!")
            else: show_error(page, "Erro.")
        view.current.controls = [ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: show_list()), ft.Text("Editar")]), ft.Column([ft.ResponsiveRow([fn,em,ph,u,p,adm]), ft.Divider(), ft.Text("Permissões:"), ft.ResponsiveRow([v,c,g]), ft.Button("Salvar", on_click=upd, style=ft.ButtonStyle(bgcolor=THEME_COLOR, color="white"))], scroll="auto")]; page.update()

    col = ft.Column(expand=True, ref=view); show_list(); return col

# ==============================================================================
# MAIN
# ==============================================================================

def main(page: ft.Page):
    page.title = APP_TITLE
    page.theme = ft.Theme(color_scheme_seed=THEME_COLOR)
    page.padding = 0
    db = Database()
    user_state = {"user": None, "perms": {}, "readonly": False}

    def logout(e=None):
        user_state["user"] = None
        page.clean()
        page.add(login_view(page, db, on_login_success))
        page.update()

    def on_login_success(username):
        user_state["user"] = username
        # AQUI BUSCA AS PERMISSÕES DO BANCO (incluindo o readonly calculado)
        perms = db.get_user_permissions(username)
        user_state["perms"] = perms
        user_state["readonly"] = perms.get("readonly", True) # Padrão True (Bloqueado) se falhar
        dashboard()

    def dashboard():
        page.clean()
        content = ft.Container(expand=True, padding=10)
        
        # Passa o 'readonly' para a Gallery View
        menu_data = [
            ("home", ft.Icons.HOME, "Início", home_view),
            ("lista_visitantes", ft.Icons.PEOPLE, "Visitantes", visitors_list_view),
            ("celulas", ft.Icons.GROUPS, "Casas de Cornélio", cells_view),
            ("galeria", ft.Icons.PHOTO_LIBRARY, "Galeria", lambda p, d, ro: gallery_view(p, d, user_state, show_success, show_error, show_warning, show_loading, hide_loading, ro)),
            ("usuarios", ft.Icons.SECURITY, "Usuários", users_view)
        ]
        
        destinations, pages = [], []
        perms = user_state["perms"]
        
        for k, icon, label, func in menu_data:
            if k == "home" or perms.get(k) or (k == "lista_visitantes" and perms.get("visitantes")):
                destinations.append(ft.NavigationRailDestination(icon=icon, label=label))
                pages.append(func)
        
        destinations.append(ft.NavigationRailDestination(icon=ft.Icons.LOGOUT, label="Sair"))

        rail = ft.NavigationRail(selected_index=0, label_type=ft.NavigationRailLabelType.ALL, min_width=100, min_extended_width=200, leading=ft.Container(get_logo(50), padding=10), destinations=destinations, on_change=lambda e: nav(e.control.selected_index))
        drawer = ft.NavigationDrawer(controls=[ft.Container(height=20), ft.Column([get_logo(60), ft.Text("IEQ Gestão")], horizontal_alignment="center"), ft.Divider()] + [ft.NavigationDrawerDestination(icon=d.icon, label=d.label) for d in destinations], on_change=lambda e: nav(e.control.selected_index))
        page.drawer = drawer
        appbar = ft.AppBar(leading=ft.IconButton(ft.Icons.MENU, on_click=lambda e: page.open(drawer)), title=ft.Text(APP_TITLE), bgcolor=THEME_COLOR, color="white", visible=False)

        def nav(idx):
            if idx == len(destinations)-1: logout(); return
            rail.selected_index = idx; drawer.selected_index = idx
            func = pages[idx]
            # Passa user_state["readonly"] para todas as views
            if func == visitors_list_view:
                content.content = func(page, db, user_state["readonly"], on_edit_visitor=lambda vid: (content.__setattr__("content", visitor_edit_view(page, db, vid, lambda: nav(idx))), page.update()), on_add_visitor=lambda: (content.__setattr__("content", visitors_view(page, db, user_state["readonly"], lambda: nav(idx))), page.update()))
            else: content.content = func(page, db, user_state["readonly"])
            page.close(drawer); page.update()

        row = ft.Row([rail, ft.VerticalDivider(width=1), content], expand=True, spacing=0)
        page.add(appbar, row)

        def resize(e):
            is_mobile = page.width < 800
            rail.visible = not is_mobile; row.controls[1].visible = not is_mobile; appbar.visible = is_mobile; page.update()
        
        page.on_resized = resize; resize(None); nav(0)

    page.add(login_view(page, db, on_login_success))

if __name__ == "__main__":
    ft.app(main, assets_dir="assets")