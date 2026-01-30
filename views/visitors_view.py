"""
View de Cadastro de Visitantes
"""
import flet as ft
from utils import ViaCEPService


def visitors_view(page: ft.Page, db):
    txt_name = ft.TextField(
        label="Nome do Visitante",
        prefix_icon=ft.Icons.PERSON
    )
    txt_phone = ft.TextField(
        label="WhatsApp/Telefone",
        prefix_icon=ft.Icons.PHONE,
        keyboard_type=ft.KeyboardType.PHONE
    )
    txt_email = ft.TextField(
        label="E-mail (Opcional)",
        prefix_icon=ft.Icons.EMAIL
    )
    
    # Campo CEP com busca automática
    txt_cep = ft.TextField(
        label="CEP",
        prefix_icon=ft.Icons.LOCATION_ON,
        hint_text="00000-000",
        max_length=9,
        keyboard_type=ft.KeyboardType.NUMBER
    )
    
    # Campos de endereço
    txt_street = ft.TextField(
        label="Logradouro (Rua/Avenida)",
        prefix_icon=ft.Icons.SIGNPOST,
        read_only=False
    )
    
    txt_number = ft.TextField(
        label="Número",
        prefix_icon=ft.Icons.NUMBERS,
        width=130
    )
    
    txt_complement = ft.TextField(
        label="Complemento",
        prefix_icon=ft.Icons.HOME_WORK,
        width=160
    )
    
    txt_neighborhood = ft.TextField(
        label="Bairro",
        prefix_icon=ft.Icons.LOCATION_CITY,
        read_only=False
    )
    
    txt_city = ft.TextField(
        label="Cidade",
        prefix_icon=ft.Icons.LOCATION_CITY,
        read_only=False,
        width=190
    )
    
    txt_state = ft.TextField(
        label="UF",
        prefix_icon=ft.Icons.MAP,
        read_only=False,
        width=100
    )
    
    txt_obs = ft.TextField(
        label="Observações",
        multiline=True,
        min_lines=3
    )
    
    # Indicador de carregamento
    loading_indicator = ft.ProgressRing(visible=False, width=20, height=20)
    cep_status = ft.Text("", size=12)
    
    def search_cep(e):
        """Busca endereço pelo CEP digitado"""
        cep = txt_cep.value
        
        if not cep or len(ViaCEPService.clean_cep(cep)) < 8:
            return
        
        # Mostrar loading
        loading_indicator.visible = True
        cep_status.value = "Buscando..."
        cep_status.color = "blue"
        page.update()
        
        # Buscar endereço
        address_data = ViaCEPService.search_by_cep(cep)
        
        if address_data:
            # Preencher campos automaticamente
            txt_street.value = address_data.get('logradouro', '')
            txt_neighborhood.value = address_data.get('bairro', '')
            txt_city.value = address_data.get('localidade', '')
            txt_state.value = address_data.get('uf', '')
            
            # Formatar CEP
            txt_cep.value = ViaCEPService.format_cep(cep)
            
            cep_status.value = "✓ CEP encontrado!"
            cep_status.color = "green"
            
            # Focar no campo número usando run_task
            page.run_task(txt_number.focus)
        else:
            cep_status.value = "✗ CEP não encontrado"
            cep_status.color = "red"
        
        loading_indicator.visible = False
        page.update()
    
    # Adicionar evento de mudança no CEP
    txt_cep.on_change = search_cep

    def save_visitor(e):
        """Salva o visitante no banco de dados"""
        # Validação
        if not txt_name.value:
            txt_name.error_text = "Nome é obrigatório"
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
        elif txt_city.value:
            address_parts.append(txt_city.value)
        
        if txt_cep.value:
            address_parts.append(f"CEP: {txt_cep.value}")
        
        full_address = ", ".join(address_parts) if address_parts else ""

        # Salvar no banco
        success = db.add_visitor(
            txt_name.value,
            txt_phone.value,
            txt_email.value,
            full_address,
            txt_obs.value
        )

        if success:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"{txt_name.value} salvo com sucesso!"),
                bgcolor="green"
            )
            page.snack_bar.open = True
            
            # Limpar campos
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
            txt_obs.value = ""
            cep_status.value = ""
            page.update()
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text("Erro ao salvar!"),
                bgcolor="red"
            )
            page.snack_bar.open = True
            page.update()

    return ft.Column([
        ft.Text("Novo Visitante", size=20, weight="bold"),
        ft.Divider(),
        
        # Dados pessoais
        ft.Text("Dados Pessoais", size=16, weight="bold"),
        txt_name,
        txt_phone,
        txt_email,
        
        ft.Divider(),
        
        # Endereço
        ft.Text("Endereço", size=16, weight="bold"),
        ft.Row([
            txt_cep,
            loading_indicator,
        ]),
        cep_status,
        txt_street,
        ft.Row([
            txt_number,
            txt_complement,
        ]),
        txt_neighborhood,
        ft.Row([
            txt_city,
            txt_state,
        ]),
        
        ft.Divider(),
        
        # Observações
        txt_obs,
        
        ft.Button(
            "Salvar",
            icon=ft.Icons.SAVE,
            on_click=save_visitor,
            height=50,
            width=400
        ),
    ], scroll=ft.ScrollMode.AUTO)
