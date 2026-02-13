import flet as ft
import json
from datetime import datetime
from zoneinfo import ZoneInfo # Importação para Fuso Horário
from core.config import Config
from utils.helpers import show_success, show_error, show_warning

# Define o Fuso Horário Brasileiro
BR_TZ = ZoneInfo("America/Sao_Paulo")

def users_view(page, db, user_state, readonly=False):
    # Verifica permissão (apenas Admin deve ver isso)
    if readonly: 
        return ft.Center(ft.Text("Acesso Negado. Apenas administradores.", color="red", weight="bold"))
    
    view = ft.Ref[ft.Column]()

    # --- LISTAGEM ---
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
            ft.DataColumn(ft.Text("Último Login (BR)")), # Nova Coluna
            ft.DataColumn(ft.Text("Ações")),
        ]
        
        rows = []
        for u in items:
            # Desempacota os dados vindos do database.py
            # Estrutura: id, username, full_name, email, is_admin, permissions, created_at, last_login
            uid, uname, fname, email, is_adm, perms_json, created, last_login = u
            
            perms = json.loads(perms_json) if isinstance(perms_json, str) else (perms_json or {})
            has_visitor_access = perms.get('visitantes', False) or is_adm

            # Formatação do Perfil
            role_badge = ft.Container(
                content=ft.Text("ADMIN" if is_adm else "Usuário", size=10, weight="bold", color="white"),
                bgcolor="red" if is_adm else "green", padding=5, border_radius=5
            )
            
            # Ícone de Acesso
            vis_icon = ft.Icon(ft.Icons.CHECK_CIRCLE, color="green", size=16) if has_visitor_access else ft.Icon(ft.Icons.CANCEL, color="grey", size=16)

            # --- FORMATAÇÃO DE DATA (UTC -> BRASIL) ---
            last_login_display = "-"
            if last_login:
                try:
                    # Converte string ISO para objeto datetime
                    # O replace garante que o python entenda que o 'Z' ou falta dele é UTC
                    dt_utc = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
                    
                    # Converte para o fuso do Brasil
                    dt_br = dt_utc.astimezone(BR_TZ)
                    
                    # Formata para string legível
                    last_login_display = dt_br.strftime("%d/%m/%Y às %H:%M")
                except Exception:
                    last_login_display = last_login # Fallback se falhar

            actions = ft.Row([
                ft.IconButton(ft.Icons.EDIT, icon_color=Config.THEME_COLOR, tooltip="Editar", on_click=lambda e, x=uid: show_form(x)),
                ft.IconButton(ft.Icons.DELETE, icon_color="red", tooltip="Excluir", disabled=(uid==1), on_click=lambda e, x=uid: (db.delete_user(x), show_list(search_field.value)))
            ], spacing=0)

            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(fname, weight="bold")),
                ft.DataCell(ft.Text(uname)),
                ft.DataCell(role_badge),
                ft.DataCell(vis_icon),
                ft.DataCell(ft.Text(last_login_display, size=12)), # Exibe data formatada
                ft.DataCell(actions),
            ]))

        table = ft.DataTable(
            columns=columns, 
            rows=rows, 
            heading_row_color=ft.colors.SURFACE_VARIANT, 
            column_spacing=20,
            data_row_min_height=50
        )
        
        # Botões do Header
        add_btn = ft.ElevatedButton("Novo Usuário", icon=ft.Icons.ADD, on_click=lambda e: show_form(), style=ft.ButtonStyle(bgcolor=Config.THEME_COLOR, color="white"))
        
        view.current.controls = [
            ft.Row([add_btn, search_field], alignment="spaceBetween"), 
            ft.Divider(), 
            ft.Row([table], scroll="always", expand=True, vertical_alignment="start")
        ]
        page.update()

    search_field = ft.TextField(hint_text="Buscar usuário...", prefix_icon=ft.Icons.SEARCH, width=250, height=40, content_padding=10, border_radius=20, on_change=lambda e: show_list(e.control.value))

    # --- FORMULÁRIO ---
    def show_form(uid=None):
        # Se for edição, busca dados
        ud = db.get_user_by_id(uid) if uid else None
        
        # Campos
        fn = ft.TextField(label="Nome Completo *", value=ud['full_name'] if ud else "", col=12)
        em = ft.TextField(label="Email", value=ud['email'] if ud else "", col=6)
        ph = ft.TextField(label="Telefone", value=ud['phone'] if ud else "", col=6)
        
        u = ft.TextField(label="Login (Usuário) *", value=ud['username'] if ud else "", col=6)
        p = ft.TextField(label="Senha" + (" (Deixe vazio para manter)" if uid else " *"), password=True, can_reveal_password=True, col=6)
        
        # Permissões
        is_admin_val = ud['is_admin'] if ud else False
        
        # Extrair permissão de visitantes com segurança
        perms_data = ud['permissions'] if ud else {}
        if isinstance(perms_data, str): perms_data = json.loads(perms_data)
        vis_val = perms_data.get('visitantes', False) if perms_data else False

        adm = ft.Checkbox(label="Administrador (Acesso Total)", value=is_admin_val, col=12)
        vis = ft.Checkbox(label="Permitir Acesso a Visitantes", value=vis_val, col=12)
        
        def save(e):
            if not fn.value or not u.value:
                show_warning(page, "Nome e Login são obrigatórios!")
                return
            if not uid and not p.value:
                show_warning(page, "Senha é obrigatória para novos usuários!")
                return

            # Estrutura de permissões padrão
            # Carona agora é padrão para todos, não precisa estar aqui explicitamente se for true no backend, 
            # mas garantimos que admins tenham tudo.
            perms_dict = {
                "visitantes": vis.value, 
                "celulas": True, 
                "galeria": True,
                "carona": True 
            }
            
            if uid:
                # Update
                if db.update_user(uid, u.value, p.value, adm.value, perms_dict, fn.value, em.value, ph.value):
                    show_success(page, "Usuário atualizado!")
                    show_list()
                else:
                    show_error(page, "Erro ao atualizar.")
            else:
                # Create
                if db.add_user(u.value, p.value, adm.value, perms_dict, fn.value, em.value, ph.value): 
                    show_success(page, "Usuário criado!")
                    show_list()
                else:
                    show_error(page, "Erro ao criar (Verifique se o login já existe).")
            
        view.current.controls = [
            ft.Column([
                ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: show_list()), ft.Text("Editar Usuário" if uid else "Novo Usuário", size=20, weight="bold")]), 
                ft.Divider(),
                ft.ResponsiveRow([fn, em, ph, u, p, adm, vis]), 
                ft.Container(ft.Button("Salvar", on_click=save, style=ft.ButtonStyle(bgcolor=Config.THEME_COLOR, color="white")), padding=20)
            ], scroll="auto", expand=True)
        ]
        page.update()

    col = ft.Column(expand=True, ref=view)
    show_list()
    return col