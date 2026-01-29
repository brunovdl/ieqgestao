"""
View do Dashboard Principal
"""
import flet as ft
from .visitors_view import visitors_view
from .components import rounded_logo


def dashboard_view(page: ft.Page, db, on_logout):
    """
    Cria a view do dashboard principal
    
    Args:
        page: Página do Flet
        db: Instância do banco de dados
        on_logout: Callback para logout
        
    Returns:
        ft.View: View do dashboard
    """
    # Conteúdo inicial (visitantes)
    main_content = ft.Container(
        content=visitors_view(page, db),
        expand=True,
        padding=20
    )

    def change_tool(e):
        """Altera a ferramenta/seção do dashboard"""
        idx = e.control.selected_index
        
        if idx == 0:  # Visitantes
            main_content.content = visitors_view(page, db)
        elif idx == 1:  # Células (placeholder)
            main_content.content = ft.Column([
                ft.Text("Gestão de Células", size=20, weight="bold"),
                ft.Divider(),
                ft.Text("Em desenvolvimento...", size=16, color="grey")
            ])
        elif idx == 2:  # Sair
            on_logout()
        
        page.update()

    # Sidebar com logo e menu
    sidebar = ft.Container(
        content=ft.Column(
            [
                # Cabeçalho com logo
                ft.Container(
                    content=ft.Column(
                        [
                            rounded_logo(size=80, show_name=True),
                            ft.Divider(height=20, color="transparent"),
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Icon(ft.Icons.PERSON, size=16, color="grey600"),
                                        ft.Text("Admin", size=12, color="grey700"),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                bgcolor="#F5F5F5",  # GREY_100
                                border_radius=20,
                                padding=ft.padding.symmetric(horizontal=12, vertical=6),
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.only(top=30, bottom=20, left=10, right=10),
                ),
                
                ft.Divider(height=1, color="#E0E0E0"),  # GREY_300
                
                # Menu de navegação
                ft.Container(
                    content=ft.NavigationRail(
                        selected_index=0,
                        label_type=ft.NavigationRailLabelType.ALL,
                        min_width=100,
                        min_extended_width=400,
                        group_alignment=-0.9,
                        destinations=[
                            ft.NavigationRailDestination(
                                icon_content=ft.Icon(ft.Icons.PERSON_ADD),
                                selected_icon_content=ft.Icon(ft.Icons.PERSON_ADD, color="#1976D2"),  # BLUE_700
                                label="Visitantes"
                            ),
                            ft.NavigationRailDestination(
                                icon_content=ft.Icon(ft.Icons.GROUPS),
                                selected_icon_content=ft.Icon(ft.Icons.GROUPS, color="#1976D2"),  # BLUE_700
                                label="Células"
                            ),
                            ft.NavigationRailDestination(
                                icon_content=ft.Icon(ft.Icons.LOGOUT),
                                selected_icon_content=ft.Icon(ft.Icons.LOGOUT, color="#D32F2F"),  # RED_700
                                label="Sair"
                            ),
                        ],
                        on_change=change_tool
                    ),
                    expand=True,
                ),
            ],
            spacing=0,
        ),
        width=150,
        bgcolor="#FAFAFA",  # GREY_50
    )

    return ft.View(
        route="/dashboard",
        controls=[
            ft.Row([
                sidebar,
                ft.VerticalDivider(width=1, color="#E0E0E0"),  # GREY_300
                main_content
            ], expand=True, spacing=0)
        ],
        bgcolor="white",
    )
