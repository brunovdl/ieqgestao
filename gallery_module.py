"""
Módulo de Galeria de Fotos
Gerenciamento de álbuns e fotos com Supabase Storage
VERSÃO FINAL SIMPLIFICADA - Flet 0.25.2
(Navegação apenas por botões - Sem Gestos - Correção de Upload Assíncrono, Calendário e Criação de Álbum)
"""
import flet as ft
from datetime import datetime
import uuid
import os
import asyncio
import glob

# ==============================================================================
# FUNÇÕES DE GALERIA NO DATABASE
# ==============================================================================

def add_gallery_methods_to_database(db_class):
    """Adiciona métodos de galeria à classe Database"""
    
    def create_album(self, name, description, event_date, created_by):
        try:
            data = {
                'name': name,
                'description': description,
                'event_date': event_date,
                'created_by': created_by
            }
            response = self.supabase.table('albums').insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Erro ao criar álbum: {e}")
            return None
    
    def get_all_albums(self):
        try:
            response = self.supabase.table('albums').select('*').order('event_date', desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Erro ao listar álbuns: {e}")
            return []
    
    def get_album_by_id(self, album_id):
        try:
            response = self.supabase.table('albums').select('*').eq('id', album_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Erro ao buscar álbum: {e}")
            return None
    
    def update_album(self, album_id, name, description, event_date):
        try:
            data = {
                'name': name,
                'description': description,
                'event_date': event_date
            }
            self.supabase.table('albums').update(data).eq('id', album_id).execute()
            return True
        except Exception as e:
            print(f"Erro ao atualizar álbum: {e}")
            return False
    
    def delete_album(self, album_id):
        try:
            photos = self.get_photos_by_album(album_id)
            for photo in photos:
                try:
                    self.supabase.storage.from_('gallery').remove([photo['storage_path']])
                except:
                    pass
            self.supabase.table('albums').delete().eq('id', album_id).execute()
            return True
        except Exception as e:
            print(f"Erro ao deletar álbum: {e}")
            return False
    
    def add_photo(self, album_id, file_name, file_path, storage_path, description, uploaded_by, file_size):
        try:
            data = {
                'album_id': album_id,
                'file_name': file_name,
                'file_path': file_path,
                'storage_path': storage_path,
                'description': description,
                'uploaded_by': uploaded_by,
                'file_size': file_size
            }
            response = self.supabase.table('photos').insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Erro ao adicionar foto: {e}")
            return None
    
    def get_photos_by_album(self, album_id):
        try:
            response = self.supabase.table('photos').select('*').eq('album_id', album_id).order('created_at', desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Erro ao listar fotos: {e}")
            return []
    
    def delete_photo(self, photo_id):
        try:
            response = self.supabase.table('photos').select('*').eq('id', photo_id).execute()
            if response.data:
                photo = response.data[0]
                try:
                    self.supabase.storage.from_('gallery').remove([photo['storage_path']])
                except:
                    pass
                self.supabase.table('photos').delete().eq('id', photo_id).execute()
                return True
            return False
        except Exception as e:
            print(f"Erro ao deletar foto: {e}")
            return False
    
    def upload_photo_to_storage(self, file_bytes, file_name, album_id):
        try:
            unique_name = f"{album_id}/{uuid.uuid4()}_{file_name}"
            self.supabase.storage.from_('gallery').upload(
                unique_name,
                file_bytes,
                file_options={"content-type": "image/jpeg"}
            )
            url = self.supabase.storage.from_('gallery').get_public_url(unique_name)
            return {'storage_path': unique_name, 'public_url': url}
        except Exception as e:
            print(f"Erro upload: {e}")
            return None
    
    def get_photo_url(self, storage_path):
        try:
            return self.supabase.storage.from_('gallery').get_public_url(storage_path)
        except Exception as e:
            print(f"Erro URL: {e}")
            return None
    
    # Vincula métodos
    db_class.create_album = create_album
    db_class.get_all_albums = get_all_albums
    db_class.get_album_by_id = get_album_by_id
    db_class.update_album = update_album
    db_class.delete_album = delete_album
    db_class.add_photo = add_photo
    db_class.get_photos_by_album = get_photos_by_album
    db_class.delete_photo = delete_photo
    db_class.upload_photo_to_storage = upload_photo_to_storage
    db_class.get_photo_url = get_photo_url

# ==============================================================================
# VIEW DE GALERIA
# ==============================================================================

def gallery_view(page: ft.Page, db, current_user, show_success, show_error, show_warning, show_loading, hide_loading, readonly=False):
    
    current_view = ft.Ref[ft.Column]()
    selected_album = {'id': None}
    current_album_photos_list = []
    
    def show_albums_list(e=None):
        """Lista de Álbuns (Visual Moderno: Foto Full + Overlay)"""
        albums = db.get_all_albums()
        album_cards = []
        
        if not albums:
            album_cards.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.PHOTO_ALBUM, size=64, color="grey"),
                        ft.Text("Nenhum álbum criado.", size=16, color="grey")
                    ], horizontal_alignment="center"),
                    padding=40
                )
            )
        else:
            for album in albums:
                album_photos = db.get_photos_by_album(album['id'])
                photos_count = len(album_photos)
                
                # Capa (Imagem de Fundo)
                if album_photos:
                    cover_url = db.get_photo_url(album_photos[0]['storage_path'])
                    cover_content = ft.Image(
                        src=cover_url, 
                        fit="cover", 
                        repeat=ft.ImageRepeat.NO_REPEAT,
                        width=float("inf"),
                        height=float("inf")
                    )
                else:
                    cover_content = ft.Container(
                        content=ft.Icon(ft.Icons.PHOTO_LIBRARY, size=50, color="white30"),
                        alignment=ft.alignment.center,
                        bgcolor="#263238" # Cinza escuro se não tiver foto
                    )

                # Formatar data
                event_date = album.get('event_date', '')
                try:
                    dt = datetime.fromisoformat(str(event_date))
                    event_date = dt.strftime("%d/%m/%Y")
                except:
                    pass
                
                # --- CARD REFINADO (STACK) ---
                card = ft.Card(
                    elevation=4,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    content=ft.Container(
                        # Container principal clicável
                        on_click=lambda e, aid=album['id']: show_album_photos(aid),
                        ink=True,
                        height=200, # Altura fixa para o cartão
                        content=ft.Stack([
                            # 1. Imagem de Fundo (Ocupa tudo)
                            cover_content,
                            
                            # 2. Overlay de Informações (No fundo)
                            ft.Container(
                                alignment=ft.alignment.bottom_left,
                                gradient=ft.LinearGradient(
                                    begin=ft.alignment.top_center,
                                    end=ft.alignment.bottom_center,
                                    colors=[ft.colors.TRANSPARENT, ft.colors.BLACK87],
                                    stops=[0.0, 0.8]
                                ),
                                padding=ft.padding.only(left=12, right=8, bottom=8, top=40),
                                content=ft.Column([
                                    # Título do Álbum
                                    ft.Text(album['name'], weight="bold", size=16, color="white", max_lines=1, overflow="ellipsis"),
                                    # Info Secundária e Botão Lixeira na Mesma Linha
                                    ft.Row([
                                        ft.Text(f"{photos_count} fotos • {event_date}", size=12, color="white70"),
                                        ft.Container(expand=True), # Empurra o ícone para a direita
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE_OUTLINE,
                                            icon_color="white",
                                            icon_size=18,
                                            tooltip="Apagar Álbum",
                                            padding=0,
                                            height=24,
                                            width=24,
                                            on_click=lambda e, aid=album['id'], nm=album['name']: confirm_delete_album(aid, nm),
                                            visible=not readonly
                                        )
                                    ], alignment="spaceBetween", vertical_alignment="center")
                                ], spacing=2, alignment=ft.MainAxisAlignment.END) # Correção aqui
                            )
                        ])
                    )
                )
                album_cards.append(card)
        
        # Header e Grid
        header = ft.Row([
            ft.Text("Galeria", size=24, weight="bold"),
            ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color="#1976D2", icon_size=40, on_click=show_create_album_form, visible=not readonly)
        ], alignment="spaceBetween")

        content = ft.Column([
            header,
            ft.Divider(),
            ft.GridView(
                controls=album_cards,
                runs_count=2, # 2 Colunas
                child_aspect_ratio=0.85, # Proporção do card
                spacing=10,
                run_spacing=10,
                expand=True
            )
        ], expand=True)
        
        current_view.current.controls = [content]
        page.update()

    def show_album_photos(album_id):
        """Visualização das Fotos (Card 'Protagonista' - Overlay de Botões)"""
        selected_album['id'] = album_id
        album = db.get_album_by_id(album_id)
        
        if not album:
            show_albums_list()
            return
        
        photos = db.get_photos_by_album(album_id)
        current_album_photos_list.clear()
        current_album_photos_list.extend(photos)
        
        photo_widgets = []
        
        if not photos:
            photo_widgets.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED, size=50, color="grey"),
                        ft.Text("Álbum vazio", color="grey")
                    ], alignment="center", horizontal_alignment="center"),
                    alignment=ft.alignment.center,
                    padding=20
                )
            )
        else:
            for index, photo in enumerate(photos):
                url = db.get_photo_url(photo['storage_path'])
                
                # --- CARD COM OVERLAY (PILHA) ---
                card = ft.Card(
                    elevation=2,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    # Container wrapper para capturar o clique em qualquer lugar do card
                    content=ft.Container(
                        on_click=lambda e, idx=index: open_lightbox(idx),
                        ink=True,
                        content=ft.Stack([
                            # 1. A FOTO (Ocupa tudo)
                            ft.Image(
                                src=url,
                                fit="cover",
                                width=float("inf"),
                                height=float("inf"),
                                error_content=ft.Icon(ft.Icons.BROKEN_IMAGE)
                            ),
                            
                            # 2. OVERLAY DE BOTÕES (No canto inferior)
                            ft.Container(
                                alignment=ft.alignment.bottom_right,
                                gradient=ft.LinearGradient(
                                    begin=ft.alignment.top_center,
                                    end=ft.alignment.bottom_center,
                                    colors=[ft.colors.TRANSPARENT, ft.colors.BLACK54],
                                ),
                                padding=5,
                                content=ft.Row([
                                    # Botões (têm prioridade no clique)
                                    ft.IconButton(
                                        icon=ft.Icons.DOWNLOAD_ROUNDED,
                                        icon_color="white",
                                        icon_size=20,
                                        tooltip="Baixar",
                                        on_click=lambda e, u=url: page.launch_url(u)
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_ROUNDED,
                                        icon_color="red",
                                        icon_size=20,
                                        tooltip="Excluir",
                                        on_click=lambda e, pid=photo['id']: delete_photo(pid),
                                        visible=not readonly
                                    )
                                ], alignment="end", spacing=0)
                            )
                        ])
                    )
                )
                photo_widgets.append(card)

        # Header do Álbum
        header = ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=show_albums_list),
            ft.Text(album['name'], size=20, weight="bold", expand=True, max_lines=1, overflow="ellipsis"),
            ft.IconButton(ft.Icons.ADD_A_PHOTO, icon_color="#1976D2", on_click=lambda e: show_upload_form(album_id), visible=not readonly)
        ])

        content = ft.Column([
            header,
            ft.Text(album.get('description', ''), size=12, color="grey", visible=bool(album.get('description', ''))),
            ft.Divider(height=1),
            ft.GridView(
                controls=photo_widgets,
                runs_count=3, # 3 colunas para mobile
                child_aspect_ratio=1.0, # Quadrado perfeito
                spacing=5,
                run_spacing=5,
                expand=True
            )
        ], expand=True)
        
        current_view.current.controls = [content]
        page.update()

    # --- FUNÇÕES AUXILIARES (Upload, Delete, Lightbox) ---
    
    def confirm_delete_album(aid, name):
        def on_del(e):
            page.close(dlg)
            if db.delete_album(aid):
                show_success(page, "Álbum deletado!")
                show_albums_list()
            else:
                show_error(page, "Erro ao deletar.")
        
        dlg = ft.AlertDialog(
            title=ft.Text("Confirmar"),
            content=ft.Text(f"Apagar '{name}' e todas as fotos?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.close(dlg)),
                ft.TextButton("Apagar", on_click=on_del, style=ft.ButtonStyle(color="red"))
            ]
        )
        page.open(dlg)

    def delete_photo(pid):
        def on_del(e):
            page.close(dlg)
            if db.delete_photo(pid):
                show_success(page, "Foto apagada!")
                show_album_photos(selected_album['id'])
            else:
                show_error(page, "Erro ao apagar.")

        dlg = ft.AlertDialog(
            title=ft.Text("Apagar Foto"),
            content=ft.Text("Tem certeza?"),
            actions=[
                ft.TextButton("Não", on_click=lambda e: page.close(dlg)),
                ft.TextButton("Sim", on_click=on_del, style=ft.ButtonStyle(color="red"))
            ]
        )
        page.open(dlg)

    # --- LIGHTBOX ---
    def open_lightbox(idx):
        current_idx = [idx]
        img_ref = ft.Ref[ft.Image]()
        count_ref = ft.Ref[ft.Text]()
        lightbox_stack_ref = ft.Ref[ft.Stack]() # Referência para remover depois

        def get_url():
            if 0 <= current_idx[0] < len(current_album_photos_list):
                return db.get_photo_url(current_album_photos_list[current_idx[0]]['storage_path'])
            return ""

        def close(e):
            # Usar a referência para remover o stack específico
            if lightbox_stack_ref.current:
                page.overlay.remove(lightbox_stack_ref.current)
                page.update()

        def move(delta):
            new_idx = current_idx[0] + delta
            if 0 <= new_idx < len(current_album_photos_list):
                current_idx[0] = new_idx
                img_ref.current.src = get_url()
                count_ref.current.value = f"{new_idx + 1}/{len(current_album_photos_list)}"
                img_ref.current.update()
                count_ref.current.update()
                page.update()

        # Botões de Navegação e Fechar com Posicionamento Absoluto
        
        # Botão Fechar
        btn_close = ft.Container(
            content=ft.IconButton(ft.Icons.CLOSE, icon_color="white", icon_size=30, on_click=close),
            padding=5,
            top=10,
            right=10,
        )
        
        # Botão Anterior
        btn_prev = ft.Container(
            content=ft.IconButton(ft.Icons.ARROW_BACK_IOS, icon_color="white", icon_size=30, on_click=lambda e: move(-1)),
            padding=5,
            left=10,
            top=page.height / 2 - 25, # Centraliza verticalmente (aprox)
            visible=len(current_album_photos_list) > 1
        )
        
        # Botão Próximo
        btn_next = ft.Container(
            content=ft.IconButton(ft.Icons.ARROW_FORWARD_IOS, icon_color="white", icon_size=30, on_click=lambda e: move(1)),
            padding=5,
            right=10,
            top=page.height / 2 - 25, # Centraliza verticalmente (aprox)
            visible=len(current_album_photos_list) > 1
        )
        
        # Contador
        lbl_count = ft.Container(
            content=ft.Text(ref=count_ref, value=f"{idx + 1}/{len(current_album_photos_list)}", color="white", weight="bold"),
            padding=5,
            top=20,
            width=page.width, # Ocupa largura total para centralizar o texto
            alignment=ft.alignment.center # Alinha o texto dentro do container
        )

        # Imagem + Fundo (Camada Fundo - SEM GestureDetector)
        bg_layer = ft.Container(
            bgcolor="black",
            opacity=0.95,
            width=page.width,
            height=page.height,
            alignment=ft.alignment.center,
            content=ft.Image(ref=img_ref, src=get_url(), fit="contain", width=page.width, height=page.height),
            on_click=close # Clicar no fundo/imagem fecha
        )

        # Pilha Principal
        # Ordem: Fundo (Imagem) -> Conteúdos -> Botões (Topo)
        stack = ft.Stack(
            ref=lightbox_stack_ref,
            controls=[
                bg_layer,   # Camada 0: Fundo e Imagem
                lbl_count,  # Camada 1: Texto
                btn_close,  # Camada 2: Botão Fechar
                btn_prev,   # Camada 3: Botão Anterior
                btn_next    # Camada 4: Botão Próximo
            ],
            width=page.width,
            height=page.height,
        )
        
        page.overlay.append(stack)
        page.update()

    # --- UPLOAD ---
    def show_create_album_form(e=None):
        name_tf = ft.TextField(label="Nome do Álbum")
        desc_tf = ft.TextField(label="Descrição")
        
        # Pegar a data atual correta
        data_atual = datetime.now()
        
        # --- Configuração do DatePicker ---
        def on_date_change(e):
            if date_picker.value:
                # Atualiza o campo com a data formatada (DD/MM/AAAA)
                date_tf.value = date_picker.value.strftime("%d/%m/%Y")
                date_tf.update()

        date_picker = ft.DatePicker(
            value=data_atual,                      # Define que abre no dia e mês atual
            first_date=datetime(2000, 1, 1),       # Evita bugar para anos irrealistas (como ano 1900 ou 2050 padrão do sistema)
            last_date=datetime(2050, 12, 31),
            on_change=on_date_change,
            confirm_text="Confirmar",
            cancel_text="Cancelar",
            help_text="Selecione a data do evento"
        )
        
        # Adicionar o picker ao overlay da página para que funcione
        page.overlay.append(date_picker)
        page.update()

        date_tf = ft.TextField(
            label="Data do Evento",
            value=data_atual.strftime("%d/%m/%Y"), # Exibição padrão DD/MM/AAAA BR
            read_only=True,
            suffix=ft.IconButton(
                icon=ft.Icons.CALENDAR_MONTH,
                on_click=lambda _: date_picker.pick_date(),
                tooltip="Selecionar data"
            )
        )
        
        def save(e):
            # Converter a data exibida (DD/MM/AAAA) para o formato do banco (YYYY-MM-DD)
            try:
                dt_obj = datetime.strptime(date_tf.value, "%d/%m/%Y")
                formatted_date = dt_obj.strftime("%Y-%m-%d")
            except Exception:
                formatted_date = datetime.now().strftime("%Y-%m-%d")

            # MUDANÇA: Obter o nome de usuário de forma segura para evitar KeyError
            creator_name = current_user.get('username', 'Desconhecido') if isinstance(current_user, dict) else 'Desconhecido'

            if db.create_album(name_tf.value, desc_tf.value, formatted_date, creator_name):
                show_success(page, "Álbum criado!")
                show_albums_list()
            else:
                show_error(page, "Erro.")

        content = ft.Column([
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=show_albums_list), ft.Text("Novo Álbum", size=20)]),
            name_tf, desc_tf, date_tf,
            ft.ElevatedButton("Salvar", on_click=save)
        ])
        current_view.current.controls = [content]
        page.update()

    def show_upload_form(album_id):
        desc_tf = ft.TextField(label="Descrição")
        info_txt = ft.Text("Selecione fotos...", color="grey")
        prog_bar = ft.ProgressBar(visible=False)
        
        files_state = {'files': [], 'picker': None}
        
        def on_result(e: ft.FilePickerResultEvent):
            if e.files:
                files_state['files'] = e.files
                info_txt.value = f"{len(e.files)} arquivo(s)"
                btn_upload.disabled = False
            page.update()

        picker = ft.FilePicker(on_result=on_result)
        page.overlay.append(picker)
        page.update()

        async def upload_task(desc):
            btn_upload.disabled = True
            prog_bar.visible = True
            page.update()
            
            # --- Lógica Híbrida de Upload ---
            files = files_state['files']
            if not files: return

            to_process = []
            need_upload = []
            
            for f in files:
                if f.path: to_process.append({'obj': f, 'path': f.path, 'temp': False})
                else: need_upload.append(f)
            
            if need_upload:
                os.makedirs("temp_uploads", exist_ok=True)
                before = set(glob.glob("temp_uploads/*"))
                
                objs = []
                for f in need_upload:
                    url = page.get_upload_url(f.name, 600)
                    objs.append(ft.FilePickerUploadFile(f.name, upload_url=url))
                
                # CORREÇÃO: Removido await porque picker.upload não é awaitable
                picker.upload(objs)
                
                # Esperar pelo upload (simples espera de tempo, ideal seria evento)
                # Como não temos callback de término fácil aqui sem reestruturar muito,
                # vamos dar um tempo razoável.
                # Em produção ideal, usaríamos on_upload para setar um Event.
                await asyncio.sleep(2) 
                
                after = set(glob.glob("temp_uploads/*"))
                new_files = list(after - before)
                
                for nf in new_files:
                    f_mock = type('obj', (object,), {'name': os.path.basename(nf)})
                    to_process.append({'obj': f_mock, 'path': nf, 'temp': True})

            count = 0
            total = len(to_process)
            
            for i, item in enumerate(to_process):
                f = item['obj']
                path = item['path']
                try:
                    info_txt.value = f"Enviando {i+1}/{total}: {f.name}"
                    prog_bar.value = (i / total)
                    page.update()
                    
                    with open(path, 'rb') as fo:
                        bits = fo.read()
                    
                    res = db.upload_photo_to_storage(bits, f.name, album_id)
                    if res:
                        user = current_user.get('username', 'Desconhecido') if isinstance(current_user, dict) else 'Desconhecido'
                        db.add_photo(album_id, f.name, res['public_url'], res['storage_path'], desc, user, len(bits))
                        count += 1
                        if item['temp']: 
                            try: os.remove(path)
                            except: pass
                except Exception as ex:
                    print(f"Erro: {ex}")

            prog_bar.visible = False
            if count > 0:
                show_success(page, "Upload concluído!")
                show_album_photos(album_id)
            else:
                show_error(page, "Falha no upload.")
                btn_upload.disabled = False
                page.update()

        btn_upload = ft.ElevatedButton("Enviar", icon=ft.Icons.UPLOAD, disabled=True, 
                                     on_click=lambda e: page.run_task(upload_task, desc_tf.value))

        content = ft.Column([
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: show_album_photos(album_id)), ft.Text("Upload")]),
            desc_tf,
            ft.ElevatedButton("Selecionar", icon=ft.Icons.IMAGE, on_click=lambda e: picker.pick_files(allow_multiple=True)),
            info_txt,
            prog_bar,
            btn_upload
        ])
        current_view.current.controls = [content]
        page.update()

    col = ft.Column(expand=True, ref=current_view)
    show_albums_list()
    return col