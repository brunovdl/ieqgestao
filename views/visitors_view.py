import flet as ft
import time
import threading
from datetime import datetime
from core.config import Config
from utils.helpers import show_loading, hide_loading, show_success, show_error, show_warning, address_form_fields, open_whatsapp, GroqAIService

# --- Form Components ---
def visitor_form(page, db, vid=None, back_callback=None):
    # Se vid existe, carrega dados
    v_data = db.get_visitor_by_id(vid) if vid else None
    
    # Parsing de endereço se for edição
    full_address = v_data[4] if v_data and v_data[4] else ""
    cep_val, log_val, num_val, bai_val, cid_val, uf_val = "", "", "", "", "", ""
    try:
        if " CEP: " in full_address:
            parts = full_address.split(" CEP: ")
            cep_val = parts[1]
            address_part = parts[0]
            if " - " in address_part:
                street_part, loc_part = address_part.split(" - ", 1)
                if ", " in street_part: log_val, num_val = street_part.rsplit(", ", 1)
                else: log_val = street_part
                if ", " in loc_part:
                    bai_val, city_uf = loc_part.split(", ", 1)
                    if "/" in city_uf: cid_val, uf_val = city_uf.split("/")
                else: bai_val = loc_part
    except: pass

    # Campos
    n = ft.TextField(label="Nome Completo *", value=v_data[1] if v_data else "", prefix_icon=ft.Icons.PERSON, col=12)
    p = ft.TextField(label="WhatsApp / Telefone", value=v_data[2] if v_data else "", prefix_icon=ft.Icons.PHONE, keyboard_type=ft.KeyboardType.PHONE, col={"sm": 12, "md": 6})
    em = ft.TextField(label="E-mail", value=v_data[3] if v_data else "", prefix_icon=ft.Icons.EMAIL, col={"sm": 12, "md": 6})
    obs = ft.TextField(label="Observações", value=v_data[6] if v_data else "", multiline=True, min_lines=3, col=12)
    
    addr = address_form_fields(page)
    if v_data:
        addr["cep"].value = cep_val; addr["logradouro"].value = log_val; addr["numero"].value = num_val
        addr["bairro"].value = bai_val; addr["cidade"].value = cid_val; addr["uf"].value = uf_val

    def save(e):
        if not n.value: show_warning(page, "Nome obrigatório!"); return
        loading = show_loading(page, "Salvando...")
        
        full_addr = addr["get_full_address"]()
        if vid: success = db.update_visitor(vid, n.value, p.value, em.value, full_addr, obs.value)
        else: success = db.add_visitor(n.value, p.value, em.value, full_addr, obs.value)
        
        hide_loading(page, loading)
        if success:
            show_success(page, "Salvo com sucesso!")
            if back_callback: back_callback()
        else:
            show_error(page, "Erro ao salvar.")

    return ft.Column([
        ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: back_callback()) if back_callback else ft.Container(), ft.Text("Editar Visitante" if vid else "Novo Visitante", size=20, weight="bold")]),
        ft.Divider(),
        ft.ResponsiveRow([n]), ft.ResponsiveRow([p, em]),
        ft.Container(height=10), ft.Text("Endereço", weight="bold", size=16), addr["ui"],
        ft.Divider(), ft.ResponsiveRow([obs]),
        ft.Container(ft.Button("Salvar", icon=ft.Icons.SAVE, on_click=save, style=ft.ButtonStyle(bgcolor=Config.THEME_COLOR, color="white"), height=50), padding=20, alignment=ft.alignment.center)
    ], scroll="auto", expand=True)

