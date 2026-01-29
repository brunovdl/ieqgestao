"""
Aplicativo de Gestão IEQ
Sistema modular para gerenciamento de igreja
"""
import flet as ft
from database import Database
from views import login_view, dashboard_view
from utils import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    APP_TITLE,
    DB_NAME,
    ROUTE_LOGIN,
    ROUTE_DASHBOARD
)


def main(page: ft.Page):
    """Função principal do aplicativo"""
    
    # Configurações da página
    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.width = WINDOW_WIDTH
    page.window.height = WINDOW_HEIGHT
    
    # Inicializar banco de dados
    db = Database(DB_NAME)
    
    # Callbacks de navegação
    def go_to_dashboard():
        """Navega para o dashboard"""
        page.run_task(page.push_route, ROUTE_DASHBOARD)
    
    def go_to_login():
        """Navega para o login"""
        page.run_task(page.push_route, ROUTE_LOGIN)
    
    # Gerenciamento de rotas
    def route_change(route):
        """Handler para mudanças de rota"""
        page.views.clear()
        
        if page.route == ROUTE_LOGIN:
            page.views.append(login_view(page, db, go_to_dashboard))
        elif page.route == ROUTE_DASHBOARD:
            page.views.append(dashboard_view(page, db, go_to_login))
        
        page.update()
    
    def view_pop(view):
        """Handler para voltar de uma view"""
        page.views.pop()
        top_view = page.views[-1]
        page.run_task(page.push_route, top_view.route)
    
    # Configurar handlers
    page.on_route_change = route_change
    page.on_view_pop = view_pop
    
    # Iniciar na tela de login
    page.run_task(page.push_route, ROUTE_LOGIN)


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
