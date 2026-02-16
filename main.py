import flet as ft
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from core.config import Config
from core.database import Database
from utils.helpers import get_logo

# Importação das Views Modulares
from views.login_view import login_view
from views.home_view import home_view
from views.visitors_view import visitors_list_view
from views.cells_view import cells_view
from views.gallery_view import gallery_view
from views.users_view import users_view
from views.carpool_view import carpool_view

def main(page: ft.Page):
    page.title = Config.APP_TITLE
    page.theme = ft.Theme(color_scheme_seed=Config.THEME_COLOR)
    page.padding = 0
    
    db = Database()
    user_state = {"user": None, "full_name": None, "perms": {}, "readonly": False}
    notification_flag = [False] 

    def logout():
        """Volta ao modo público (não à tela de login)."""
        notification_flag[0] = False 
        user_state.update({"user": None, "full_name": None, "perms": {}, "readonly": False})
        page.drawer = None
        dashboard()

    def on_login_success(username_val):
        user_data = db.get_user_permissions(username_val)
        full_user_obj = db.supabase.table('users').select('full_name').eq('username', username_val).execute()
        real_name = username_val
        if full_user_obj.data:
            real_name = full_user_obj.data[0].get('full_name', username_val)

        user_state["user"] = username_val
        user_state["full_name"] = real_name
        user_state["perms"] = user_data
        user_state["readonly"] = user_data.get("readonly", True)
        dashboard()

    def dashboard():
        page.clean()
        page.overlay.clear()
        content = ft.Container(expand=True, padding=10)
        
        notification_flag[0] = True
        is_logged_in = user_state["user"] is not None
        
        # --- REFERÊNCIA DO VÍDEO ---
        video_ref = ft.Ref[ft.WebView]()

        # --- CONTROLE DE VISIBILIDADE DO VÍDEO (CORREÇÃO DE ERRO) ---
        def toggle_video(show):
            try:
                if video_ref.current:
                    video_ref.current.visible = show
                    video_ref.current.update()
            except Exception:
                pass

        def show_login_dialog(e=None):
            """Abre o login como um dialog compacto, escondendo o vídeo."""
            toggle_video(False)
            
            user_field = ft.TextField(label="Usuário", dense=True)
            pwd_field = ft.TextField(label="Senha", password=True, can_reveal_password=True, dense=True)
            
            def try_login(e):
                from utils.helpers import show_error, show_warning
                if not user_field.value or not pwd_field.value:
                    show_warning(page, "Preencha tudo!")
                    return
                if db.check_login(user_field.value, pwd_field.value):
                    page.close(login_dlg)
                    on_login_success(user_field.value)
                else:
                    show_error(page, "Dados inválidos.")
            
            user_field.on_submit = try_login
            pwd_field.on_submit = try_login
            
            login_dlg = ft.AlertDialog(
                title=ft.Row([
                    get_logo(30),
                    ft.Text("Entrar", size=18, weight="bold", color=Config.THEME_COLOR)
                ], spacing=8),
                content=ft.Container(
                    width=280,
                    content=ft.Column([user_field, pwd_field], spacing=10, tight=True)
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: (page.close(login_dlg), toggle_video(True))),
                    ft.ElevatedButton("Entrar", on_click=try_login, bgcolor=Config.THEME_COLOR, color="white")
                ],
                on_dismiss=lambda e: toggle_video(True)
            )
            page.open(login_dlg)

        # --- SAUDAÇÃO (Horário do Brasil) ---
        BR_TZ = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(BR_TZ)
        hour = now.hour
        raw_name = user_state.get('full_name', 'Visitante') or "Visitante"
        first_name = raw_name.split()[0].capitalize()

        if 6 <= hour < 12: greeting_msg = f"Bom dia, {first_name}"; icon, color = ft.Icons.WB_SUNNY, "orange"
        elif 12 <= hour < 18: greeting_msg = f"Boa tarde, {first_name}"; icon, color = ft.Icons.WB_SUNNY_OUTLINED, "orange"
        else: greeting_msg = f"Boa noite, {first_name}"; icon, color = ft.Icons.NIGHTLIGHT_ROUND, "blue"

        drawer_header = ft.Container(
            content=ft.Column([
                get_logo(60),
                ft.Container(height=10),
                ft.Row([ft.Icon(icon, color=color, size=20), ft.Text(greeting_msg, weight="bold", size=13)], alignment="center", spacing=8)
            ], horizontal_alignment="center", spacing=0),
            bgcolor=ft.colors.SURFACE_VARIANT, padding=20, border_radius=12, margin=10, alignment=ft.alignment.center
        )
        
        # --- BADGES ---
        badge_text_ref = ft.Ref[ft.Text]()
        badge_container_ref = ft.Ref[ft.Container]()
        mobile_badge_text_ref = ft.Ref[ft.Text]()
        mobile_badge_container_ref = ft.Ref[ft.Container]()

        carpool_icon_menu = ft.Container(content=ft.Stack([ft.Icon(ft.Icons.DIRECTIONS_CAR), ft.Container(ref=badge_container_ref, content=ft.Text(ref=badge_text_ref, value="0", size=10, color="white", weight="bold"), bgcolor="red", border_radius=10, width=16, height=16, alignment=ft.alignment.center, top=0, right=0, visible=False)]), width=24, height=24)

        # --- ROTAS PÚBLICAS (sem login) ---
        public_routes = [
            ("home", ft.Icons.HOME, "Início", home_view),
            ("celulas", ft.Icons.GROUPS, "Casas de Cornélio", cells_view),
            ("galeria", ft.Icons.PHOTO_LIBRARY, "Galeria", gallery_view),
        ]

        # --- ROTAS PROTEGIDAS (com login) ---
        all_protected_routes = [
            ("lista_visitantes", ft.Icons.PEOPLE, "Visitantes", visitors_list_view),
            ("carona", carpool_icon_menu, "Carona Solidária", carpool_view), 
            ("usuarios", ft.Icons.SECURITY, "Gestão de Usuários", users_view)
        ]
        
        active_routes = list(public_routes)
        carpool_route_index = -1
        
        if is_logged_in:
            perms = user_state["perms"]
            # Adiciona carona (todos logados têm acesso)
            active_routes.append(("carona", carpool_icon_menu, "Carona Solidária", carpool_view))
            carpool_route_index = len(active_routes) - 1
            
            for key, icon_or_badge, label, func in all_protected_routes:
                if key == "carona": continue  # Já adicionado
                if perms.get(key) or (key == "lista_visitantes" and perms.get("visitantes")):
                    active_routes.append((key, icon_or_badge, label, func))

        def update_badge_loop():
            while notification_flag[0]:
                try:
                    count = db.get_upcoming_rides_count()
                    val_str = str(count) if count < 99 else "99+"
                    is_visible = (count > 0)
                    if badge_text_ref.current:
                        badge_text_ref.current.value = val_str; badge_container_ref.current.visible = is_visible
                    if mobile_badge_text_ref.current:
                        mobile_badge_text_ref.current.value = val_str; mobile_badge_container_ref.current.visible = is_visible
                    page.update()
                except: pass
                time.sleep(10)

        if is_logged_in:
            threading.Thread(target=update_badge_loop, daemon=True).start()

        destinations = []
        for r in active_routes:
            # Em Flet 0.25+, 'icon' aceita Control ou string, substituindo 'icon_content'
            destinations.append(ft.NavigationRailDestination(icon=r[1], label=r[2]))
        
        # Botão de Sair ou Login no menu lateral
        if is_logged_in:
            destinations.append(ft.NavigationRailDestination(icon=ft.Icons.LOGOUT, label="Sair"))
        else:
            destinations.append(ft.NavigationRailDestination(icon=ft.Icons.LOGIN, label="Entrar"))

        # --- HISTÓRICO DE NAVEGAÇÃO ---
        nav_history = []
        current_nav_index = [0]
        is_programmatic_nav = [False]

        def nav(idx, from_back=False):
            # Último item = Sair/Login
            if idx == len(active_routes):
                if is_logged_in:
                    logout()
                else:
                    show_login_dialog()
                return
            
            if not from_back and current_nav_index[0] != idx:
                nav_history.append(current_nav_index[0])
            
            current_nav_index[0] = idx
            rail.selected_index = idx; drawer.selected_index = idx
            key, _, label, func = active_routes[idx]
            header_title.value = label
            
            # --- INJEÇÃO DE DEPENDÊNCIAS ---
            if func == home_view:
                content.content = func(page, db, True if not is_logged_in else user_state["readonly"], webview_ref=video_ref)
            elif func in [visitors_list_view, gallery_view, users_view, carpool_view]:
                content.content = func(page, db, user_state, True if not is_logged_in else user_state["readonly"])
            else:
                content.content = func(page, db, True if not is_logged_in else user_state["readonly"])
            
            page.close(drawer)
            toggle_video(True)
            
            if not from_back:
                is_programmatic_nav[0] = True
                page.route = f"/{key}"
                
            page.update()

        def on_route_change(e):
            if is_programmatic_nav[0]:
                is_programmatic_nav[0] = False
                return
            if nav_history:
                prev_idx = nav_history.pop()
                nav(prev_idx, from_back=True)

        page.on_route_change = on_route_change

        rail = ft.NavigationRail(selected_index=0, label_type=ft.NavigationRailLabelType.ALL, min_width=130, leading=drawer_header, destinations=destinations, on_change=lambda e: nav(e.control.selected_index))
        
        # --- DRAWER ---
        drawer = ft.NavigationDrawer(
            controls=[
                ft.Container(drawer_header, padding=10), 
                ft.Divider(thickness=1, color="grey"), 
                ft.Container(height=10)
            ] + [ft.NavigationDrawerDestination(icon=d.icon, label=d.label) for d in destinations], 
            
            on_change=lambda e: nav(e.control.selected_index),
            on_dismiss=lambda e: toggle_video(True)
        )
        page.drawer = drawer

        header_title = ft.Text(active_routes[0][2], size=20, weight="bold", color="white")
        mobile_actions = []
        
        # Badge da carona (apenas quando logado)
        if is_logged_in and carpool_route_index != -1:
            mobile_actions.append(ft.Container(content=ft.Stack([ft.IconButton(ft.Icons.DIRECTIONS_CAR, icon_color="white", on_click=lambda e: nav(carpool_route_index)), ft.Container(ref=mobile_badge_container_ref, content=ft.Text(ref=mobile_badge_text_ref, value="0", size=10, color="white", weight="bold"), bgcolor="red", border_radius=10, width=16, height=16, alignment=ft.alignment.center, top=5, right=5, visible=False)]), padding=0))
        
        # Botão de Login/Logout no header (mobile)
        if is_logged_in:
            mobile_actions.append(ft.IconButton(ft.Icons.LOGOUT, icon_color="white", tooltip="Sair", on_click=lambda e: logout()))
        else:
            mobile_actions.append(ft.IconButton(ft.Icons.LOGIN, icon_color="white", tooltip="Entrar", on_click=lambda e: show_login_dialog()))

        # --- BOTÃO MENU COM PROTEÇÃO ---
        btn_menu = ft.IconButton(
            ft.Icons.MENU, 
            icon_color="white", 
            on_click=lambda e: (toggle_video(False), page.open(drawer))
        )

        header = ft.Container(
            content=ft.Row([
                ft.Row([btn_menu, header_title], vertical_alignment="center"), 
                ft.Row(mobile_actions, vertical_alignment="center")
            ], alignment="spaceBetween"), 
            bgcolor=Config.THEME_COLOR, 
            padding=ft.padding.symmetric(horizontal=10, vertical=5), 
            shadow=ft.BoxShadow(blur_radius=5)
        )

        row = ft.Row([rail, ft.VerticalDivider(width=1), content], expand=True, spacing=0)
        page.add(ft.SafeArea(ft.Column([header, ft.Container(row, expand=True)], spacing=0, expand=True), expand=True))

        def resize(e):
            is_mobile = page.width < 800
            rail.visible = not is_mobile; row.controls[1].visible = not is_mobile; header.visible = is_mobile; page.update()
        
        page.on_resized = resize; resize(None); nav(0)

    # --- INICIA DIRETO NO DASHBOARD (modo público) ---
    dashboard()

if __name__ == "__main__":
    import os
    os.makedirs("temp_uploads", exist_ok=True)
    ft.app(target=main, assets_dir="assets", upload_dir="temp_uploads", view=ft.WEB_BROWSER)