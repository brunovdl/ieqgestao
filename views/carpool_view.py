import flet as ft
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from core.config import Config
from utils.helpers import show_success, show_error, show_warning, open_whatsapp, ViaCEPService

BR_TZ = ZoneInfo("America/Sao_Paulo")

def carpool_view(page, db, user_state, readonly=False):
    view = ft.Ref[ft.Column]()
    
    # Lista de Caronas
    rides_list_view = ft.ListView(expand=True, spacing=10)
    
    stop_refresh = [False]
    last_data_snapshot = [None] 

    def auto_refresh_loop():
        while not stop_refresh[0]:
            try:
                if view.current: refresh_list(silent=True)
            except: pass
            time.sleep(5)

    threading.Thread(target=auto_refresh_loop, daemon=True).start()

    # --- FORMULÁRIO ---
    def show_ride_form(e=None, edit_data=None):
        form_title = "Editar Carona" if edit_data else "Oferecer Carona"
        events = db.get_upcoming_events()
        cells = db.get_all_cells()
        destinations_map = {} 
        options = []

        if events:
            options.append(ft.dropdown.Option(key="header_ev", text="--- EVENTOS ---", disabled=True))
            for ev in events:
                try:
                    dt = datetime.strptime(ev['event_date'], "%Y-%m-%d")
                    tm = datetime.strptime(ev['event_time'], "%H:%M:%S")
                    fmt = f"EVENTO: {ev['title']} ({dt.strftime('%d/%m')} às {tm.strftime('%H:%M')})"
                    key = f"EV_{ev['id']}"
                    destinations_map[key] = {"type": "event", "data": ev, "dt": dt, "tm": tm}
                    options.append(ft.dropdown.Option(key=key, text=fmt))
                except: continue

        active_cells = [c for c in cells if c[8]]
        if active_cells:
            options.append(ft.dropdown.Option(key="header_cell", text="--- CASAS DE CORNÉLIO ---", disabled=True))
            for c in active_cells:
                fmt = f"CÉLULA: {c[1]} ({c[5]} às {c[6]})"
                key = f"CELL_{c[0]}"
                destinations_map[key] = {"type": "cell", "data": c}
                options.append(ft.dropdown.Option(key=key, text=fmt))

        init_cep = ""
        init_bairro = edit_data['origin'] if edit_data else ""
        init_vagas = str(edit_data['available_seats']) if edit_data else "4"
        init_whats = edit_data['whatsapp'] if edit_data else ""
        
        init_date_val = datetime.now().strftime("%d/%m/%Y")
        init_time_val = "19:00"
        
        if edit_data:
            try:
                dt_obj = datetime.fromisoformat(edit_data['ride_datetime'].replace('Z', '+00:00')).astimezone(BR_TZ)
                init_date_val = dt_obj.strftime("%d/%m/%Y")
                init_time_val = dt_obj.strftime("%H:%M")
            except: pass

        cep_field = ft.TextField(label="CEP", value=init_cep, max_length=8, keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, col=5)
        bairro_field = ft.TextField(label="Bairro de Saída", value=init_bairro, expand=True, col=7)
        btn_busca_cep = ft.IconButton(icon=ft.Icons.SEARCH, tooltip="Buscar CEP", col=2)
        
        def buscar_cep(e):
            if len(cep_field.value) < 8: return
            cep_field.error_text = None; page.update()
            res = ViaCEPService.search_by_cep(cep_field.value)
            if res:
                bairro, logra = res.get('bairro', ''), res.get('logradouro', '')
                bairro_field.value = f"{bairro} ({logra})" if logra else bairro
                bairro_field.update()
            else:
                cep_field.error_text = "CEP não encontrado"; cep_field.update()

        btn_busca_cep.on_click = buscar_cep
        cep_field.on_change = lambda e: buscar_cep(e) if len(e.control.value) == 8 else None

        dd_destinos = ft.Dropdown(label="Qual o Destino?", options=options, col=12)
        if edit_data: dd_destinos.hint_text = f"Atual: {edit_data['destination']}"

        dt_txt = ft.TextField(label="Data", value=init_date_val, read_only=True, col=6)
        hora_saida = ft.TextField(label="Saída (HH:MM)", value=init_time_val, col=6)
        
        date_picker = ft.DatePicker(first_date=datetime(2024, 1, 1), last_date=datetime(2030, 12, 31), on_change=lambda e: (setattr(dt_txt, 'value', e.control.value.strftime("%d/%m/%Y")), dt_txt.update()) if e.control.value else None)
        page.overlay.append(date_picker)
        btn_calendar = ft.IconButton(ft.Icons.CALENDAR_MONTH, on_click=lambda _: date_picker.pick_date(), col=2)

        def on_dest_change(e):
            key = dd_destinos.value
            if not key: return
            info = destinations_map.get(key)
            if info and info["type"] == "event":
                dt_txt.value = info["dt"].strftime("%d/%m/%Y"); dt_txt.read_only = True; btn_calendar.disabled = True
            else:
                dt_txt.read_only = False; btn_calendar.disabled = False
            dt_txt.update(); btn_calendar.update()

        dd_destinos.on_change = on_dest_change
        vagas = ft.TextField(label="Vagas", value=init_vagas, keyboard_type=ft.KeyboardType.NUMBER, col=3)
        whats = ft.TextField(label="Seu WhatsApp", value=init_whats, icon=ft.Icons.PHONE, keyboard_type=ft.KeyboardType.PHONE, col=9)

        # Texto de validação inline (visível dentro do dialog)
        validation_text = ft.Text("", color="red", size=13, visible=False)

        def show_form_error(msg):
            validation_text.value = msg
            validation_text.visible = True
            validation_text.update()

        def save(e):
            validation_text.visible = False
            if not bairro_field.value or not hora_saida.value:
                show_form_error("⚠ Preencha Bairro e Horário!"); return
            
            key = dd_destinos.value
            dest_name = edit_data['destination'] if edit_data and not key else ""
            event_dt_iso = edit_data['event_datetime'] if edit_data and not key else None
            
            if key:
                info = destinations_map.get(key)
                if info:
                    if info["type"] == "event":
                        dest_name = info["data"]["title"]
                        ev_dt_naive = datetime.strptime(f"{info['data']['event_date']} {info['data']['event_time']}", "%Y-%m-%d %H:%M:%S")
                        event_dt_iso = ev_dt_naive.replace(tzinfo=BR_TZ).isoformat()
                    else:
                        dest_name = f"Célula: {info['data'][1]}"
                        event_dt_iso = None 

            if not dest_name: show_form_error("⚠ Selecione um destino!"); return

            try:
                ride_dt_naive = datetime.strptime(f"{dt_txt.value} {hora_saida.value}", "%d/%m/%Y %H:%M")
                ride_dt_aware = ride_dt_naive.replace(tzinfo=BR_TZ)
            except ValueError: show_form_error("⚠ Data ou Hora inválida!"); return

            driver_display_name = user_state.get('full_name', user_state.get('user', 'Anônimo'))
            
            if edit_data:
                if db.update_ride(edit_data['id'], bairro_field.value, dest_name, ride_dt_aware.isoformat(), vagas.value, whats.value, event_dt_iso):
                    show_success(page, "Carona atualizada!")
                    page.close(dlg); last_data_snapshot[0] = None; refresh_list()
                else: show_error(page, "Erro ao atualizar.")
            else:
                if db.add_ride(driver_display_name, bairro_field.value, dest_name, ride_dt_aware.isoformat(), vagas.value, whats.value, event_dt_iso):
                    show_success(page, "Carona ofertada!")
                    page.close(dlg); last_data_snapshot[0] = None; refresh_list()
                else: show_error(page, "Erro ao salvar.")

        dlg = ft.AlertDialog(title=ft.Text(form_title), content=ft.Container(width=500, content=ft.Column([validation_text, ft.Text("Destino e Data", weight="bold"), ft.ResponsiveRow([dd_destinos]), ft.ResponsiveRow([dt_txt, btn_calendar, hora_saida], vertical_alignment="center"), ft.Divider(), ft.Text("Origem", weight="bold"), ft.ResponsiveRow([cep_field, btn_busca_cep, bairro_field], vertical_alignment="center"), ft.Divider(), ft.Text("Detalhes", weight="bold"), ft.ResponsiveRow([vagas, whats])], scroll="auto")), actions=[ft.TextButton("Cancelar", on_click=lambda e: page.close(dlg)), ft.ElevatedButton("Salvar", on_click=save, bgcolor=Config.THEME_COLOR, color="white")])
        page.open(dlg)

    # --- LISTAGEM OTIMIZADA ---
    def refresh_list(silent=False):
        rides = db.get_upcoming_rides()
        
        if rides == last_data_snapshot[0]: return
        last_data_snapshot[0] = rides

        if not rides:
            rides_list_view.controls = [
                ft.Container(content=ft.Column([
                    ft.Icon(ft.Icons.DIRECTIONS_CAR, size=64, color="grey"), 
                    ft.Text("Nenhuma carona disponível.", color="grey")
                ], horizontal_alignment="center"), padding=40, alignment=ft.alignment.center)
            ]
            try: rides_list_view.update()
            except: pass
            return

        cards = []
        now_br = datetime.now(BR_TZ)
        my_name = user_state.get('full_name') 
        my_user = user_state.get('user')
        is_admin = user_state.get('perms', {}).get('is_admin', False)

        for r in rides:
            rid, driver, orig, dest = r['id'], r['driver_name'], r['origin'], r['destination']
            seats, passengers_str, phone = r['available_seats'], r['passengers'] or "", r['whatsapp']
            
            ride_dt_display, is_locked, lock_reason = "Data inválida", False, ""

            try:
                ride_obj = datetime.fromisoformat(r['ride_datetime']).replace(tzinfo=BR_TZ) if datetime.fromisoformat(r['ride_datetime']).tzinfo is None else datetime.fromisoformat(r['ride_datetime']).astimezone(BR_TZ)
                ride_dt_display = ride_obj.strftime("%d/%m às %H:%M")
                
                if r.get('event_datetime'):
                    event_obj = datetime.fromisoformat(r['event_datetime'])
                    if event_obj.tzinfo is None: event_obj = event_obj.replace(tzinfo=BR_TZ)
                    else: event_obj = event_obj.astimezone(BR_TZ)
                    if now_br > (event_obj - timedelta(minutes=30)): is_locked = True; lock_reason = "Inscrições Encerradas"
            except: pass

            is_me = (driver == my_name) or (driver == my_user)
            can_edit_ride = is_me or is_admin

            # --- LÓGICA DE PASSAGEIROS (CHIPS) ---
            passengers_list = [p.strip() for p in passengers_str.split(',') if p.strip()]
            am_i_passenger = (my_name in passengers_list) or (my_user in passengers_list)

            chips_controls = []
            if passengers_list:
                for p_name in passengers_list:
                    # Posso remover se for eu motorista, eu passageiro ou admin
                    can_remove_this = is_me or is_admin or (p_name == my_name) or (p_name == my_user)
                    
                    chip = ft.Chip(
                        label=ft.Text(p_name, size=12),
                        bgcolor="blue50" if can_remove_this else "grey100",
                        delete_icon_color="red" if can_remove_this else "grey",
                        # Garante que o evento capture as variáveis corretas
                        on_delete=lambda e, nm=p_name, i=rid, p=passengers_str, s=seats: remove_passenger_click(i, nm, p, s) if can_remove_this else None,
                        disabled=not can_remove_this
                    )
                    chips_controls.append(chip)
            else:
                chips_controls.append(ft.Text("Nenhum passageiro ainda.", italic=True, size=12, color="grey"))

            def remove_passenger_click(ride_id, p_name, current_str, current_seats):
                if db.remove_passenger(ride_id, p_name, current_str, current_seats):
                    last_data_snapshot[0] = None 
                    show_success(page, f"{p_name} saiu da carona.")
                    refresh_list()
                else: show_error(page, "Erro ao remover passageiro.")

            def join(e, xid=rid, xpass=passengers_str, xseats=seats):
                me = user_state.get('full_name', user_state.get('user', 'Eu'))
                if me in passengers_list: show_warning(page, "Você já está nesta carona!"); return
                if xseats <= 0: return
                last_data_snapshot[0] = None
                if db.join_ride(xid, me, xpass, xseats): 
                    if not silent: show_success(page, "Vaga reservada!")
                    refresh_list()
                else: show_error(page, "Erro.")

            btn_text, btn_color, btn_disabled = "Reservar", "green", False
            if am_i_passenger: btn_text, btn_color, btn_disabled = "Confirmado", "blue", True
            elif seats <= 0: btn_text, btn_color, btn_disabled = "Lotado", "grey", True
            elif is_locked: btn_text, btn_color, btn_disabled = lock_reason, "grey", True
            elif is_me: btn_text, btn_color, btn_disabled = "Sua Carona", "blue", True

            actions = [ft.ElevatedButton(btn_text, icon=ft.Icons.ADD, on_click=join, disabled=btn_disabled, bgcolor=btn_color, color="white")]
            
            if phone and not is_me: 
                msg_text = f"Olá {driver} poderia me dar uma carona para {dest}?"
                actions.append(ft.IconButton(ft.Icons.PHONE, tooltip="WhatsApp", icon_color="green", url=open_whatsapp(phone, driver, msg_text)))
            
            if can_edit_ride: 
                actions.append(ft.IconButton(ft.Icons.EDIT, icon_color=Config.THEME_COLOR, tooltip="Editar", on_click=lambda e, ride_data=r: show_ride_form(edit_data=ride_data)))
                actions.append(ft.IconButton(ft.Icons.DELETE, icon_color="red", tooltip="Cancelar Carona", on_click=lambda e, x=rid: (last_data_snapshot.__setitem__(0, None), db.delete_ride(x), refresh_list())))

            card = ft.Card(elevation=3, content=ft.Container(padding=15, content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.DIRECTIONS_CAR, color=Config.THEME_COLOR), 
                    ft.Column([ft.Text(driver, weight="bold", size=15), ft.Text(f"Indo para: {dest}", size=13, color="grey")], spacing=2, expand=True), 
                    ft.Container(content=ft.Text(f"{seats} vagas", color="white", size=12), bgcolor="orange" if seats < 2 else "green", padding=5, border_radius=5)
                ]),
                ft.Divider(height=10, color="transparent"),
                ft.Row([ft.Icon(ft.Icons.PIN_DROP, size=14, color="grey"), ft.Text(f"Sai de: {orig}", size=13, expand=True, no_wrap=False)]),
                ft.Row([ft.Icon(ft.Icons.ACCESS_TIME, size=14, color="grey"), ft.Text(ride_dt_display, weight="bold", size=13, color="blue")]),
                ft.Container(height=5),
                ft.Text("Passageiros:", size=11, weight="bold", color="grey"),
                
                # --- CORREÇÃO AQUI: USANDO ft.Row(wrap=True) ---
                ft.Row(controls=chips_controls, wrap=True, spacing=5),
                
                ft.Row(actions, alignment="end")
            ])))
            cards.append(card)

        rides_list_view.controls = cards
        try: rides_list_view.update()
        except: pass

    def header():
        return ft.Column([
            ft.Row([
                ft.Text("Carona Solidária", size=24, weight="bold"),
                ft.ElevatedButton("Oferecer Carona", icon=ft.Icons.ADD, bgcolor=Config.THEME_COLOR, color="white", on_click=lambda e: show_ride_form())
            ], alignment="spaceBetween"),
            ft.Divider()
        ])

    col = ft.Column(expand=True, ref=view, controls=[header(), rides_list_view])
    def on_dismount(e): stop_refresh[0] = True
    col.on_detach = on_dismount
    refresh_list()
    return col