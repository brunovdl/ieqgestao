"""
View de Login
"""
import flet as ft


def login_view(page: ft.Page, db, on_login_success):
    """
    Cria a view de login
    
    Args:
        page: Página do Flet
        db: Instância do banco de dados
        on_login_success: Callback para quando o login for bem-sucedido
        
    Returns:
        ft.View: View de login
    """
    user_input = ft.TextField(label="Usuário", width=300)
    pass_input = ft.TextField(
        label="Senha",
        password=True,
        can_reveal_password=True,
        width=300
    )
    error_text = ft.Text("", color="red")

    def attempt_login(e):
        """Tenta fazer login com as credenciais fornecidas"""
        if db.check_login(user_input.value, pass_input.value):
            on_login_success()
        else:
            error_text.value = "Usuário ou senha inválidos"
            page.update()

    return ft.View(
        route="/login",
        controls=[
            ft.Container(
                content=ft.Column([
                    ft.Image(
                        src="logoieq.png",
                        width=150,
                        height=150,
                        fit="contain",
                        error_content=ft.Icon(ft.Icons.BROKEN_IMAGE)
                    ),
                    ft.Text("Bem-vindo", size=24, weight="bold"),
                    ft.Text("Sistema de Gestão IEQ", size=14, color="grey"),
                    ft.Divider(height=20, color="transparent"),
                    user_input,
                    pass_input,
                    error_text,
                    ft.Button(
                        "Entrar",
                        on_click=attempt_login,
                        width=300,
                        height=50
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.Alignment(0, 0),
                expand=True
            )
        ]
    )
