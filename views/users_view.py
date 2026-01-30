"""
View de Gestão de Usuários (Apenas para Admin)
"""
import flet as ft


def users_view(page: ft.Page, db):
    """
    Cria a view de gestão de usuários
    
    Args:
        page: Página do Flet
        db: Instância do banco de dados
        
    Returns:
        ft.Column: Conteúdo da view de usuários
    """
    
    # Lista de usuários
    users_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    
    def load_users():
        """Carrega lista de usuários"""
        users_list.controls.clear()
        users = db.get_all_users()
        
        for user in users:
            user_id, username, is_admin, permissions = user
            
            # Parse permissões
            import json
            try:
                perms = json.loads(permissions) if permissions else {}
            except:
                perms = {}
            
            # Card do usuário
            user_card = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(
                                ft.Icons.ADMIN_PANEL_SETTINGS if is_admin else ft.Icons.PERSON,
                                color="#1976D2" if is_admin else "grey"
                            ),
                            ft.Column([
                                ft.Text(username, weight="bold", size=16),
                                ft.Text(
                                    "Administrador" if is_admin else "Usuário",
                                    size=12,
                                    color="#1976D2" if is_admin else "grey"
                                ),
                            ], spacing=0, expand=True),
                            ft.IconButton(
                                icon=ft.Icons.EDIT,
                                tooltip="Editar",
                                on_click=lambda e, uid=user_id, uname=username, 
                                        admin=is_admin, perms=perms: edit_user(uid, uname, admin, perms)
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE,
                                tooltip="Deletar",
                                icon_color="red" if user_id != 1 else "grey",
                                disabled=user_id == 1,
                                on_click=lambda e, uid=user_id, uname=username: delete_user(uid, uname)
                            ),
                        ]),
                        # Mostrar permissões se não for admin
                        ft.Column([
                            ft.Divider(height=1),
                            ft.Text("Permissões:", size=12, weight="bold"),
                            ft.Wrap([
                                ft.Chip(
                                    label=ft.Text(perm.capitalize(), size=10),
                                    bgcolor="#E3F2FD" if value else "#FFEBEE",
                                    disabled=True,
                                ) for perm, value in perms.items() if value
                            ], spacing=5)
                        ], spacing=5) if not is_admin and perms else ft.Container()
                    ], spacing=10),
                    padding=15,
                )
            )
            
            users_list.controls.append(user_card)
        
        page.update()
    
    # Dialog para adicionar/editar usuário
    dlg_username = ft.TextField(label="Nome de Usuário", width=300)
    dlg_password = ft.TextField(label="Senha", password=True, can_reveal_password=True, width=300)
    dlg_is_admin = ft.Checkbox(label="Administrador", value=False)
    
    # Checkboxes de permissões
    perm_visitantes = ft.Checkbox(label="Visitantes", value=True)
    perm_celulas = ft.Checkbox(label="Células", value=False)
    perm_usuarios = ft.Checkbox(label="Usuários", value=False)
    perm_relatorios = ft.Checkbox(label="Relatórios", value=False)
    
    edit_user_id = [None]  # Lista para manter referência mutável
    
    def toggle_admin(e):
        """Desabilita permissões individuais se for admin"""
        is_admin = dlg_is_admin.value
        perm_visitantes.disabled = is_admin
        perm_celulas.disabled = is_admin
        perm_usuarios.disabled = is_admin
        perm_relatorios.disabled = is_admin
        
        if is_admin:
            perm_visitantes.value = True
            perm_celulas.value = True
            perm_usuarios.value = True
            perm_relatorios.value = True
        
        page.update()
    
    dlg_is_admin.on_change = toggle_admin
    
    def save_user(e):
        """Salva novo usuário ou atualiza existente"""
        if not dlg_username.value or not dlg_password.value:
            page.snack_bar = ft.SnackBar(ft.Text("Preencha todos os campos!"), bgcolor="red")
            page.snack_bar.open = True
            page.update()
            return
        
        permissions = {
            "visitantes": perm_visitantes.value,
            "celulas": perm_celulas.value,
            "usuarios": perm_usuarios.value,
            "relatorios": perm_relatorios.value
        }
        
        if edit_user_id[0] is None:
            # Novo usuário
            success = db.add_user(
                dlg_username.value,
                dlg_password.value,
                dlg_is_admin.value,
                permissions
            )
            msg = "Usuário criado com sucesso!" if success else "Erro ao criar usuário!"
        else:
            # Atualizar usuário
            success = db.update_user(
                edit_user_id[0],
                dlg_username.value,
                dlg_password.value if dlg_password.value else None,
                dlg_is_admin.value,
                permissions
            )
            msg = "Usuário atualizado com sucesso!" if success else "Erro ao atualizar usuário!"
        
        if success:
            user_dialog.open = False
            load_users()
            page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="green")
        else:
            page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="red")
        
        page.snack_bar.open = True
        page.update()
    
    user_dialog = ft.AlertDialog(
        title=ft.Text("Adicionar Usuário"),
        content=ft.Column([
            dlg_username,
            dlg_password,
            ft.Divider(),
            dlg_is_admin,
            ft.Divider(),
            ft.Text("Permissões:", weight="bold"),
            perm_visitantes,
            perm_celulas,
            perm_usuarios,
            perm_relatorios,
        ], tight=True, spacing=10, height=400),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: close_dialog()),
            ft.TextButton("Salvar", on_click=save_user),
        ],
    )
    
    def close_dialog():
        """Fecha dialog e limpa campos"""
        user_dialog.open = False
        edit_user_id[0] = None
        dlg_username.value = ""
        dlg_password.value = ""
        dlg_is_admin.value = False
        perm_visitantes.value = True
        perm_celulas.value = False
        perm_usuarios.value = False
        perm_relatorios.value = False
        perm_visitantes.disabled = False
        perm_celulas.disabled = False
        perm_usuarios.disabled = False
        perm_relatorios.disabled = False
        page.update()
    
    def add_user(e):
        """Abre dialog para adicionar usuário"""
        edit_user_id[0] = None
        user_dialog.title = ft.Text("Adicionar Usuário")
        dlg_password.label = "Senha"
        page.dialog = user_dialog
        user_dialog.open = True
        page.update()
    
    def edit_user(user_id, username, is_admin, perms):
        """Abre dialog para editar usuário"""
        edit_user_id[0] = user_id
        user_dialog.title = ft.Text(f"Editar Usuário: {username}")
        dlg_username.value = username
        dlg_password.value = ""
        dlg_password.label = "Nova Senha (deixe vazio para manter)"
        dlg_is_admin.value = is_admin
        
        perm_visitantes.value = perms.get("visitantes", False)
        perm_celulas.value = perms.get("celulas", False)
        perm_usuarios.value = perms.get("usuarios", False)
        perm_relatorios.value = perms.get("relatorios", False)
        
        toggle_admin(None)
        
        page.dialog = user_dialog
        user_dialog.open = True
        page.update()
    
    def delete_user(user_id, username):
        """Confirma e deleta usuário"""
        def confirm_delete(e):
            if db.delete_user(user_id):
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Usuário {username} deletado!"),
                    bgcolor="green"
                )
                load_users()
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("Erro ao deletar usuário!"),
                    bgcolor="red"
                )
            
            confirm_dialog.open = False
            page.snack_bar.open = True
            page.update()
        
        confirm_dialog = ft.AlertDialog(
            title=ft.Text("Confirmar Exclusão"),
            content=ft.Text(f"Deseja realmente deletar o usuário '{username}'?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(confirm_dialog, 'open', False) or page.update()),
                ft.TextButton("Deletar", on_click=confirm_delete),
            ],
        )
        
        page.dialog = confirm_dialog
        confirm_dialog.open = True
        page.update()
    
    # Carregar usuários ao iniciar
    load_users()
    
    return ft.Column([
        ft.Row([
            ft.Text("Gestão de Usuários", size=20, weight="bold"),
            ft.IconButton(
                icon=ft.Icons.REFRESH,
                tooltip="Atualizar",
                on_click=lambda e: load_users()
            ),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(),
        ft.Button(
            "Adicionar Novo Usuário",
            icon=ft.Icons.PERSON_ADD,
            on_click=add_user,
            height=50,
        ),
        ft.Divider(),
        users_list,
    ], scroll=ft.ScrollMode.AUTO, expand=True)