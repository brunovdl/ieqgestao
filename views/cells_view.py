import flet as ft
import urllib.parse
from core.config import Config
from utils.helpers import show_success, show_error, show_warning, address_form_fields

def cells_view(page, db, readonly=False):
    view = ft.Ref[ft.Column]()
    
    filter_dd = ft.Dropdown(width=120, text_size=13, options=[ft.dropdown.Option("Todas"), ft.dropdown.Option("Ativas"), ft.dropdown.Option("Inativas")], value="Todas", on_change=lambda e: show_list(), visible=not readonly)
    
    def confirm_delete(cid, cname):
        dlg = ft.AlertDialog(title=ft.Text("Exclusão Permanente"), content=ft.Text(f"Apagar '{cname}'?"), actions=[ft.TextButton("Cancelar", on_click=lambda e: page.close(dlg)), ft.TextButton("Apagar", on_click=lambda e: (db.delete_cell_permanent(cid), page.close(dlg), show_success(page, "Apagado!"), show_list()), style=ft.ButtonStyle(color="red"))]); page.open(dlg)

    def show_list():
        items = db.get_all_cells()
        current = "Ativas" if readonly else filter_dd.value
        filtered = [c for c in items if (current=="Todas") or (current=="Ativas" and c[8]) or (current=="Inativas" and not c[8])]
        
        if not filtered: content = ft.Text("Nenhum registro.", color="grey")
        else:
            cards = []
            for c in filtered:
                cid, cname, cleader, chost, addr, day, time, obs, active = c
                bg = Config.THEME_COLOR if active else "grey"
                
                admin_acts = ft.Container()
                if not readonly:
                    if active: admin_acts = ft.IconButton(ft.Icons.DELETE, icon_color="red", tooltip="Desativar", on_click=lambda e, x=cid: (db.deactivate_cell(x), show_list()))
                    else: admin_acts = ft.Row([ft.IconButton(ft.Icons.RESTORE, icon_color="green", on_click=lambda e, x=cid: (db.activate_cell(x), show_list())), ft.IconButton(ft.Icons.DELETE_FOREVER, icon_color="red", on_click=lambda e, x=cid, n=cname: confirm_delete(x, n))])

                cards.append(ft.Card(content=ft.Container(content=ft.Column([
                    ft.Container(content=ft.Column([ft.Icon(ft.Icons.HOME_FILLED if active else ft.Icons.HOME_WORK_OUTLINED, size=40, color="white"), ft.Text(day.upper(), weight="bold", color="white", size=12), ft.Text(time, weight="bold", color="white", size=20)], horizontal_alignment="center", spacing=2), bgcolor=bg, height=130, alignment=ft.alignment.center, border_radius=ft.border_radius.only(top_left=10, top_right=10)),
                    ft.Container(content=ft.Column([
                        ft.Text(cname, weight="bold", size=18, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Row([ft.Icon(ft.Icons.PERSON, size=16), ft.Text(f"Líder: {cleader}", size=13, expand=True)]),
                        ft.Row([ft.Icon(ft.Icons.REAL_ESTATE_AGENT, size=16), ft.Text(f"Anfitrião: {chost}", size=13, expand=True)]),
                        ft.Divider(),
                        ft.Row([ft.ElevatedButton("Mapa", icon=ft.Icons.MAP, bgcolor="green", color="white", on_click=lambda e, a=addr: page.launch_url(f"http://maps.google.com/?q={urllib.parse.quote(a)}"), visible=bool(addr)), admin_acts], alignment="spaceBetween")
                    ], spacing=5), padding=15)
                ], spacing=0), opacity=1.0 if active else 0.8), col={"sm": 12, "md": 6, "lg": 4}, elevation=4))
            content = ft.ResponsiveRow(cards)

        view.current.controls = [ft.Row([filter_dd, ft.IconButton(ft.Icons.ADD, on_click=show_form, bgcolor=Config.THEME_COLOR, icon_color="white") if not readonly else ft.Container()], alignment="end"), ft.Divider(), ft.Column([content], scroll="auto", expand=True)]
        page.update()

    def show_form(e):
        h = ft.TextField(label="Anfitrião *", col={"sm":12,"md":6})
        l = ft.TextField(label="Líder *", col={"sm":12,"md":6})
        t = ft.TextField(label="Horário", col={"sm":12,"md":6})
        o = ft.TextField(label="Obs", multiline=True, col=12)
        d = ft.Dropdown(label="Dia", options=[ft.dropdown.Option(x) for x in ["Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira","Sexta-feira","Sábado","Domingo"]], col={"sm":12,"md":6})
        addr = address_form_fields(page)

        def save(e):
            if not l.value or not h.value: show_warning(page, "Preencha Líder e Anfitrião!"); return
            if db.add_cell(f"Casa de {h.value}", l.value, h.value, addr["get_full_address"](), d.value, t.value, o.value): show_success(page, "Salvo!"); show_list()
            else: show_error(page, "Erro.")

        view.current.controls = [ft.Column([ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: show_list()), ft.Text("Nova Casa", size=20)]), ft.Divider(), ft.ResponsiveRow([h, l, d, t]), ft.Text("Endereço", weight="bold"), addr["ui"], ft.Divider(), ft.ResponsiveRow([o]), ft.Button("Salvar", on_click=save, style=ft.ButtonStyle(bgcolor=Config.THEME_COLOR, color="white"))], scroll="auto", expand=True)]; page.update()

    col = ft.Column(expand=True, ref=view); show_list(); return col