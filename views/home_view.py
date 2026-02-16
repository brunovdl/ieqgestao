import flet as ft
import threading
import time
import urllib.parse
from datetime import datetime
from core.config import Config
from utils.helpers import get_latest_video_id, show_success, show_error, show_warning, get_logo, GroqAIService

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
                ref=webview_ref,
                url=embed_url,
                expand=True,
            ),
            width=float("inf"),
            height=250, 
            border_radius=8,
            clip_behavior=ft.ClipBehavior.HARD_EDGE, 
            bgcolor="black"
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

    # --- AGENDA (Para o lado direito do YouTube) ---
    agenda_col = ft.Column([], spacing=8, scroll=ft.ScrollMode.AUTO)
    WEEKDAYS = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}

    # --- DIALOG DE POST DE EVENTO COM IA ---
    def show_event_post_dialog(ev):
        """Gera post de divulgação com IA e exibe dialog para edição e compartilhamento."""
        d_obj = datetime.strptime(ev['event_date'], "%Y-%m-%d")
        t_obj = datetime.strptime(ev['event_time'], "%H:%M:%S")
        date_formatted = f"{WEEKDAYS[d_obj.weekday()]}, {d_obj.strftime('%d/%m/%Y')}"
        time_formatted = t_obj.strftime('%H:%M')
        
        msg_field = ft.TextField(
            label="Post gerado pela IA",
            multiline=True,
            min_lines=5,
            max_lines=10,
            value="Gerando post...",
            read_only=True
        )
        
        btn_share = ft.ElevatedButton(
            "Compartilhar",
            icon=ft.Icons.SHARE,
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
                ft.Text("Post de Divulgação", weight="bold")
            ]),
            content=ft.Container(
                width=450,
                content=ft.Column([
                    ft.Text(f"Evento: {ev['title']}", size=13, color="grey", italic=True),
                    msg_field,
                ], spacing=10)
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.close(dlg)),
                btn_regenerate,
                btn_share,
            ]
        )
        
        def generate_post():
            msg_field.value = "Gerando post..."
            msg_field.read_only = True
            btn_share.disabled = True
            btn_regenerate.disabled = True
            try: page.update()
            except: pass

            message, error = GroqAIService.generate_event_post(
                Config.GROQ_API_KEY, ev['title'], ev.get('description', ''),
                date_formatted, time_formatted, ev.get('location', '')
            )
            
            if message:
                msg_field.value = message
                msg_field.read_only = False
                btn_share.disabled = False
                btn_regenerate.disabled = False
            else:
                msg_field.value = f"Erro ao gerar post: {error}"
                btn_regenerate.disabled = False
            
            try: page.update()
            except: pass
        
        def share_whatsapp(e):
            final_msg = msg_field.value
            if not final_msg or final_msg.startswith("Gerando") or final_msg.startswith("Erro"):
                show_warning(page, "Post inválido!")
                return
            encoded = urllib.parse.quote_plus(final_msg)
            url = f"https://api.whatsapp.com/send?text={encoded}"
            page.close(dlg)
            page.launch_url(url)
        
        btn_share.on_click = share_whatsapp
        btn_regenerate.on_click = lambda e: threading.Thread(target=generate_post, daemon=True).start()
        
        page.open(dlg)
        threading.Thread(target=generate_post, daemon=True).start()

    def refresh_agenda():
        events = db.get_upcoming_events()
        agenda_col.controls.clear()
        if not events: agenda_col.controls.append(ft.Text("Sem eventos próximos.", italic=True, size=13, color="grey"))
        today_str = datetime.now().strftime("%Y-%m-%d")

        for ev in events:
            d_obj = datetime.strptime(ev['event_date'], "%Y-%m-%d")
            t_obj = datetime.strptime(ev['event_time'], "%H:%M:%S")
            line1_text = f"{WEEKDAYS[d_obj.weekday()]} às {t_obj.strftime('%H:%M')}"
            is_today = (ev['event_date'] == today_str)
            
            actions = ft.Container()
            if not readonly:
                actions = ft.Row([
                    ft.IconButton(ft.Icons.AUTO_AWESOME, icon_color="amber", icon_size=16, tooltip="Gerar post com IA", on_click=lambda e, x=ev: show_event_post_dialog(x)),
                    ft.IconButton(ft.Icons.EDIT, icon_color=Config.THEME_COLOR, icon_size=16, tooltip="Editar", on_click=lambda e, x=ev: edit_ev_dialog(x)),
                    ft.IconButton(ft.Icons.DELETE, icon_color="red", icon_size=16, tooltip="Excluir", on_click=lambda e, x=ev['id']: (db.delete_event(x), refresh_agenda(), show_success(page, "Removido!")))
                ], spacing=0, tight=True)
            
            card = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Column([
                            ft.Text(str(d_obj.day), size=18, weight="bold", color="white"),
                            ft.Text(d_obj.strftime("%b").upper(), size=10, color="white")
                        ], alignment="center", spacing=0, horizontal_alignment="center"),
                        bgcolor="green" if is_today else Config.THEME_COLOR,
                        width=45, height=45, border_radius=8,
                        alignment=ft.alignment.center
                    ),
                    ft.Column([
                        ft.Text(ev['title'], weight="bold", size=13, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(line1_text, size=11, color="grey"),
                    ], expand=True, spacing=2),
                    actions
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=ft.padding.symmetric(vertical=4, horizontal=8),
                border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
                border_radius=8,
            )
            agenda_col.controls.append(card)
        try: page.update()
        except: pass

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



    # ==========================
    # DEVOCIONAL DO DIA
    # ==========================
    devotional_data = db.get_today_devotional()

    MESES = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
             7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}

    if devotional_data and devotional_data.get('data'):
        d_obj = datetime.strptime(str(devotional_data['data']), "%Y-%m-%d")
        date_label = f"📅 {d_obj.day} de {MESES[d_obj.month]} de {d_obj.year}"
    else:
        today_now = datetime.now()
        date_label = f"📅 {today_now.day} de {MESES[today_now.month]} de {today_now.year}"

    if devotional_data:
        sections = []
        for field in ['versiculo', 'texto', 'pratica', 'e_voce']:
            val = devotional_data.get(field, '')
            if val:
                sections.append(
                    ft.Container(
                        content=ft.Text(val, size=14, color=ft.colors.with_opacity(0.9, "white")),
                        padding=ft.padding.only(bottom=10),
                    )
                )

        # Estado local do card
        dev_expanded = [False]
        dev_likes = [devotional_data.get('likes', 0) or 0] # Suporta null no DB
        
        dev_content_col = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO)

        def toggle_dev(e):
            dev_expanded[0] = not dev_expanded[0]
            render_dev()
            
        def like_dev(e):
            dev_likes[0] += 1
            e.control.text = str(dev_likes[0])
            e.control.icon = ft.Icons.FAVORITE
            e.control.update()
            # Atualiza no banco em background
            threading.Thread(target=lambda: db.increment_devotional_likes(devotional_data['id']), daemon=True).start()

        def render_dev():
            dev_content_col.controls.clear()
            
            # HEADER (Sempre visível)
            header = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.AUTO_STORIES, color=ft.colors.with_opacity(0.8, "white"), size=24),
                        ft.Text("Devocional do Dia", size=18, weight="bold", color=ft.colors.with_opacity(0.85, "white")),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(date_label, size=12, color=ft.colors.with_opacity(0.5, "white")),
                    ft.Container(height=6),
                    ft.Text(
                        devotional_data.get('titulo', ''),
                        size=17,
                        weight="bold",
                        color="white",
                        italic=True,
                    ),
                ], spacing=3),
                padding=ft.padding.only(bottom=14),
                border=ft.border.only(bottom=ft.BorderSide(1, ft.colors.with_opacity(0.15, "white"))),
            )
            dev_content_col.controls.append(header)
            
            if not dev_expanded[0]:
                # VISÃO RECOLHIDA
                btn_read = ft.ElevatedButton(
                    "Ler Devocional",
                    icon=ft.Icons.MENU_BOOK,
                    style=ft.ButtonStyle(
                        color="white",
                        bgcolor={"": ft.colors.with_opacity(0.1, "white"), "hovered": ft.colors.with_opacity(0.2, "white")},
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=toggle_dev
                )
                dev_content_col.controls.append(ft.Container(btn_read, alignment=ft.alignment.center, padding=ft.padding.symmetric(vertical=15)))
            
            else:
                # VISÃO EXPANDIDA
                dev_content_col.controls.append(ft.Container(height=8))
                dev_content_col.controls.extend(sections)
                
                # Ações (Curtir + Recolher)
                actions = ft.Row([
                    ft.TextButton(
                        text=str(dev_likes[0]),
                        icon=ft.Icons.FAVORITE_BORDER if dev_likes[0] == (devotional_data.get('likes', 0) or 0) else ft.Icons.FAVORITE,
                        icon_color="red",
                        style=ft.ButtonStyle(color="white"),
                        on_click=like_dev,
                        tooltip="Curtir devocional"
                    ),
                    ft.TextButton(
                        "Recolher",
                        icon=ft.Icons.EXPAND_LESS,
                        icon_color=ft.colors.with_opacity(0.5, "white"),
                        style=ft.ButtonStyle(color=ft.colors.with_opacity(0.5, "white")),
                        on_click=toggle_dev
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                
                dev_content_col.controls.append(ft.Container(actions, padding=ft.padding.symmetric(vertical=10)))

                # Rodapé Fixo
                footer = ft.Container(
                    content=ft.Row([
                        get_logo(30),
                        ft.Column([
                            ft.Text("IEQ JD Portugal", size=12, weight="bold", color=ft.colors.with_opacity(0.6, "white")),
                            ft.Text("Av Raphaella Amoroso Micelli, 270", size=10, color=ft.colors.with_opacity(0.4, "white")),
                        ], spacing=1),
                    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.only(top=12),
                    border=ft.border.only(top=ft.BorderSide(1, ft.colors.with_opacity(0.1, "white"))),
                )
                dev_content_col.controls.append(footer)
            
            try: dev_content_col.update()
            except: pass

        # Renderização Inicial
        render_dev()

        devotional_content = ft.Container(
            content=dev_content_col,
            padding=20,
            border_radius=14,
            gradient=ft.LinearGradient(begin=ft.alignment.top_left, end=ft.alignment.bottom_right, colors=["#1e293b", "#334155"]),
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=10, color=ft.colors.with_opacity(0.2, "black"), offset=ft.Offset(0, 3)),
            animate_size=ft.animation.Animation(300, ft.AnimationCurve.EASE_OUT)
        )
    else:
        devotional_content = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.AUTO_STORIES, color=ft.colors.with_opacity(0.4, "white"), size=28),
                    ft.Column([
                        ft.Text("Devocional do Dia", size=18, weight="bold", color=ft.colors.with_opacity(0.6, "white")),
                        ft.Text(date_label, size=11, color=ft.colors.with_opacity(0.35, "white")),
                    ], spacing=2),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(height=8),
                ft.Text("O devocional de hoje ainda não foi publicado.\nVolte mais tarde! 🙏", size=13, color=ft.colors.with_opacity(0.4, "white"), text_align=ft.TextAlign.CENTER, italic=True),
            ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=22, border_radius=14,
            gradient=ft.LinearGradient(begin=ft.alignment.top_left, end=ft.alignment.bottom_right, colors=["#1e293b", "#334155"]),
            alignment=ft.alignment.center,
        )

    # --- ROW: YouTube (esquerda) + Devocional (direita) ---
    is_mobile = (page.width or 800) < 800

    if is_mobile:
        yt_devocional_section = ft.Column([
            devotional_content,
            yt_card,
        ], spacing=10)
    else:
        yt_devocional_section = ft.Row([
            ft.Container(content=devotional_content, expand=1),
            ft.Container(content=yt_card, expand=1),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START)

    # --- LAYOUT FINAL ---
    return ft.ListView([
        ft.Container(content=carousel_row, height=160), 
        ft.Divider(), 
        yt_devocional_section,
        ft.Divider(),
        ft.Row([
            ft.Text("Próximos Eventos", weight="bold", size=16),
            ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color=Config.THEME_COLOR, on_click=add_ev_dialog) if not readonly else ft.Container()
        ], alignment="spaceBetween"),
        agenda_col,
        ft.Container(height=20),
    ], padding=10, spacing=20, expand=True)