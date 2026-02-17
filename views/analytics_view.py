import flet as ft
import threading
from datetime import datetime
from core.config import Config


def analytics_view(page, db, user_state, readonly=False):
    """Dashboard de Analytics — Visualização de acessos ao aplicativo."""

    # ============================
    # ESTADO E DADOS
    # ============================
    period_filter = [30]  # dias
    summary_data = [{}]
    ranking_data = [[]]
    daily_data = [[]]
    user_data = [[]]

    # Refs para atualizar
    cards_row = ft.Row(wrap=True, spacing=12, run_spacing=12, alignment=ft.MainAxisAlignment.CENTER)
    ranking_col = ft.Column(spacing=6)
    daily_col = ft.Column(spacing=4)
    users_col = ft.Column(spacing=6)
    loading_ring = ft.ProgressRing(width=30, height=30, stroke_width=3, color=Config.THEME_COLOR)
    loading_container = ft.Container(content=loading_ring, alignment=ft.alignment.center, height=100)

    MESES = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
             7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}

    # ============================
    # CARDS DE RESUMO
    # ============================
    def build_summary_card(title, value, icon, color):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(icon, color="white", size=20),
                        width=36, height=36, border_radius=8,
                        bgcolor=color, alignment=ft.alignment.center,
                    ),
                    ft.Column([
                        ft.Text(title, size=11, color="grey", weight="w500"),
                        ft.Text(str(value), size=22, weight="bold"),
                    ], spacing=0, expand=True),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=6),
            padding=16, border_radius=12, width=200,
            border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
            bgcolor=ft.colors.SURFACE_VARIANT,
            shadow=ft.BoxShadow(blur_radius=4, color=ft.colors.with_opacity(0.08, "black"), offset=ft.Offset(0, 2)),
        )

    # ============================
    # RANKING DE PÁGINAS
    # ============================
    def build_ranking():
        ranking_col.controls.clear()
        data = ranking_data[0]
        if not data:
            ranking_col.controls.append(ft.Text("Sem dados ainda.", italic=True, color="grey", size=13))
            return

        max_views = data[0]['views'] if data else 1

        PAGE_ICONS = {
            'home': ft.Icons.HOME,
            'celulas': ft.Icons.GROUPS,
            'galeria': ft.Icons.PHOTO_LIBRARY,
            'lista_visitantes': ft.Icons.PEOPLE,
            'carona': ft.Icons.DIRECTIONS_CAR,
            'usuarios': ft.Icons.SECURITY,
            'analytics': ft.Icons.ANALYTICS,
        }

        for i, item in enumerate(data):
            pct = (item['views'] / max_views) if max_views > 0 else 0
            icon = PAGE_ICONS.get(item['page_name'], ft.Icons.WEB)
            label = item.get('page_label') or item['page_name']

            row = ft.Container(
                content=ft.Row([
                    ft.Text(f"{i+1}º", size=12, weight="bold", color="grey", width=28),
                    ft.Icon(icon, size=18, color=Config.THEME_COLOR),
                    ft.Text(label, size=13, weight="w500", expand=True),
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                width=max(pct * 120, 4), height=8,
                                border_radius=4,
                                bgcolor=Config.THEME_COLOR,
                            ),
                        ]),
                        width=130,
                    ),
                    ft.Text(str(item['views']), size=13, weight="bold", width=40, text_align=ft.TextAlign.RIGHT),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=ft.padding.symmetric(vertical=6, horizontal=10),
                border_radius=8,
                bgcolor=ft.colors.SURFACE_VARIANT if i % 2 == 0 else None,
            )
            ranking_col.controls.append(row)

    # ============================
    # ATIVIDADE DIÁRIA
    # ============================
    def build_daily():
        daily_col.controls.clear()
        data = daily_data[0]
        if not data:
            daily_col.controls.append(ft.Text("Sem dados ainda.", italic=True, color="grey", size=13))
            return

        WEEKDAYS = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sáb", 6: "Dom"}
        max_v = max(d['views'] for d in data) if data else 1

        for item in data[:20]:  # últimos 20 dias
            try:
                d_obj = datetime.strptime(item['date'], "%Y-%m-%d")
                day_name = WEEKDAYS[d_obj.weekday()]
                day_label = f"{d_obj.day:02d}/{d_obj.month:02d} ({day_name})"
            except:
                day_label = item['date']

            pct = (item['views'] / max_v) if max_v > 0 else 0

            bar = ft.Container(
                content=ft.Row([
                    ft.Text(day_label, size=12, width=100, color="grey"),
                    ft.Container(
                        content=ft.Container(
                            width=max(pct * 200, 3), height=14,
                            border_radius=4,
                            bgcolor=Config.THEME_COLOR,
                        ),
                        expand=True,
                    ),
                    ft.Text(str(item['views']), size=12, weight="bold", width=35, text_align=ft.TextAlign.RIGHT),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.symmetric(vertical=2),
            )
            daily_col.controls.append(bar)

    # ============================
    # ATIVIDADE POR USUÁRIO
    # ============================
    def build_users():
        users_col.controls.clear()
        data = user_data[0]
        if not data:
            users_col.controls.append(ft.Text("Sem dados ainda.", italic=True, color="grey", size=13))
            return

        max_v = data[0]['views'] if data else 1

        for item in data:
            is_visitor = (item['user'] == 'Visitante')
            pct = (item['views'] / max_v) if max_v > 0 else 0

            row = ft.Container(
                content=ft.Row([
                    ft.CircleAvatar(
                        content=ft.Text(item['user'][0].upper(), size=14, weight="bold", color="white"),
                        bgcolor="grey" if is_visitor else Config.THEME_COLOR,
                        radius=16,
                    ),
                    ft.Text(item['user'], size=13, weight="w500", expand=True),
                    ft.Container(
                        content=ft.Container(
                            width=max(pct * 100, 3), height=8,
                            border_radius=4,
                            bgcolor="grey" if is_visitor else Config.THEME_COLOR,
                        ),
                        width=110,
                    ),
                    ft.Text(str(item['views']), size=13, weight="bold", width=40, text_align=ft.TextAlign.RIGHT),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                padding=ft.padding.symmetric(vertical=5, horizontal=10),
                border_radius=8,
                bgcolor=ft.colors.SURFACE_VARIANT if data.index(item) % 2 == 0 else None,
            )
            users_col.controls.append(row)

    # ============================
    # CARREGAMENTO GERAL
    # ============================
    main_content = ft.Column(spacing=16)

    def load_data():
        try:
            summary_data[0] = db.get_analytics_summary()
            ranking_data[0] = db.get_page_ranking(period_filter[0])
            daily_data[0] = db.get_daily_views(period_filter[0])
            user_data[0] = db.get_user_activity(period_filter[0])
        except:
            pass

        # Monta os cards
        s = summary_data[0]
        cards_row.controls = [
            build_summary_card("Hoje", s.get('today', 0), ft.Icons.TODAY, "#4CAF50"),
            build_summary_card("7 Dias", s.get('week', 0), ft.Icons.DATE_RANGE, "#2196F3"),
            build_summary_card("30 Dias", s.get('month', 0), ft.Icons.CALENDAR_MONTH, "#FF9800"),
            build_summary_card("Total", s.get('total', 0), ft.Icons.ALL_INCLUSIVE, "#9C27B0"),
        ]

        build_ranking()
        build_daily()
        build_users()

        # Monta layout final
        is_mobile = (page.width or 800) < 800

        main_content.controls.clear()
        main_content.controls.append(cards_row)

        if is_mobile:
            main_content.controls.extend([
                _section("📊 Páginas Mais Acessadas", ranking_col),
                _section("📅 Acessos por Dia", daily_col),
                _section("👥 Atividade por Usuário", users_col),
            ])
        else:
            main_content.controls.append(
                ft.Row([
                    ft.Container(content=_section("📊 Páginas Mais Acessadas", ranking_col), expand=1),
                    ft.Container(content=_section("👥 Atividade por Usuário", users_col), expand=1),
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START)
            )
            main_content.controls.append(_section("📅 Acessos por Dia", daily_col))

        try:
            loading_container.visible = False
            page.update()
        except:
            pass

    def _section(title, content_col):
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=16, weight="bold"),
                ft.Divider(height=1, thickness=1),
                content_col,
            ], spacing=8),
            padding=16,
            border_radius=12,
            border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
            bgcolor=ft.colors.SURFACE_VARIANT,
        )

    def refresh(e=None):
        loading_container.visible = True
        try: page.update()
        except: pass
        threading.Thread(target=load_data, daemon=True).start()

    # Header com botão de refresh
    header = ft.Row([
        ft.Row([
            ft.Icon(ft.Icons.ANALYTICS, color=Config.THEME_COLOR, size=28),
            ft.Text("Analytics de Acessos", size=20, weight="bold"),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.IconButton(ft.Icons.REFRESH, icon_color=Config.THEME_COLOR, tooltip="Atualizar", on_click=refresh),
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # Inicia carregamento
    refresh()

    return ft.ListView([
        header,
        loading_container,
        main_content,
        ft.Container(height=20),
    ], padding=15, spacing=12, expand=True)
