import flet as ft
import threading
import time
from datetime import datetime
from core.config import Config
from utils.helpers import get_latest_video_id, show_success, show_error, show_warning, get_logo

# MUDANÇA 1: Adicionamos o argumento opcional 'webview_ref'
def home_view(page, db, readonly=False, webview_ref=None):
    
    # --- CARROSSEL DE FOTOS (Mantido) ---
    carousel_photos = db.get_recent_photos(15)
    if not carousel_photos: carousel_photos = ["https://via.placeholder.com/300x200?text=Bem-vindo"] * 6
    
    carousel_row = ft.Row(spacing=10, alignment=ft.MainAxisAlignment.CENTER)
    current_start_index = [0]

    def open_lightbox_home(src):
        img_full = ft.Image(src=src, fit=ft.ImageFit.CONTAIN, width=page.width, height=page.height)
        stack = ft.Stack([
            ft.Container(bgcolor="black", opacity=0.9, on_click=lambda e: close_lightbox(stack), expand=True),
            ft.Container(content=img_full, alignment=ft.alignment.center),
            ft.Container(content=ft.IconButton(ft.Icons.CLOSE, icon_color="white", icon_size=30, on_click=lambda e: close_lightbox(stack)), top=20, right=20)
        ], expand=True)
        page.overlay.append(stack); page.update()

    def close_lightbox(stack):
        page.overlay.remove(stack); page.update()

    def update_carousel_view(do_update=True):
        w = page.width if page.width else 800
        if w < 600: num_visible = 3
        elif w < 1000: num_visible = 4
        else: num_visible = 6
        
        spacing = 10; total_spacing = (num_visible - 1) * spacing
        available_width = w - 40; img_width = (available_width - total_spacing) / num_visible
        
        visible_images = []
        for i in range(num_visible):
            idx = (current_start_index[0] + i) % len(carousel_photos)
            src = carousel_photos[idx]
            img = ft.Image(src=src, key=src, height=160, width=img_width, fit=ft.ImageFit.COVER, border_radius=8, gapless_playback=True)
            switcher = ft.AnimatedSwitcher(content=img, transition=ft.AnimatedSwitcherTransition.FADE, duration=800, reverse_duration=100)
            container = ft.Container(content=switcher, on_click=lambda e, s=src: open_lightbox_home(s), ink=True, border_radius=8)
            visible_images.append(container)
            
        carousel_row.controls = visible_images
        if do_update:
            try:
                if carousel_row.page: carousel_row.update()
            except: pass

    def cycle_carousel():
        while True:
            time.sleep(4)
            try:
                current_start_index[0] = (current_start_index[0] + 1) % len(carousel_photos)
                update_carousel_view(do_update=True)
            except: break

    update_carousel_view(do_update=False)
    if len(carousel_photos) > 1: threading.Thread(target=cycle_carousel, daemon=True).start()

    # --- PLAYER DO YOUTUBE EMBUTIDO ---
    clean_id = Config.YOUTUBE_CHANNEL_ID.strip().replace('"', '').replace("'", "") if Config.YOUTUBE_CHANNEL_ID else ""
    
    video_id = get_latest_video_id(clean_id)
    
    if video_id:
        embed_url = f"https://www.youtube.com/embed/{video_id}"
        streams_url = f"https://www.youtube.com/channel/{clean_id}/streams"
        
        video_content = ft.Container(
            content=ft.WebView(
                ref=webview_ref, # MUDANÇA 2: Ligamos a referência aqui
                url=embed_url,
                expand=True,
            ),
            width=float("inf"),
            height=250, 
            border_radius=8,
            clip_behavior=ft.ClipBehavior.HARD_EDGE, 
            bgcolor="black" # Fundo preto para quando o vídeo estiver invisível
        )
    else:
        video_content = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.VIDEO_LIBRARY, size=50, color="grey"),
                ft.Text("Nenhum vídeo encontrado", color="grey")
            ], alignment="center", horizontal_alignment="center"),
            height=200, bgcolor="black12", border_radius=8
        )
        streams_url = "https://www.youtube.com/"

    yt_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.SMART_DISPLAY, color="red", size=28), 
                    ft.Text("Youtube", size=20, weight="bold", color="red")
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                
                video_content,
                
                ft.Row([
                    ft.TextButton("Ver Todos os Cultos", icon=ft.Icons.VIDEO_LIBRARY, on_click=lambda e: page.launch_url(streams_url), style=ft.ButtonStyle(color=Config.THEME_COLOR))
                ], alignment=ft.MainAxisAlignment.END)
            ], spacing=10), 
            padding=15
        ), 
        elevation=5
    )

    # --- AGENDA (Mantido) ---
    agenda_col = ft.Column([], spacing=10)
    WEEKDAYS = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}

    def refresh_agenda():
        events = db.get_upcoming_events()
        agenda_col.controls.clear()
        if not events: agenda_col.controls.append(ft.Text("Sem eventos próximos.", italic=True))
        today_str = datetime.now().strftime("%Y-%m-%d")

        for ev in events:
            d_obj = datetime.strptime(ev['event_date'], "%Y-%m-%d")
            t_obj = datetime.strptime(ev['event_time'], "%H:%M:%S")
            line1_text = f"{WEEKDAYS[d_obj.weekday()]} às {t_obj.strftime('%H:%M')}"
            is_today = (ev['event_date'] == today_str)
            
            actions = ft.Container()
            if not readonly:
                actions = ft.Column([
                    ft.IconButton(ft.Icons.EDIT, icon_color=Config.THEME_COLOR, tooltip="Editar", on_click=lambda e, x=ev: edit_ev_dialog(x)),
                    ft.IconButton(ft.Icons.DELETE, icon_color="red", tooltip="Excluir", on_click=lambda e, x=ev['id']: (db.delete_event(x), refresh_agenda(), show_success(page, "Removido!")))
                ], spacing=0)
            
            card = ft.Card(content=ft.Container(content=ft.Row([
                ft.Container(content=ft.Column([ft.Text(str(d_obj.day), size=24, weight="bold", color="white"), ft.Text(d_obj.strftime("%b").upper(), size=12, color="white")], alignment="center", spacing=0), bgcolor="green" if is_today else Config.THEME_COLOR, width=60, height=60, border_radius=8, alignment=ft.alignment.center),
                ft.Column([ft.Row([ft.Text(ev['title'], weight="bold", size=16), ft.Icon(ft.Icons.REPEAT, size=16, color="blue", tooltip="Evento Semanal") if ev.get('is_recurring') else ft.Container()], spacing=5), ft.Text(line1_text, size=14, color="black", weight="bold" if is_today else "normal"), ft.Text(f"Local: {ev['location']}", size=12, color="grey"), ft.Text(ev['description'], size=12, italic=True, color="grey")], expand=True, spacing=2),
                actions
            ]), padding=10))
            agenda_col.controls.append(card)
        page.update()

    def edit_ev_dialog(ev_data):
        t = ft.TextField(label="Título *", value=ev_data['title'])
        d = ft.TextField(label="Descrição", value=ev_data['description'] or "")
        tm = ft.TextField(label="Hora (HH:MM) *", value=ev_data['event_time'][:5])
        l = ft.TextField(label="Local", value=ev_data['location'])
        rec = ft.Checkbox(label="Recorrente (Semanal)", value=ev_data.get('is_recurring', False))
        
        current_date_obj = datetime.strptime(ev_data['event_date'], "%Y-%m-%d")
        dt = ft.TextField(label="Data (DD-MM-AAAA) *", value=current_date_obj.strftime("%d-%m-%Y"), read_only=True, expand=True)

        date_picker = ft.DatePicker(on_change=lambda e: (setattr(dt, 'value', e.control.value.strftime("%d-%m-%Y")) if e.control.value else None, dt.update()), first_date=datetime(2000, 1, 1), last_date=datetime(2050, 12, 31), value=current_date_obj)
        page.overlay.append(date_picker); page.update()

        def save_changes(e):
            if not t.value or not dt.value or not tm.value: show_warning(page, "Preencha Título, Data e Hora!"); return
            try: db_date = datetime.strptime(dt.value.strip(), "%d-%m-%Y").strftime("%Y-%m-%d")
            except ValueError: show_error(page, "Data inválida!"); return

            if db.update_event(ev_data['id'], t.value, d.value, db_date, tm.value, l.value, rec.value):
                page.close(dlg); refresh_agenda(); show_success(page, "Atualizado!")
            else: show_error(page, "Erro ao atualizar.")

        dlg = ft.AlertDialog(title=ft.Text("Editar Evento"), content=ft.Column([t, d, ft.Row([dt, ft.IconButton(ft.Icons.CALENDAR_MONTH, icon_color=Config.THEME_COLOR, on_click=lambda _: date_picker.pick_date())], alignment="center"), tm, l, rec], height=400, scroll="auto"), actions=[ft.TextButton("Cancelar", on_click=lambda e: page.close(dlg)), ft.TextButton("Salvar", on_click=save_changes)])
        page.open(dlg)

    def add_ev_dialog(e):
        t = ft.TextField(label="Título *")
        d = ft.TextField(label="Descrição")
        dt = ft.TextField(label="Data (DD-MM-AAAA) *", hint_text="Clique no calendário ->", read_only=True, expand=True)
        today = datetime.now()
        
        date_picker = ft.DatePicker(on_change=lambda e: (setattr(dt, 'value', e.control.value.strftime("%d-%m-%Y")) if e.control.value else None, dt.update()), first_date=datetime(2000, 1, 1), last_date=datetime(2050, 12, 31), current_date=today)
        page.overlay.append(date_picker); page.update()

        tm = ft.TextField(label="Hora (HH:MM) *", value="19:30")
        l = ft.TextField(label="Local", value="Igreja")
        rec = ft.Checkbox(label="Recorrente (Semanal)", value=False)
        
        def save(e):
            if not t.value or not dt.value or not tm.value: show_warning(page, "Preencha Título, Data e Hora!"); return
            try: db_date = datetime.strptime(dt.value.strip(), "%d-%m-%Y").strftime("%Y-%m-%d")
            except ValueError: show_error(page, "Data inválida!"); return

            if db.add_event(t.value, d.value, db_date, tm.value, l.value, rec.value): 
                page.close(dlg); refresh_agenda(); show_success(page, "Evento Adicionado!")
            else: show_error(page, "Erro ao salvar.")
        
        dlg = ft.AlertDialog(title=ft.Text("Novo Evento"), content=ft.Column([t, d, ft.Row([dt, ft.IconButton(ft.Icons.CALENDAR_MONTH, icon_color=Config.THEME_COLOR, on_click=lambda _: date_picker.pick_date())], alignment="center"), tm, l, rec], height=400, scroll="auto"), actions=[ft.TextButton("Cancelar", on_click=lambda e: page.close(dlg)), ft.TextButton("Salvar", on_click=save)])
        page.open(dlg)

    refresh_agenda()
    return ft.ListView([
        ft.Container(content=carousel_row, height=160), 
        ft.Divider(), 
        yt_card, 
        ft.Divider(), 
        ft.Row([ft.Text("Próximos Eventos", weight="bold", size=16), ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color=Config.THEME_COLOR, on_click=add_ev_dialog) if not readonly else ft.Container()], alignment="spaceBetween"), 
        agenda_col
    ], padding=10, spacing=20, expand=True)