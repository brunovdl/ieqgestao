"""
View do Dashboard Principal
"""
import flet as ft
from .visitors_view import visitors_view
from .users_view import users_view
from .components import rounded_logo


def dashboard_view(page: ft.Page, db, on_logout, current_user):
    """
    Cria a view do dashboard principal
    
    Args:
        page: Página do Flet
        db: Instância do banco de dados
        on_logout: Callback para logout
        current_user: Nome do usuário logado
        
    Returns:
        ft.View: View do dashboard
    """
    # Obter permissões do usuário
    permissions = db.get_user_permissions(current_user)
    
    # Conteúdo inicial (primeira tela disponível)
    initial_content = None
    if permissions.get("visitantes"):
        initial_content = visitors_view(page, db)
    elif permissions.get("celulas"):
        initial_content = ft.Column([
            ft.Text("Gestão de Células", size=20, weight="bold"),
            ft.Divider(),
            ft.Text("Em desenvolvimento...", size=16, color="grey")
        ])
    elif permissions.get("usuarios"):
        initial_content = users_view(page, db)
    elif permissions.get("colaboradores"):
        initial_content = collaborators_view(page, db)
    else:
        initial_content = ft.Column([
            ft.Text("Sem Permissões", size=20, weight="bold"),
            ft.Divider(),
            ft.Text("Você não tem permissão para acessar nenhuma área.", size=16, color="red")
        ])
    
    main_content = ft.Container(
        content=initial_content,
        expand=True,
        padding=20
    )

    def change_tool(e):
        """Altera a ferramenta/seção do dashboard"""
        idx = e.control.selected_index
        
        # Mapear índice para funcionalidade baseado em permissões
        available_items = []
        if permissions.get("visitantes"):
            available_items.append("visitantes")
        if permissions.get("celulas"):
            available_items.append("celulas")
        if permissions.get("usuarios"):
            available_items.append("usuarios")
        
        available_items.append("sair")  # Sempre disponível
        
        selected_item = available_items[idx] if idx < len(available_items) else "sair"
        
        if selected_item == "visitantes":
            main_content.content = visitors_view(page, db)
        elif selected_item == "colaboradores":
            main_content.content = collaborators_view(page, db)
        elif selected_item == "celulas":
            main_content.content = ft.Column([
                ft.Text("Gestão de Células", size=20, weight="bold"),
                ft.Divider(),
                ft.Text("Em desenvolvimento...", size=16, color="grey")
            ])
        elif selected_item == "usuarios":
            main_content.content = users_view(page, db)
        elif selected_item == "sair":
            on_logout()
        
        page.update()

    # Construir destinos do menu baseado em permissões
    destinations = []
    
    if permissions.get("visitantes"):
        destinations.append(
            ft.NavigationRailDestination(
                icon=ft.Icons.PERSON_ADD,
                label="Visitantes"
            )
        )
    
    if permissions.get("celulas"):
        destinations.append(
            ft.NavigationRailDestination(
                icon=ft.Icons.GROUPS,
                label="Células"
            )
        )
    
    if permissions.get("usuarios"):
        destinations.append(
            ft.NavigationRailDestination(
                icon=ft.Icons.MANAGE_ACCOUNTS,
                label="Usuários"
            )
        )
    
    # Sair sempre disponível
    destinations.append(
        ft.NavigationRailDestination(
            icon=ft.Icons.LOGOUT,
            label="Sair"
        )
    )

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
                                        ft.Icon(ft.Icons.PERSON, size=16, color="grey"),
                                        ft.Text(current_user, size=12, color="grey"),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                bgcolor="#F5F5F5",
                                border_radius=20,
                                padding=12,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=20,
                ),
                
                ft.Divider(height=1, color="#E0E0E0"),
                
                # Menu de navegação
                ft.Container(
                    content=ft.NavigationRail(
                        selected_index=0,
                        label_type=ft.NavigationRailLabelType.ALL,
                        min_width=100,
                        destinations=destinations,
                        on_change=change_tool
                    ),
                    expand=True,
                ),
            ],
            spacing=0,
        ),
        width=150,
        bgcolor="#FAFAFA",
    )

    return ft.View(
        route="/dashboard",
        controls=[
            ft.Row([
                sidebar,
                ft.VerticalDivider(width=1, color="#E0E0E0"),
                main_content
            ], expand=True, spacing=0)
        ],
        bgcolor="white",
    )