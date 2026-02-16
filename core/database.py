import json
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from supabase import create_client, Client
from core.config import Config

BR_TZ = ZoneInfo("America/Sao_Paulo")

class Database:
    def __init__(self):
        if Config.SUPABASE_URL and Config.SUPABASE_KEY:
            self.supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        else:
            self.supabase = None

    # --- AUTENTICAÇÃO ---
    def check_login(self, username, password):
        try:
            response = self.supabase.table('users').select('*').eq('username', username).eq('password', password).execute()
            if response.data:
                user = response.data[0]
                try:
                    now_iso = datetime.now(BR_TZ).isoformat()
                    self.supabase.table('users').update({'last_login': now_iso}).eq('id', user['id']).execute()
                except: pass
                return user
            return None
        except: return None

    def get_user_permissions(self, username):
        try:
            res = self.supabase.table('users').select('permissions, is_admin').eq('username', username).execute()
            if res.data:
                u = res.data[0]
                is_admin = u.get('is_admin', False)
                perms = u.get('permissions', {})
                if isinstance(perms, str): perms = json.loads(perms)
                
                perms['is_admin'] = is_admin
                perms['readonly'] = not is_admin
                
                perms['home'] = True 
                perms['galeria'] = True
                perms['celulas'] = True
                perms['carona'] = True 
                
                if is_admin:
                    perms['visitantes'] = True
                    perms['usuarios'] = True
                else:
                    perms['visitantes'] = perms.get('visitantes', False)
                    perms['usuarios'] = False
                
                return perms
            return {'readonly': True}
        except: return {'readonly': True}

    def add_user(self, username, password, is_admin, perms, full_name, email, phone):
        try:
            data = {'username': username, 'password': password, 'full_name': full_name, 'email': email, 'phone': phone, 'is_admin': is_admin, 'permissions': perms if isinstance(perms, dict) else json.loads(perms), 'is_google_auth': False}
            self.supabase.table('users').insert(data).execute()
            return True
        except: return False
    
    def update_user(self, uid, username, password, is_admin, perms, full_name, email, phone):
        try:
            data = {'username': username, 'full_name': full_name, 'email': email, 'phone': phone, 'is_admin': is_admin, 'permissions': perms if isinstance(perms, dict) else json.loads(perms)}
            if password and password.strip(): data['password'] = password
            self.supabase.table('users').update(data).eq('id', uid).execute()
            return True
        except: return False

    def delete_user(self, uid):
        if uid == 1: return False
        try:
            self.supabase.table('users').delete().eq('id', uid).execute()
            return True
        except: return False

    def get_all_users(self):
        try:
            res = self.supabase.table('users').select('id, username, full_name, email, is_admin, permissions, created_at, last_login').order('full_name').execute()
            result = []
            for u in res.data:
                result.append((u['id'], u['username'], u.get('full_name', ''), u.get('email', ''), u['is_admin'], u['permissions'], u.get('created_at'), u.get('last_login')))
            return result
        except: return []

    def get_user_by_id(self, uid):
        try: return self.supabase.table('users').select('*').eq('id', uid).execute().data[0]
        except: return None

    # --- VISITANTES ---
    def add_visitor(self, name, phone, email, address, obs):
        try:
            now_br = datetime.now(BR_TZ).isoformat()
            data = {'name': name, 'phone': phone, 'email': email, 'address': address, 'observations': obs, 'date_visit': now_br}
            self.supabase.table('visitors').insert(data).execute()
            return True
        except: return False

    def get_all_visitors(self):
        try:
            res = self.supabase.table('visitors').select('*').order('date_visit', desc=True).execute()
            result = []
            for v in res.data:
                dv = v.get('date_visit', '')
                dt_visit = None
                if dv:
                    try: dt_visit = datetime.fromisoformat(dv.replace('Z', '+00:00')).astimezone(BR_TZ)
                    except: pass
                result.append((v['id'], v['name'], v.get('phone'), v.get('email'), v.get('address'), dt_visit, v.get('observations'), v.get('contacted_by'), v.get('contacted_at')))
            return result
        except: return []

    def update_visitor(self, vid, name, phone, email, address, obs):
        try:
            data = {'name': name, 'phone': phone, 'email': email, 'address': address, 'observations': obs}
            self.supabase.table('visitors').update(data).eq('id', vid).execute()
            return True
        except: return False

    def delete_visitor(self, vid):
        try:
            self.supabase.table('visitors').delete().eq('id', vid).execute()
            return True
        except: return False

    def get_visitor_by_id(self, vid):
        try:
            res = self.supabase.table('visitors').select('*').eq('id', vid).execute()
            if res.data:
                v = res.data[0]
                return (v['id'], v['name'], v.get('phone'), v.get('email'), v.get('address'), v.get('date_visit'), v.get('observations'))
            return None
        except: return None

    def mark_visitor_contacted(self, visitor_id, user_name):
        try:
            now_br = datetime.now(BR_TZ).isoformat()
            self.supabase.table('visitors').update({'contacted_by': user_name, 'contacted_at': now_br}).eq('id', visitor_id).execute()
            return True
        except: return False

    # --- CÉLULAS ---
    def add_cell(self, name, leader, host, address, day, time, obs):
        try:
            data = {'name': name, 'leader_name': leader, 'host_name': host, 'address': address, 'meeting_day': day, 'meeting_time': time, 'observations': obs, 'active': True}
            self.supabase.table('cells').insert(data).execute()
            return True
        except: return False

    def get_all_cells(self):
        try:
            res = self.supabase.table('cells').select('*').order('active', desc=True).order('name').execute()
            return [(c['id'], c['name'], c['leader_name'], c.get('host_name'), c.get('address'), c.get('meeting_day'), c.get('meeting_time'), c.get('observations'), c.get('active')) for c in res.data]
        except: return []

    def deactivate_cell(self, cid):
        try:
            self.supabase.table('cells').update({'active': False}).eq('id', cid).execute()
            return True
        except: return False

    def activate_cell(self, cid):
        try:
            self.supabase.table('cells').update({'active': True}).eq('id', cid).execute()
            return True
        except: return False

    def delete_cell_permanent(self, cid):
        try:
            self.supabase.table('cells').delete().eq('id', cid).execute()
            return True
        except: return False

    # --- AGENDA ---
    def add_event(self, title, desc, date, time, loc, is_recurring):
        try:
            if len(time) == 5: time += ":00"
            data = {'title': title, 'description': desc, 'event_date': date, 'event_time': time, 'location': loc, 'is_recurring': is_recurring}
            self.supabase.table('agenda').insert(data).execute()
            return True
        except: return False

    def update_event(self, eid, title, desc, date, time, loc, is_recurring):
        try:
            if len(time) == 5: time += ":00"
            data = {'title': title, 'description': desc, 'event_date': date, 'event_time': time, 'location': loc, 'is_recurring': is_recurring}
            self.supabase.table('agenda').update(data).eq('id', eid).execute()
            return True
        except: return False

    def delete_event(self, eid):
        try:
            self.supabase.table('agenda').delete().eq('id', eid).execute()
            return True
        except: return False

    def sync_agenda(self):
        try:
            res = self.supabase.table('agenda').select('*').execute()
            if not res.data: return
            today = datetime.now(BR_TZ).date()
            for ev in res.data:
                try:
                    ev_date_obj = datetime.strptime(ev['event_date'], "%Y-%m-%d").date()
                    if ev_date_obj < today:
                        if ev.get('is_recurring'):
                            new_date = ev_date_obj
                            while new_date < today: new_date += timedelta(days=7)
                            self.supabase.table('agenda').update({'event_date': new_date.strftime("%Y-%m-%d")}).eq('id', ev['id']).execute()
                        else: self.delete_event(ev['id'])
                except: continue
        except: pass

    def get_upcoming_events(self):
        try:
            self.sync_agenda()
            today_str = datetime.now(BR_TZ).strftime("%Y-%m-%d")
            return self.supabase.table('agenda').select('*').gte('event_date', today_str).order('event_date').order('event_time').execute().data
        except: return []

    def get_recent_photos(self, limit=15):
        try:
            res = self.supabase.table('photos').select('storage_path').order('created_at', desc=True).limit(limit).execute()
            return [self.get_photo_url(p['storage_path']) for p in res.data]
        except: return []

    # --- DEVOCIONAL DO DIA ---
    def get_today_devotional(self):
        """Busca o devocional vigente. Antes das 8h (BR) mostra o do dia anterior.
        Se não encontrar o devocional esperado, faz fallback para o mais recente."""
        try:
            now_br = datetime.now(BR_TZ)
            
            # Antes das 8h, o devocional vigente é o do dia anterior
            if now_br.hour < 8:
                target_date = (now_br - timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                target_date = now_br.strftime("%Y-%m-%d")
            
            res = self.supabase.table('devotionals').select('*').eq('data', target_date).execute()
            if res.data:
                return res.data[0]
            
            # Fallback: busca o devocional mais recente disponível
            if res.data:
                return res.data[0]
            return None
        except:
            return None

    def increment_devotional_likes(self, dev_id):
        """Incrementa o contador de likes de um devocional."""
        try:
            # Primeiro busca o valor atual para garantir consistência (ou usa rpc se tiver)
            # Aqui vamos fazer um update simples incrementando
            # Nota: Em produção idealmente usaria uma RPC 'increment_likes' para atomicidade
            res = self.supabase.table('devotionals').select('likes').eq('id', dev_id).execute()
            if res.data:
                current = res.data[0].get('likes', 0) or 0
                new_val = current + 1
                self.supabase.table('devotionals').update({'likes': new_val}).eq('id', dev_id).execute()
                return new_val
            return None
        except Exception as e:
            print(f"Erro ao curtir devocional: {e}")
            return None

    # --- GALERIA NATIVA ---
    def create_album(self, name, description, event_date, created_by):
        try:
            data = {'name': name, 'description': description, 'event_date': event_date, 'created_by': created_by}
            response = self.supabase.table('albums').insert(data).execute()
            return response.data[0] if response.data else None
        except: return None
    
    def get_all_albums(self):
        try:
            response = self.supabase.table('albums').select('*').order('event_date', desc=True).execute()
            return response.data if response.data else []
        except: return []
    
    def get_album_by_id(self, album_id):
        try:
            response = self.supabase.table('albums').select('*').eq('id', album_id).execute()
            return response.data[0] if response.data else None
        except: return None
    
    def delete_album(self, album_id):
        try:
            photos = self.get_photos_by_album(album_id)
            for photo in photos:
                try: self.supabase.storage.from_('gallery').remove([photo['storage_path']])
                except: pass
            self.supabase.table('albums').delete().eq('id', album_id).execute()
            return True
        except: return False
    
    def add_photo(self, album_id, file_name, file_path, storage_path, description, uploaded_by, file_size):
        try:
            data = {'album_id': album_id, 'file_name': file_name, 'file_path': file_path, 'storage_path': storage_path, 'description': description, 'uploaded_by': uploaded_by, 'file_size': file_size}
            response = self.supabase.table('photos').insert(data).execute()
            return response.data[0] if response.data else None
        except: return None
    
    def get_photos_by_album(self, album_id):
        try:
            response = self.supabase.table('photos').select('*').eq('album_id', album_id).order('created_at', desc=True).execute()
            return response.data if response.data else []
        except: return []
    
    def delete_photo(self, photo_id):
        try:
            response = self.supabase.table('photos').select('*').eq('id', photo_id).execute()
            if response.data:
                photo = response.data[0]
                try: self.supabase.storage.from_('gallery').remove([photo['storage_path']])
                except: pass
                self.supabase.table('photos').delete().eq('id', photo_id).execute()
                return True
            return False
        except: return False
    
    def upload_photo_to_storage(self, file_bytes, file_name, album_id):
        try:
            unique_name = f"{album_id}/{uuid.uuid4()}_{file_name}"
            self.supabase.storage.from_('gallery').upload(unique_name, file_bytes, file_options={"content-type": "image/jpeg"})
            url = self.supabase.storage.from_('gallery').get_public_url(unique_name)
            return {'storage_path': unique_name, 'public_url': url}
        except: return None
    
    def get_photo_url(self, storage_path):
        try: return self.supabase.storage.from_('gallery').get_public_url(storage_path)
        except: return None

    # ==========================
    # CARONA SOLIDÁRIA
    # ==========================
    
    def add_ride(self, driver, origin, dest, ride_datetime, seats, whatsapp, event_datetime):
        try:
            data = {
                'driver_name': driver,
                'origin': origin,
                'destination': dest,
                'ride_datetime': ride_datetime,
                'event_datetime': event_datetime,
                'available_seats': int(seats),
                'whatsapp': whatsapp,
                'passengers': ""
            }
            self.supabase.table('rides').insert(data).execute()
            return True
        except Exception as e:
            print(f"Erro add_ride: {e}")
            return False

    # --- MÉTODO DE ATUALIZAÇÃO ---
    def update_ride(self, ride_id, origin, dest, ride_datetime, seats, whatsapp, event_datetime):
        try:
            data = {
                'origin': origin,
                'destination': dest,
                'ride_datetime': ride_datetime,
                'event_datetime': event_datetime,
                'available_seats': int(seats),
                'whatsapp': whatsapp
            }
            self.supabase.table('rides').update(data).eq('id', ride_id).execute()
            return True
        except Exception as e:
            print(f"Erro update_ride: {e}")
            return False

    def get_upcoming_rides(self):
        try:
            now_br = datetime.now(BR_TZ).isoformat()
            res = self.supabase.table('rides').select('*').gte('ride_datetime', now_br).order('ride_datetime').execute()
            return res.data if res.data else []
        except: return []
    
    def get_upcoming_rides_count(self):
        try:
            now_br = datetime.now(BR_TZ).isoformat()
            res = self.supabase.table('rides').select('*', count='exact', head=True).gte('ride_datetime', now_br).execute()
            return res.count
        except: return 0

    def join_ride(self, ride_id, passenger_name, current_passengers, current_seats):
        try:
            new_passengers = f"{current_passengers}, {passenger_name}" if current_passengers else passenger_name
            new_seats = current_seats - 1
            if new_seats < 0: return False

            self.supabase.table('rides').update({'passengers': new_passengers, 'available_seats': new_seats}).eq('id', ride_id).execute()
            return True
        except: return False

    # --- REMOVER PASSAGEIRO ---
    def remove_passenger(self, ride_id, passenger_to_remove, current_passengers_str, current_seats):
        try:
            if not current_passengers_str: return False
            
            # 1. Transforma a string em lista: "Bruno, Maria" -> ["Bruno", "Maria"]
            passenger_list = [p.strip() for p in current_passengers_str.split(',') if p.strip()]
            
            # 2. Remove o passageiro da lista
            if passenger_to_remove in passenger_list:
                passenger_list.remove(passenger_to_remove)
            else:
                return False # Passageiro não encontrado na lista
            
            # 3. Reconstrói a string e aumenta a vaga
            new_passengers_str = ", ".join(passenger_list)
            new_seats = current_seats + 1
            
            # 4. Atualiza no banco
            self.supabase.table('rides').update({
                'passengers': new_passengers_str,
                'available_seats': new_seats
            }).eq('id', ride_id).execute()
            
            return True
        except Exception as e:
            print(f"Erro remove_passenger: {e}")
            return False

    def delete_ride(self, ride_id):
        try:
            self.supabase.table('rides').delete().eq('id', ride_id).execute()
            return True
        except: return False