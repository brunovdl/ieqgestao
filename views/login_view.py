import flet as ft
from core.config import Config
from utils.helpers import show_loading, hide_loading, show_error, show_warning, get_logo

def login_view(page, db, on_success):
    user = ft.TextField(label="Usuário", col=12)
    pwd = ft.TextField(label="Senha", password=True, can_reveal_password=True, col=12)
    
    def try_login(e):
        if not user.value or not pwd.value:
            show_warning(page, "Preencha tudo!")
            return
            
        loading = show_loading(page, "Entrando...")
        # Simula tempo para loading
        import time; time.sleep(0.5)
        
        if db.check_login(user.value, pwd.value):
            hide_loading(page, loading)
            on_success(user.value)
        else:
            hide_loading(page, loading)
            show_error(page, "Dados inválidos.")

    user.on_submit = try_login
    pwd.on_submit = try_login

    login_card = ft.Container(
        content=ft.Column([
            ft.Text("Login", size=20, weight="bold", color=Config.THEME_COLOR),
            ft.ResponsiveRow([user, pwd]),
            ft.Button("Entrar", on_click=try_login, width=300, style=ft.ButtonStyle(bgcolor=Config.THEME_COLOR, color="white"))
        ], horizontal_alignment="center", spacing=20),
        padding=20, width=400, border=ft.border.all(1, "grey"), border_radius=10, bgcolor=ft.colors.SURFACE_VARIANT
    )

    return ft.Container(
        content=ft.Column([
            get_logo(100),
            ft.Text(Config.APP_TITLE, size=18, weight="bold", color="grey"),
            login_card
        ], horizontal_alignment="center", alignment=ft.alignment.center, spacing=20, scroll="auto"), 
        padding=10, alignment=ft.alignment.center, expand=True
    )