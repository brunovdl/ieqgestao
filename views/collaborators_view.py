"""
View de Cadastro de Colaboradores
"""
import flet as ft
from datetime import datetime
from utils import ViaCEPService


def collaborators_view(page: ft.Page, db):
    """
    Cria a view de cadastro de colaboradores
    
    Args:
        page: Página do Flet
        db: Instância do banco de dados
        
    Returns:
        ft.Column: Conteúdo da view de colaboradores
    """
    
    # Estado da view
    view_mode = {"current": "list"}  # 'list' ou 'form'
    edit_collab_id = [None]
    
    # ========== FORMULÁRIO ==========
    
    # Dados pessoais
    txt_name = ft.TextField(
        label="Nome Completo *",
        prefix_icon=ft.Icons.PERSON,
        width=400
    )
    txt_phone = ft.TextField(
        label="Telefone/WhatsApp",
        prefix_icon=ft.Icons.PHONE,
        keyboard_type=ft.KeyboardType.PHONE,
        width=300
    )
    txt_email = ft.TextField(
        label="E-mail",
        prefix_icon=ft.Icons.EMAIL,
        keyboard_type=ft.KeyboardType.EMAIL,
        width=300
    )
    
    # Dados profissionais
    txt_role = ft.TextField(
        label="Cargo/Função *",
        prefix_icon=ft.Icons.WORK,
        width=300
    )
    
    txt_department = ft.Dropdown(
        label="Departamento *",
        prefix_icon=ft.Icons.BUSINESS,
        width=300,
        options=[
            ft.dropdown.Option("Administração"),
            ft.dropdown.Option("Pastoral"),
            ft.dropdown.Option("Louvor"),
            ft.dropdown.Option("Mídia"),
            ft.dropdown.Option("Infantil"),
            ft.dropdown.Option("Jovens"),
            ft.dropdown.Option("Intercessão"),
            ft.dropdown.Option("Recepção"),
            ft.dropdown.Option("Limpeza"),
            ft.dropdown.Option("Manutenção"),
            ft.dropdown.Option("Outro"),
        ],
    )
    
    txt_hire_date = ft.TextField(
        label="Data de Início",
        prefix_icon=ft.Icons.CALENDAR_TODAY,
        hint_text="DD/MM/AAAA",
        width=200,
        value=datetime.now().strftime("%d/%m/%Y")
    )
    
    # Endereço
    txt_cep = ft.TextField(
        label="CEP",
        prefix_icon=ft.Icons.LOCATION_ON,
        hint_text="00000-000",
        max_length=9,
        keyboard_type=ft.KeyboardType.NUMBER,
        width=150
    )
    
    txt_street = ft.TextField(
        label="Logradouro",
        prefix_icon=ft.Icons.SIGNPOST,
        width=400
    )
    
    txt_number = ft.TextField(
        label="Número",
        prefix_icon=ft.Icons.NUMBERS,
        width=100
    )
    
    txt_complement = ft.TextField(
        label="Complemento",
        prefix_icon=ft.Icons.HOME_WORK,
        width=200
    )
    
    txt_neighborhood = ft.TextField(
        label="Bairro",
        prefix_icon=ft.Icons.LOCATION_CITY,
        width=300
    )
    
    txt_city = ft.TextField(
        label="Cidade",
        prefix_icon=ft.Icons.LOCATION_CITY,
        width=250
    )
    
    txt_state = ft.TextField(
        label="UF",
        prefix_icon=ft.Icons.MAP,
        max_length=2,
        width=80
    )
    
    txt_obs = ft.TextField(
        label="Observações",
        multiline=True,
        min_lines=3,
        max_lines=5,
        width=400
    )
    
    # Indicadores
    loading_indicator = ft.ProgressRing(visible=False, width=20, height=20)
    cep_status = ft.Text("", size=12)
    
    def search_cep(e):
        """Busca endereço pelo CEP"""
        cep = txt_cep.value
        
        if not cep or len(ViaCEPService.clean_cep(cep)) < 8:
            return
        
        loading_indicator.visible = True
        cep_status.value = "Buscando..."
        cep_status.color = "blue"
        page.update()
        
        address_data = ViaCEPService.search_by_cep(cep)
        
        if address_data:
            txt_street.value = address_data.get('logradouro', '')
            txt_neighborhood.value = address_data.get('bairro', '')
            txt_city.value = address_data.get('localidade', '')
            txt_state.value = address_data.get('uf', '')
            txt_cep.value = ViaCEPService.format_cep(cep)
            
            cep_status.value = "✓ CEP encontrado!"
            cep_status.color = "green"
        else:
            cep_status.value = "✗ CEP não encontrado"
            cep_status.color = "red"
        
        loading_indicator.visible = False
        page.update()
    
    txt_cep.on_change = search_cep
    
    def save_collaborator(e):
        """Salva colaborador no banco"""
        # Validação
        if not txt_name.value:
            txt_name.error_text = "Nome é obrigatório"
            page.update()
            return
        
        if not txt_role.value:
            txt_role.error_text = "Cargo é obrigatório"
            page.update()
            return
        
        if not txt_department.value:
            txt_department.error_text = "Departamento é obrigatório"
            page.update()
            return
        
        # Montar endereço completo
        address_parts = []
        if txt_street.value:
            street_with_number = txt_street.value
            if txt_number.value:
                street_with_number += f", {txt_number.value}"
            address_parts.append(street_with_number)
        
        if txt_complement.value:
            address_parts.append(txt_complement.value)
        if txt_neighborhood.value:
            address_parts.append(txt_neighborhood.value)
        if txt_city.value and txt_state.value:
            address_parts.append(f"{txt_city.value}/{txt_state.value}")
        if txt_cep.value:
            address_parts.append(f"CEP: {txt_cep.value}")
        
        full_address = ", ".join(address_parts) if address_parts else ""
        
        # Salvar
        if edit_collab_id[0] is None:
            # Novo colaborador
            success = db.add_collaborator(
                txt_name.value,
                txt_phone.value,
                txt_email.value,
                full_address,
                txt_role.value,
                txt_department.value,
                txt_hire_date.value,
                txt_obs.value
            )
            msg = "Colaborador cadastrado com sucesso!"
        else:
            # Atualizar colaborador
            success = db.update_collaborator(
                edit_collab_id[0],
                name=txt_name.value,
                phone=txt_phone.value,
                email=txt_email.value,
                address=full_address,
                role=txt_role.value,
                department=txt_department.value,
                hire_date=txt_hire_date.value,
                observations=txt_obs.value
            )
            msg = "Colaborador atualizado com sucesso!"
        
        if success:
            page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="green")
            clear_form()
            show_list()
        else:
            page.snack_bar = ft.SnackBar(ft.Text("Erro ao salvar!"), bgcolor="red")
        
        page.snack_bar.open = True
        page.update()
    
    def clear_form():
        """Limpa todos os campos do formulário"""
        txt_name.value = ""
        txt_name.error_text = ""
        txt_phone.value = ""
        txt_email.value = ""
        txt_cep.value = ""
        txt_street.value = ""
        txt_number.value = ""
        txt_complement.value = ""
        txt_neighborhood.value = ""
        txt_city.value = ""
        txt_state.value = ""
        txt_role.value = ""
        txt_role.error_text = ""
        txt_department.value = None
        txt_department.error_text = ""
        txt_hire_date.value = datetime.now().strftime("%d/%m/%Y")
        txt_obs.value = ""
        cep_status.value = ""
        edit_collab_id[0] = None
    
    # Formulário
    form_content = ft.Column([
        ft.Row([
            ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                tooltip="Voltar",
                on_click=lambda e: show_list()
            ),
            ft.Text(
                "Novo Colaborador",
                size=20,
                weight="bold"
            ),
        ]),
        ft.Divider(),
        
        # Dados Pessoais
        ft.Text("Dados Pessoais", size=16, weight="bold"),
        txt_name,
        ft.Row([txt_phone, txt_email]),
        
        ft.Divider(),
        
        # Dados Profissionais
        ft.Text("Dados Profissionais", size=16, weight="bold"),
        ft.Row([txt_role, txt_department]),
        txt_hire_date,
        
        ft.Divider(),
        
        # Endereço
        ft.Text("Endereço", size=16, weight="bold"),
        ft.Row([txt_cep, loading_indicator]),
        cep_status,
        txt_street,
        ft.Row([txt_number, txt_complement]),
        txt_neighborhood,
        ft.Row([txt_city, txt_state]),
        
        ft.Divider(),
        
        # Observações
        txt_obs,
        
        # Botões
        ft.Row([
            ft.Button(
                "Cancelar",
                icon=ft.Icons.CANCEL,
                on_click=lambda e: (clear_form(), show_list())
            ),
            ft.Button(
                "Salvar",
                icon=ft.Icons.SAVE,
                on_click=save_collaborator,
                style=ft.ButtonStyle(
                    bgcolor="#1976D2",
                    color="white"
                )
            ),
        ], alignment=ft.MainAxisAlignment.END),
    ], scroll=ft.ScrollMode.AUTO)
    
    # ========== LISTA ==========
    
    collaborators_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    
    def load_collaborators():
        """Carrega lista de colaboradores"""
        collaborators_list.controls.clear()
        collabs = db.get_all_collaborators()
        
        if not collabs:
            collaborators_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.PEOPLE_OUTLINE, size=64, color="grey"),
                        ft.Text("Nenhum colaborador cadastrado", color="grey"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    padding=40
                )
            )
        else:
            for collab in collabs:
                collab_id, name, phone, email, address, role, department, hire_date, reg_date, obs, active = collab
                
                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.PERSON, color="#1976D2", size=32),
                                ft.Column([
                                    ft.Text(name, weight="bold", size=16),
                                    ft.Text(f"{role} • {department}", size=12, color="grey"),
                                ], spacing=0, expand=True),
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    tooltip="Editar",
                                    on_click=lambda e, c=collab: edit_collaborator(c)
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE,
                                    tooltip="Desativar",
                                    icon_color="red",
                                    on_click=lambda e, cid=collab_id, n=name: deactivate_collab(cid, n)
                                ),
                            ]),
                            ft.Divider(height=1),
                            ft.Row([
                                ft.Icon(ft.Icons.PHONE, size=16, color="grey"),
                                ft.Text(phone or "Sem telefone", size=12),
                            ], spacing=5) if phone else ft.Container(),
                            ft.Row([
                                ft.Icon(ft.Icons.EMAIL, size=16, color="grey"),
                                ft.Text(email or "Sem e-mail", size=12),
                            ], spacing=5) if email else ft.Container(),
                            ft.Row([
                                ft.Icon(ft.Icons.CALENDAR_TODAY, size=16, color="grey"),
                                ft.Text(f"Início: {hire_date}", size=12),
                            ], spacing=5) if hire_date else ft.Container(),
                        ], spacing=8),
                        padding=15
                    )
                )
                
                collaborators_list.controls.append(card)
        
        page.update()
    
    def edit_collaborator(collab):
        """Preenche formulário para edição"""
        collab_id, name, phone, email, address, role, department, hire_date, reg_date, obs, active = collab
        
        edit_collab_id[0] = collab_id
        txt_name.value = name
        txt_phone.value = phone or ""
        txt_email.value = email or ""
        txt_role.value = role or ""
        txt_department.value = department or None
        txt_hire_date.value = hire_date or ""
        txt_obs.value = obs or ""
        
        # TODO: Parsear endereço de volta para campos individuais se necessário
        
        form_content.controls[0].controls[1].value = f"Editar: {name}"
        show_form()
    
    def deactivate_collab(collab_id, name):
        """Desativa um colaborador"""
        def confirm(e):
            if db.deactivate_collaborator(collab_id):
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"{name} desativado!"),
                    bgcolor="green"
                )
                load_collaborators()
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("Erro ao desativar!"),
                    bgcolor="red"
                )
            
            dialog.open = False
            page.snack_bar.open = True
            page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirmar Desativação"),
            content=ft.Text(f"Deseja desativar o colaborador '{name}'?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(dialog, 'open', False) or page.update()),
                ft.TextButton("Desativar", on_click=confirm),
            ],
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    list_content = ft.Column([
        ft.Row([
            ft.Text("Colaboradores", size=20, weight="bold"),
            ft.IconButton(
                icon=ft.Icons.REFRESH,
                tooltip="Atualizar",
                on_click=lambda e: load_collaborators()
            ),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(),
        ft.Button(
            "Adicionar Colaborador",
            icon=ft.Icons.PERSON_ADD,
            on_click=lambda e: show_form(),
            height=50,
        ),
        ft.Divider(),
        collaborators_list,
    ], scroll=ft.ScrollMode.AUTO, expand=True)
    
    # Container principal
    main_container = ft.Container(content=list_content, expand=True)
    
    def show_form():
        """Mostra formulário"""
        view_mode["current"] = "form"
        form_content.controls[0].controls[1].value = "Novo Colaborador" if edit_collab_id[0] is None else f"Editar Colaborador"
        main_container.content = form_content
        page.update()
    
    def show_list():
        """Mostra lista"""
        view_mode["current"] = "list"
        clear_form()
        load_collaborators()
        main_container.content = list_content
        page.update()
    
    # Carregar lista inicial
    load_collaborators()
    
    return main_container