# --- Main View ---
def visitors_list_view(page, db, user_state, readonly=False):
    view = ft.Ref[ft.Column]()
    is_mobile = page.width < 600
    
    def nav_to_form(vid=None):
        view.current.controls.clear()
        view.current.controls.append(visitor_form(page, db, vid, lambda: show_list()))
        page.update()

    # --- DIALOG DE MENSAGEM IA ---
    def show_ai_greeting_dialog(visitor_name, visitor_phone):
        """Gera mensagem com IA e exibe dialog para edição e aprovação."""
        msg_field = ft.TextField(
            label="Mensagem gerada pela IA",
            multiline=True,
            min_lines=4,
            max_lines=8,
            value="Gerando mensagem...",
            read_only=True,
            col=12
        )
        
        btn_send = ft.ElevatedButton(
            "Enviar via WhatsApp",
            icon=ft.Icons.SEND,
            bgcolor="green",
            color="white",
            disabled=True
        )
        
        btn_regenerate = ft.OutlinedButton(
            "Regenerar",
            icon=ft.Icons.REFRESH,
            disabled=True
        )

        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.AUTO_AWESOME, color="amber"),
                ft.Text("Mensagem de Saudação", weight="bold")
            ]),
            content=ft.Container(
                width=450,
                content=ft.Column([
                    ft.Text(f"Para: {visitor_name}", size=13, color="grey", italic=True),
                    msg_field,
                ], spacing=10)
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.close(dlg)),
                btn_regenerate,
                btn_send,
            ]
        )
        
        def generate_message():
            msg_field.value = "Gerando mensagem..."
            msg_field.read_only = True
            btn_send.disabled = True
            btn_regenerate.disabled = True
            try: page.update()
            except: pass

            message, error = GroqAIService.generate_greeting(Config.GROQ_API_KEY, visitor_name)
            
            if message:
                msg_field.value = message
                msg_field.read_only = False
                btn_send.disabled = False
                btn_regenerate.disabled = False
            else:
                msg_field.value = f"Erro ao gerar mensagem: {error}"
                btn_regenerate.disabled = False
            
            try: page.update()
            except: pass
        
        def send_whatsapp(e):
            final_msg = msg_field.value
            if not final_msg or final_msg.startswith("Gerando") or final_msg.startswith("Erro"):
                show_warning(page, "Mensagem inválida!")
                return
            url = open_whatsapp(visitor_phone, visitor_name, final_msg)
            page.close(dlg)
            page.launch_url(url)
        
        btn_send.on_click = send_whatsapp
        btn_regenerate.on_click = lambda e: threading.Thread(target=generate_message, daemon=True).start()
        
        page.open(dlg)
        threading.Thread(target=generate_message, daemon=True).start()

    def show_list(search_term=""):
        items = db.get_all_visitors()
        if search_term: items = [v for v in items if search_term.lower() in v[1].lower()]

        columns = [ft.DataColumn(ft.Text("Data")), ft.DataColumn(ft.Text("Nome")), ft.DataColumn(ft.Text("Status")), ft.DataColumn(ft.Text("Ações"))]
        rows = []
        
        for v in items:
            vid, name, phone, _, _, date_obj, _, c_by, c_at = v
            date_cell = ft.Text(date_obj.strftime("%d/%m") if date_obj else "-", size=12)
            
            name_display = name[:13]+"..." if is_mobile and len(name)>15 else name
            name_col = ft.Column([ft.Text(name_display, weight="bold", size=13), ft.Text(phone or "-", size=11, color="grey")], spacing=2)

            contact_txt = None
            if c_by:
                try: 
                    dt = datetime.fromisoformat(c_at.replace('Z', '+00:00'))
                    contact_txt = f"{c_by}\n{dt.strftime('%d/%m')}"
                except: contact_txt = c_by
            
            if contact_txt:
                status = ft.Container(content=ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color="green", size=14), ft.Text(contact_txt, size=10, color="green")], spacing=2), padding=5, border=ft.border.all(1, "green"), border_radius=8)
            else:
                status = ft.IconButton(icon=ft.Icons.HOW_TO_REG, icon_color="orange", on_click=lambda e, x=vid: (db.mark_visitor_contacted(x, user_state.get("user", "?")), show_list(search_term))) if is_mobile else ft.ElevatedButton("Marcar", bgcolor="orange", color="white", height=30, on_click=lambda e, x=vid: (db.mark_visitor_contacted(x, user_state.get("user", "?")), show_list(search_term)))

            btns = []
            if phone:
                btns.append(ft.IconButton(content=ft.Image(src="https://img.icons8.com/color/48/whatsapp--v1.png", width=24, height=24), url=open_whatsapp(phone, name, "")))
                # Botão de gerar mensagem com IA
                btns.append(ft.IconButton(
                    ft.Icons.AUTO_AWESOME,
                    icon_color="amber",
                    icon_size=20,
                    tooltip="Gerar mensagem com IA",
                    on_click=lambda e, n=name, p=phone: show_ai_greeting_dialog(n, p)
                ))
            if not readonly:
                btns.append(ft.IconButton(ft.Icons.EDIT, icon_color=Config.THEME_COLOR, icon_size=20, on_click=lambda e, x=vid: nav_to_form(x)))
                btns.append(ft.IconButton(ft.Icons.DELETE, icon_color="red", icon_size=20, on_click=lambda e, x=vid: (db.delete_visitor(x), show_list(search_term))))

            rows.append(ft.DataRow(cells=[ft.DataCell(date_cell), ft.DataCell(name_col), ft.DataCell(status), ft.DataCell(ft.Row(btns, spacing=0))]))

        table = ft.DataTable(columns=columns, rows=rows, heading_row_color=ft.colors.SURFACE_VARIANT, column_spacing=10 if is_mobile else 20, data_row_min_height=50)
        
        search = ft.TextField(hint_text="Buscar...", prefix_icon=ft.Icons.SEARCH, width=180 if is_mobile else 250, height=40, border_radius=20, on_change=lambda e: show_list(e.control.value))
        add_btn = ft.ElevatedButton("Novo" if not is_mobile else "+", icon=ft.Icons.ADD, on_click=lambda e: nav_to_form(), style=ft.ButtonStyle(bgcolor=Config.THEME_COLOR, color="white")) if not readonly else ft.Container()
        
        view.current.controls = [ft.Row([add_btn, search], alignment="spaceBetween"), ft.Divider(), ft.Row([table], scroll="always", expand=True, vertical_alignment="start")]
        page.update()

    col = ft.Column(expand=True, ref=view)
    show_list()
    return ft.Container(col, padding=5 if is_mobile else 10, expand=True)