import flet as ft
import threading
import time
from datetime import datetime
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
    
    # Controle da Thread de Notificação (Sininho)
    notification_flag = [False] 

    def logout():
        notification_flag[0] = False 
        user_state.update({"user": None, "full_name": None, "perms": {}, "readonly": False})
        page.drawer = None
        page.clean()
        page.add(login_view(page, db, on_login_success))
        page.update()

    def on_login_success(username_val):
        # Busca permissões e nome completo
        user_data = db.get_user_permissions(username_val)
        
        # Tenta buscar o nome completo no banco, se não tiver usa o user
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
        
        # Ativa a thread de notificação
        notification_flag[0] = True
        
        # --- 1. LÓGICA DE SAUDAÇÃO ---
        now = datetime.now()
        hour = now.hour
        
        # Pega o primeiro nome
        raw_name = user_state.get('full_name', 'Visitante') or "Visitante"
        first_name = raw_name.split()[0].capitalize()

        # Define texto e ícone (SEM QUEBRA DE LINHA \n)
        if 5 <= hour < 12:
            greeting_msg = f"Bom dia, {first_name}"
            icon, color = ft.Icons.WB_SUNNY, "orange"
        elif 12 <= hour < 18:
            greeting_msg = f"Boa tarde, {first_name}"
            icon, color = ft.Icons.WB_SUNNY_OUTLINED, "orange"
        else:
            greeting_msg = f"Boa noite, {first_name}"
            icon, color = ft.Icons.NIGHTLIGHT_ROUND, "blue"

        # --- HEADER DO MENU (CORRIGIDO PARA LINHA ÚNICA) ---
        drawer_header = ft.Container(
            content=ft.Column([
                get_logo(60), # Logo
                ft.Container(height=10), # Espaçamento
                
                # ALTERADO DE COLUMN PARA ROW (Para ficar na mesma linha)
                ft.Row([
                    ft.Icon(icon, color=color, size=20),
                    ft.Text(greeting_msg, weight="bold", size=13)
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=8)
                
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            
            bgcolor=ft.colors.SURFACE_VARIANT, 
            padding=20, 
            border_radius=12, 
            margin=10, 
            alignment=ft.alignment.center
        )
        
        # --- 2. BADGES DE NOTIFICAÇÃO (SININHO DA CARONA) ---
        
        # Refs para atualizar o número sem recarregar tudo
        badge_text_ref = ft.Ref[ft.Text]()
        badge_container_ref = ft.Ref[ft.Container]()      # Menu Lateral
        mobile_badge_text_ref = ft.Ref[ft.Text]()
        mobile_badge_container_ref = ft.Ref[ft.Container]() # Header Mobile

        # Ícone Especial para o Menu Lateral (Com Badge)
        carpool_icon_menu = ft.Container(
            content=ft.Stack([
                ft.Icon(ft.Icons.DIRECTIONS_CAR),
                ft.Container(
                    ref=badge_container_ref,
                    content=ft.Text(ref=badge_text_ref, value="0", size=10, color="white", weight="bold"),
                    bgcolor="red", border_radius=10, width=16, height=16, alignment=ft.alignment.center,
                    top=0, right=0, visible=False 
                )
            ], width=24, height=24)
        )

        # Definição das Rotas
        all_routes = [
            ("home", ft.Icons.HOME, "Início", home_view),
            ("lista_visitantes", ft.Icons.PEOPLE, "Visitantes", visitors_list_view),
            ("celulas", ft.Icons.GROUPS, "Casas de Cornélio", cells_view),
            ("carona", carpool_icon_menu, "Carona Solidária", carpool_view), 
            ("galeria", ft.Icons.PHOTO_LIBRARY, "Galeria", gallery_view),
            ("usuarios", ft.Icons.SECURITY, "Gestão de Usuários", users_view)
        ]
        
        active_routes = []
        perms = user_state["perms"]
        carpool_route_index = -1
        
        # Filtra rotas permitidas
        for i, (key, icon_or_badge, label, func) in enumerate(all_routes):
            if key in ["home", "carona"] or perms.get(key) or (key == "lista_visitantes" and perms.get("visitantes")):
                active_routes.append((key, icon_or_badge, label, func))
                if key == "carona":
                    carpool_route_index = len(active_routes) - 1

        # --- 3. THREAD DE ATUALIZAÇÃO DOS BADGES ---
        def update_badge_loop():
            while notification_flag[0]:
                try:
                    count = db.get_upcoming_rides_count()
                    val_str = str(count) if count < 99 else "99+"
                    is_visible = (count > 0)

                    # Atualiza Menu Lateral
                    if badge_text_ref.current:
                        badge_text_ref.current.value = val_str
                        badge_container_ref.current.visible = is_visible
                    
                    # Atualiza Header Mobile
                    if mobile_badge_text_ref.current:
                        mobile_badge_text_ref.current.value = val_str
                        mobile_badge_container_ref.current.visible = is_visible
                        
                    page.update()
                except: pass
                time.sleep(10) # Verifica a cada 10s

        threading.Thread(target=update_badge_loop, daemon=True).start()

        # Navegação (Monta Destinos)
        destinations = []
        for r in active_routes:
            if isinstance(r[1], ft.Container):
                destinations.append(ft.NavigationRailDestination(icon_content=r[1], label=r[2]))
            else:
                destinations.append(ft.NavigationRailDestination(icon=r[1], label=r[2]))
        
        destinations.append(ft.NavigationRailDestination(icon=ft.Icons.LOGOUT, label="Sair"))

        # Função de Navegação
        def nav(idx):
            if idx == len(active_routes): logout(); return
            rail.selected_index = idx; drawer.selected_index = idx
            
            key, _, label, func = active_routes[idx]
            header_title.value = label # Atualiza título Mobile
            
            # Injeta user_state se necessário
            if func in [visitors_list_view, gallery_view, users_view, carpool_view]:
                content.content = func(page, db, user_state, user_state["readonly"])
            else:
                content.content = func(page, db, user_state["readonly"])
            
            page.close(drawer); page.update()

        # Componentes de Navegação
        rail = ft.NavigationRail(
            selected_index=0, 
            label_type=ft.NavigationRailLabelType.ALL, 
            min_width=130, 
            leading=drawer_header, # Usa o Card com Saudação
            destinations=destinations, 
            on_change=lambda e: nav(e.control.selected_index)
        )
        
        drawer = ft.NavigationDrawer(
            controls=[
                ft.Container(drawer_header, padding=10), 
                ft.Divider(thickness=1, color="grey"), 
                ft.Container(height=10)
            ] + [ft.NavigationDrawerDestination(icon_content=d.icon_content, icon=d.icon, label=d.label) for d in destinations], 
            on_change=lambda e: nav(e.control.selected_index)
        )
        page.drawer = drawer

        # --- 4. HEADER MOBILE (COM ÍCONE DE NOTIFICAÇÃO) ---
        header_title = ft.Text(active_routes[0][2], size=20, weight="bold", color="white")
        
        # Ações do lado direito (Sininho Carona)
        mobile_actions = []
        if carpool_route_index != -1:
            mobile_actions.append(
                ft.Container(
                    content=ft.Stack([
                        ft.IconButton(
                            ft.Icons.DIRECTIONS_CAR, 
                            icon_color="white", 
                            on_click=lambda e: nav(carpool_route_index)
                        ),
                        ft.Container(
                            ref=mobile_badge_container_ref,
                            content=ft.Text(ref=mobile_badge_text_ref, value="0", size=10, color="white", weight="bold"),
                            bgcolor="red", border_radius=10, width=16, height=16, alignment=ft.alignment.center,
                            top=5, right=5, visible=False
                        )
                    ]),
                    padding=0
                )
            )

        header = ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.IconButton(ft.Icons.MENU, icon_color="white", on_click=lambda e: page.open(drawer)), 
                    header_title
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                
                ft.Row(mobile_actions, vertical_alignment=ft.CrossAxisAlignment.CENTER)
                
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            
            bgcolor=Config.THEME_COLOR, 
            padding=ft.padding.symmetric(horizontal=10, vertical=5), 
            shadow=ft.BoxShadow(blur_radius=5)
        )

        # Montagem Layout
        row = ft.Row([rail, ft.VerticalDivider(width=1), content], expand=True, spacing=0)
        page.add(ft.SafeArea(ft.Column([header, ft.Container(row, expand=True)], spacing=0, expand=True), expand=True))

        def resize(e):
            is_mobile = page.width < 800
            rail.visible = not is_mobile; row.controls[1].visible = not is_mobile; header.visible = is_mobile; page.update()
        
        page.on_resized = resize; resize(None); nav(0)

    page.add(login_view(page, db, on_login_success))

if __name__ == "__main__":
    import os
    os.makedirs("temp_uploads", exist_ok=True)
    ft.app(target=main, assets_dir="assets", upload_dir="temp_uploads", view=ft.WEB_BROWSER)