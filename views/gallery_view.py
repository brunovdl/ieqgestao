import flet as ft
from datetime import datetime
import uuid
import os
import asyncio
import glob
from core.config import Config
from utils.helpers import show_success, show_error, show_warning, show_loading, hide_loading

def gallery_view(page, db, user_state, readonly=False):
    current_view = ft.Ref[ft.Column]()
    selected_album = {'id': None}
    
    # --- LISTAGEM DE ÁLBUNS ---
    def show_albums_list(e=None):
        albums = db.get_all_albums()
        cards = []
        
        if not albums:
            cards.append(ft.Container(content=ft.Column([ft.Icon(ft.Icons.PHOTO_ALBUM, size=64, color="grey"), ft.Text("Nenhum álbum.", color="grey")]), padding=40))
        else:
            for album in albums:
                photos = db.get_photos_by_album(album['id'])
                # Capa do álbum
                cover_content = ft.Container(bgcolor="#263238", content=ft.Icon(ft.Icons.PHOTO_LIBRARY, color="white30"))
                if photos:
                    cover_content = ft.Image(src=db.get_photo_url(photos[0]['storage_path']), fit="cover", width=float("inf"), height=float("inf"))

                date_str = datetime.fromisoformat(str(album['event_date'])).strftime("%d/%m/%Y") if album.get('event_date') else ""
                
                cards.append(ft.Card(elevation=4, clip_behavior=ft.ClipBehavior.HARD_EDGE, content=ft.Container(
                    on_click=lambda e, aid=album['id']: show_album_photos(aid), ink=True, height=200, 
                    content=ft.Stack([
                        cover_content,
                        ft.Container(alignment=ft.alignment.bottom_left, gradient=ft.LinearGradient(begin=ft.alignment.top_center, end=ft.alignment.bottom_center, colors=[ft.colors.TRANSPARENT, ft.colors.BLACK87], stops=[0.0, 0.8]), padding=ft.padding.only(left=12, right=8, bottom=8, top=40), content=ft.Column([
                            ft.Text(album['name'], weight="bold", size=16, color="white"),
                            ft.Row([ft.Text(f"{len(photos)} fotos • {date_str}", size=12, color="white70"), ft.Container(expand=True), ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="white", icon_size=18, on_click=lambda e, aid=album['id'], nm=album['name']: confirm_delete_album(aid, nm), visible=not readonly)])
                        ], spacing=2))
                    ])
                )))
        
        current_view.current.controls = [
            ft.Row([ft.Text("Galeria", size=24, weight="bold"), ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color=Config.THEME_COLOR, icon_size=40, on_click=show_create_album_form, visible=not readonly)], alignment="spaceBetween"), 
            ft.Divider(), 
            ft.GridView(controls=cards, runs_count=2, child_aspect_ratio=0.85, spacing=10, run_spacing=10, expand=True)
        ]
        page.update()

    # --- VISUALIZAÇÃO DE FOTOS ---
    def show_album_photos(album_id):
        selected_album['id'] = album_id
        album = db.get_album_by_id(album_id)
        photos = db.get_photos_by_album(album_id)
        
        # Lista local para lightbox
        current_album_photos_list = photos 
        widgets = []
        
        for index, photo in enumerate(photos):
            url = db.get_photo_url(photo['storage_path'])
            widgets.append(ft.Card(elevation=2, clip_behavior=ft.ClipBehavior.HARD_EDGE, content=ft.Container(
                on_click=lambda e, idx=index: open_lightbox(idx, current_album_photos_list), ink=True, 
                content=ft.Stack([
                    ft.Image(src=url, fit="cover", width=float("inf"), height=float("inf")),
                    ft.Container(alignment=ft.alignment.bottom_right, gradient=ft.LinearGradient(colors=[ft.colors.TRANSPARENT, ft.colors.BLACK54]), padding=5, content=ft.Row([
                        ft.IconButton(ft.Icons.DOWNLOAD_ROUNDED, icon_color="white", icon_size=20, on_click=lambda e, u=url: page.launch_url(u)),
                        ft.IconButton(ft.Icons.DELETE_ROUNDED, icon_color="red", icon_size=20, on_click=lambda e, pid=photo['id']: delete_photo(pid), visible=not readonly)
                    ], alignment="end", spacing=0))
                ])
            )))

        current_view.current.controls = [ft.Column([
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=show_albums_list), ft.Text(album['name'], size=20, weight="bold", expand=True), ft.IconButton(ft.Icons.ADD_A_PHOTO, icon_color=Config.THEME_COLOR, on_click=lambda e: show_upload_form(album_id), visible=not readonly)]),
            ft.Text(album.get('description', ''), size=12, color="grey"), ft.Divider(height=1),
            ft.GridView(controls=widgets, runs_count=3, child_aspect_ratio=1.0, spacing=5, run_spacing=5, expand=True)
        ], expand=True)]
        page.update()

    # --- UPLOAD REAL (Restaurado do gallery_module.py) ---
    def show_upload_form(album_id):
        desc_tf = ft.TextField(label="Descrição (Opcional)")
        info_txt = ft.Text("Selecione fotos...", color="grey")
        prog_bar = ft.ProgressBar(visible=False)
        btn_upload = ft.Ref[ft.ElevatedButton]()
        
        files_state = {'files': []}
        
        # Lógica de seleção
        def on_file_result(e: ft.FilePickerResultEvent):
            if e.files:
                files_state['files'] = e.files
                info_txt.value = f"{len(e.files)} arquivo(s) selecionado(s)"
                btn_upload.current.disabled = False
            page.update()

        picker = ft.FilePicker(on_result=on_file_result)
        page.overlay.append(picker)
        page.update()

        # TAREFA DE UPLOAD ASSÍNCRONA
        async def upload_task(desc):
            if not files_state['files']: return
            
            btn_upload.current.disabled = True
            prog_bar.visible = True
            page.update()
            
            files = files_state['files']
            to_process = []
            need_upload = []

            # Separa o que precisa de upload (Web) do que já tem path (Desktop)
            for f in files:
                if f.path: 
                    to_process.append({'obj': f, 'path': f.path, 'temp': False})
                else: 
                    need_upload.append(f)
            
            # Lógica específica para WEB (FilePickerUploadFile)
            if need_upload:
                # Garante diretório temporário
                os.makedirs("temp_uploads", exist_ok=True)
                before_files = set(glob.glob("temp_uploads/*"))
                
                objs = []
                for f in need_upload:
                    # Gera URL assinada para upload interno do Flet
                    url = page.get_upload_url(f.name, 600)
                    objs.append(ft.FilePickerUploadFile(f.name, upload_url=url))
                
                # Dispara o upload do navegador para o servidor python
                picker.upload(objs)
                
                # Aguarda (Simples wait, idealmente usaria eventos mas wait funciona para scripts simples)
                await asyncio.sleep(2.0) 
                
                after_files = set(glob.glob("temp_uploads/*"))
                new_files = list(after_files - before_files)
                
                for nf in new_files:
                    # Cria objeto mock para manter compatibilidade
                    f_mock = type('obj', (object,), {'name': os.path.basename(nf)})
                    to_process.append({'obj': f_mock, 'path': nf, 'temp': True})

            # Processamento Final (Envio para Supabase)
            count = 0
            total = len(to_process)
            
            for i, item in enumerate(to_process):
                f = item['obj']
                path = item['path']
                try:
                    info_txt.value = f"Enviando {i+1}/{total}: {f.name}"
                    prog_bar.value = (i / total)
                    page.update()
                    
                    # Leitura binária
                    with open(path, 'rb') as fo:
                        file_bytes = fo.read()
                    
                    # Upload para Supabase
                    res = db.upload_photo_to_storage(file_bytes, f.name, album_id)
                    
                    if res:
                        # Registro no Banco
                        user_name = user_state.get('user', 'Desconhecido')
                        db.add_photo(album_id, f.name, res['public_url'], res['storage_path'], desc, user_name, len(file_bytes))
                        count += 1
                        
                        # Limpeza se for arquivo temporário
                        if item['temp']: 
                            try: os.remove(path)
                            except: pass
                except Exception as ex:
                    print(f"Erro Upload {f.name}: {ex}")

            prog_bar.visible = False
            if count > 0:
                show_success(page, f"{count} fotos enviadas!")
                show_album_photos(album_id)
            else:
                show_error(page, "Falha no upload.")
                btn_upload.current.disabled = False
                page.update()

        btn_select = ft.ElevatedButton("Selecionar Fotos", icon=ft.Icons.IMAGE, on_click=lambda e: picker.pick_files(allow_multiple=True))
        btn_upload.current = ft.ElevatedButton("Enviar", icon=ft.Icons.UPLOAD, disabled=True, on_click=lambda e: page.run_task(upload_task, desc_tf.value))

        current_view.current.controls = [ft.Column([
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: show_album_photos(album_id)), ft.Text("Upload de Fotos", size=20)]),
            desc_tf,
            btn_select,
            info_txt,
            prog_bar,
            btn_upload.current
        ])]
        page.update()

    # --- LIGHTBOX (Auxiliar) ---
    def open_lightbox(idx, photos_list):
        current_idx = [idx]
        img_ref = ft.Ref[ft.Image]()
        
        def move(delta):
            new_idx = current_idx[0] + delta
            if 0 <= new_idx < len(photos_list):
                current_idx[0] = new_idx
                img_ref.current.src = db.get_photo_url(photos_list[new_idx]['storage_path'])
                img_ref.current.update()

        stack = ft.Stack([
            ft.Container(bgcolor="black", opacity=0.95, on_click=lambda e: close_lightbox(stack), width=page.width, height=page.height),
            ft.Container(content=ft.Image(ref=img_ref, src=db.get_photo_url(photos_list[idx]['storage_path']), fit="contain", width=page.width, height=page.height), alignment=ft.alignment.center),
            ft.Container(content=ft.IconButton(ft.Icons.CLOSE, icon_color="white", icon_size=30, on_click=lambda e: close_lightbox(stack)), top=10, right=10),
            ft.Container(content=ft.IconButton(ft.Icons.ARROW_BACK_IOS, icon_color="white", on_click=lambda e: move(-1)), left=10, top=page.height/2-25),
            ft.Container(content=ft.IconButton(ft.Icons.ARROW_FORWARD_IOS, icon_color="white", on_click=lambda e: move(1)), right=10, top=page.height/2-25)
        ], width=page.width, height=page.height)
        page.overlay.append(stack); page.update()

    def close_lightbox(stack):
        page.overlay.remove(stack); page.update()

    # --- AUXILIARES (Deletar, Criar Álbum) ---
    def confirm_delete_album(aid, name):
        dlg = ft.AlertDialog(title=ft.Text("Confirmar"), content=ft.Text(f"Apagar '{name}'?"), actions=[ft.TextButton("Cancelar", on_click=lambda e: page.close(dlg)), ft.TextButton("Apagar", on_click=lambda e: (db.delete_album(aid), page.close(dlg), show_albums_list()), style=ft.ButtonStyle(color="red"))]); page.open(dlg)
    
    def delete_photo(pid):
        def on_del(e):
            page.close(dlg)
            if db.delete_photo(pid): show_success(page, "Foto apagada!"); show_album_photos(selected_album['id'])
        dlg = ft.AlertDialog(title=ft.Text("Apagar Foto"), content=ft.Text("Confirmar?"), actions=[ft.TextButton("Não", on_click=lambda e: page.close(dlg)), ft.TextButton("Sim", on_click=on_del, style=ft.ButtonStyle(color="red"))]); page.open(dlg)

    def show_create_album_form(e=None):
        name_tf, desc_tf = ft.TextField(label="Nome"), ft.TextField(label="Descrição")
        dt_val = ft.TextField(label="Data (DD/MM/AAAA)", value=datetime.now().strftime("%d/%m/%Y"), read_only=True)
        dp = ft.DatePicker(on_change=lambda e: (setattr(dt_val, 'value', e.control.value.strftime("%d/%m/%Y")), dt_val.update()))
        page.overlay.append(dp); page.update()
        
        def save(e):
            try: dt_iso = datetime.strptime(dt_val.value, "%d/%m/%Y").strftime("%Y-%m-%d")
            except: dt_iso = datetime.now().strftime("%Y-%m-%d")
            if db.create_album(name_tf.value, desc_tf.value, dt_iso, user_state.get('user', '?')): show_success(page, "Álbum criado!"); show_albums_list()
        
        current_view.current.controls = [ft.Column([ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=show_albums_list), ft.Text("Novo Álbum")]), name_tf, desc_tf, ft.Row([dt_val, ft.IconButton(ft.Icons.CALENDAR_MONTH, on_click=lambda _: dp.pick_date())]), ft.ElevatedButton("Salvar", on_click=save)])]; page.update()

    col = ft.Column(expand=True, ref=current_view); show_albums_list(); return col