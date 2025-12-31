import customtkinter as ctk
from tkinter import ttk, messagebox
import re
import os
import threading
import time
import glob
import shutil
from datetime import datetime
from gui.disk_manager_window import DiskManagerWindow
from gui.file_config_window import FileConfigWindow
from support.msx_bridge import OpenMSXBridge

class AllFilesWindow(ctk.CTkToplevel):
    def __init__(self, parent, db, syncer, embed=False):
        if embed:
            self.master = parent
        else:
            super().__init__(parent)
            self.title("FileHunter - Gerenciador de Arquivos (Modo Explorer)")
            self.geometry("1200x800")

        self.db = db
        self.syncer = syncer

        # Estado
        self.selected_category_id = None
        self.all_data = []  # Cache de arquivos da categoria atual
        self.filtered_data = []
        self.sort_asc = True
        self.current_page = 0
        self.items_per_page = 50

        # Inicializa a bridge com o executável configurado
        config = self.db.get_config()
        openmsx_exe = config.get('openmsx_exe', 'openmsx.exe') if config else "openmsx.exe"

        self.msx_bridge = OpenMSXBridge(executable=openmsx_exe)
        self.msx_bridge.on_output_received = self.update_status

        # Backup do callback original do syncer
        self.original_status_callback = self.syncer.log
        self.syncer.log = self.update_status

        self.setup_ui(embed=embed)
        self.load_root_categories()
        self.apply_search()

        if not embed:
            self.protocol("WM_DELETE_WINDOW", self.on_close)

    def update_status(self, message):
        if hasattr(self, "status_box") and self.status_box.winfo_exists():
            try:
                prefix = "openMSX >> " if "openMSX:" not in message and "> Enviado" not in message else ""
                self.status_box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {prefix}{message}\n")
                self.status_box.see("end")
            except Exception:
                pass

    def setup_ui(self, embed=False):
        container = self.master if embed else self

        if embed:
            # Se estiver embutido, self não é um widget Tkinter completo ainda
            # pois super().__init__ não foi chamado. Usamos container.
            root_window = container.winfo_toplevel()
            root_window.geometry("1200x800")
            root_window.title("FileHunter MSX Manager - Explorer")

        # 1. Barra Superior
        top_frame = ctk.CTkFrame(container)
        top_frame.pack(side="top", fill="x", padx=10, pady=10)

        ctk.CTkButton(top_frame, text="Sair", width=80, fg_color="#A13333", hover_color="#7A2626",
                      command=self.quit_application).pack(side="left", padx=5)

        def get_root():
            return container.winfo_toplevel()

        ctk.CTkButton(top_frame, text="Configurações", width=120,
                      command=lambda: get_root().open_settings()).pack(side="left", padx=5)

        ctk.CTkButton(top_frame, text="Discos", width=100, fg_color="#1f538d",
                      command=self.open_disk_manager).pack(side="left", padx=5)

        self.btn_sync = ctk.CTkButton(top_frame, text="Sincronizar Banco", width=140, fg_color="#2E7D32",
                                      hover_color="#1B5E20", command=self.start_sync_thread)
        self.btn_sync.pack(side="left", padx=5)

        self.search_entry = ctk.CTkEntry(top_frame, placeholder_text="Filtrar nesta pasta (Regex)...")
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.search_entry.bind("<Return>", lambda e: self.apply_search())

        ctk.CTkButton(top_frame, text="Buscar", width=80, command=self.apply_search).pack(side="left", padx=2)
        ctk.CTkButton(top_frame, text="Limpar", width=80, fg_color="#A13333", command=self.clear_search).pack(
            side="left", padx=2)

        # --- ÁREA DE COMANDO MSX ---
        self.msx_cmd_frame = ctk.CTkFrame(container)
        self.msx_cmd_frame.pack(side="bottom", fill="x", padx=10, pady=(10, 0))

        self.msx_entry = ctk.CTkEntry(
            self.msx_cmd_frame,
            placeholder_text="Comando openMSX (ex: set pause on, screenshot, reset)..."
        )
        self.msx_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.msx_entry.bind("<Return>", lambda e: self.send_msx_command())

        self.btn_send_msx = ctk.CTkButton(
            self.msx_cmd_frame,
            text="Enviar",
            width=80,
            command=self.send_msx_command
        )
        self.btn_send_msx.pack(side="right")

        # 2. Console de Status
        self.status_box = ctk.CTkTextbox(container, height=100)
        self.status_box.pack(side="bottom", fill="x", padx=10, pady=(0, 10))

        # 3. Container Principal
        self.main_container = ctk.CTkFrame(container, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=0)

        self.left_panel = ctk.CTkFrame(self.main_container, width=300)
        self.left_panel.pack(side="left", fill="y", padx=(0, 5))

        ctk.CTkLabel(self.left_panel, text="Diretórios", font=("Arial", 14, "bold")).pack(pady=5)

        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        self.tree = ttk.Treeview(self.left_panel, show="tree")
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<<TreeviewOpen>>", self.on_tree_expand)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        self.right_panel = ctk.CTkFrame(self.main_container)
        self.right_panel.pack(side="right", fill="both", expand=True)

        self.pagination_frame = ctk.CTkFrame(self.right_panel)
        self.pagination_frame.pack(side="bottom", fill="x", padx=5, pady=5)

        self.btn_prev = ctk.CTkButton(self.pagination_frame, text="<<", width=40, command=self.prev_page)
        self.btn_prev.pack(side="left", padx=5)

        self.page_label = ctk.CTkLabel(self.pagination_frame, text="Página 1")
        self.page_label.pack(side="left", expand=True)

        self.btn_download_all = ctk.CTkButton(
            self.pagination_frame,
            text="Baixar Todos",
            fg_color="#2E7D32",
            hover_color="#1B5E20",
            command=self.download_all_current
        )

        self.btn_next = ctk.CTkButton(self.pagination_frame, text=">>", width=40, command=self.next_page)
        self.btn_next.pack(side="right", padx=5)

        self.scroll_frame = ctk.CTkScrollableFrame(self.right_panel)
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

    def execute_file(self, local_path, relative_path=None):
        try:
            screenshot_base_dir = "screenshots"
            if relative_path:
                relative_dir = os.path.dirname(relative_path)
                target_screenshot_dir = os.path.join(screenshot_base_dir, relative_dir)
                os.makedirs(target_screenshot_dir, exist_ok=True)
            else:
                target_screenshot_dir = screenshot_base_dir

            config = self.db.get_config()
            if not config or not config.get('openmsx_exe'):
                messagebox.showwarning("Configuração", "Configure o executável do openMSX.")
                return

            openmsx_exe = os.path.abspath(config.get('openmsx_exe'))
            file_cfg = self.db.get_file_config(relative_path) if relative_path else None

            if file_cfg:
                machine, media_type, ext1, ext2 = file_cfg[0], file_cfg[1], file_cfg[2], file_cfg[3]
                exts = [ext1, ext2]
            else:
                machine = config.get('default_msx_machine')
                media_type = "Auto"
                exts = [config.get(f'ext{i}') for i in range(1, 5)]

            abs_local_path = os.path.abspath(local_path)
            path_upper = local_path.upper()
            media_args = []

            if media_type == "ROM" or (media_type == "Auto" and any(path_upper.endswith(e) for e in [".ROM", ".MX1", ".MX2"])):
                media_args.extend(["-carta", abs_local_path])
            elif media_type == "DSK" or (media_type == "Auto" and path_upper.endswith(".DSK")):
                media_args.extend(["-diska", abs_local_path])
            elif media_type == "CAS" or (media_type == "Auto" and path_upper.endswith(".CAS")):
                media_args.extend(["-cassetteplayer", abs_local_path])
            else:
                media_args.append(abs_local_path)

            extra_args = []
            if machine and machine != "_nenhuma_":
                extra_args.extend(["-machine", machine])
            for ext in exts:
                if ext and ext != "_nenhuma_":
                    extra_args.extend(["-ext", ext])
            extra_args.extend(media_args)

            self.update_status("Iniciando openMSX...")
            self.msx_bridge.start(extra_args=extra_args)

            if relative_path:
                threading.Thread(
                    target=self.monitor_and_collect_screenshots,
                    args=(relative_path, target_screenshot_dir),
                    daemon=True
                ).start()

        except Exception as e:
            self.update_status(f"Erro: {e}")
            messagebox.showerror("Erro", str(e))

    def monitor_and_collect_screenshots(self, relative_path, target_dir):
        if not self.msx_bridge:
            return

        # 1. Tratamento imediato do nome
        base_filename = os.path.basename(relative_path)
        while '.' in base_filename:
            base_filename = os.path.splitext(base_filename)[0]

        docs_dir = os.path.join(os.path.expanduser("~"), "Documents", "openMSX", "screenshots")
        abs_target = os.path.abspath(target_dir)
        # Nota: Inclusão do ESPAÇO antes dos 4 dígitos como solicitado
        mask = f"{base_filename} [0-9][0-9][0-9][0-9].png"

        self.update_status(f"Monitoramento Iniciado:")
        self.update_status(f"  > Origem: {docs_dir}")
        self.update_status(f"  > Destino: {abs_target}")
        self.update_status(f"  > Máscara: '{mask}'")

        # Pré-checagem
        initial_check = glob.glob(os.path.join(docs_dir, mask))
        if initial_check:
            self.update_status(f"  > Já existem {len(initial_check)} imagens na origem.")

        # Aguarda encerramento
        wait_count = 0
        while True:
            if not self.msx_bridge.is_running():
                self.update_status("Detectado encerramento do openMSX.")
                break
            time.sleep(1)
            wait_count += 1
            if wait_count % 10 == 0:
                self.update_status(f"Aguardando fechamento do emulador... ({wait_count}s)")

        try:
            self.update_status(f"--- Fim da Execução: Coletando Imagens ---")
            if not os.path.exists(docs_dir):
                self.update_status("Erro: Pasta de origem não encontrada.")
                return

            found_screenshots = glob.glob(os.path.join(docs_dir, mask))
            if found_screenshots:
                self.update_status(f"Processando {len(found_screenshots)} imagens...")
                os.makedirs(abs_target, exist_ok=True)
                for src_path in found_screenshots:
                    filename = os.path.basename(src_path)
                    dest_path = os.path.join(abs_target, filename)
                    self.update_status(f"Movendo: {filename}")
                    shutil.move(src_path, dest_path)
                self.update_status("Concluído: Screenshots movidas.")
            else:
                self.update_status(f"Nenhuma imagem encontrada com a máscara '{mask}'.")
                files = os.listdir(docs_dir)
                if files:
                    self.update_status(f"Dica: Existem outros arquivos na pasta: {files[:3]}...")
            self.update_status("---------------------------------------")
        except Exception as e:
            self.update_status(f"Erro no coletor: {e}")

    # ... Restante dos métodos (apply_search, load_root_categories, etc.) mantém a lógica original ...
    def send_msx_command(self):
        if not hasattr(self, 'msx_entry'): return
        command = self.msx_entry.get().strip()
        if not command: return
        if self.msx_bridge and self.msx_bridge.is_running():
            self.msx_bridge.send_command(command)
            self.msx_entry.delete(0, "end")
        else:
            self.update_status("Erro: openMSX não está em execução.")

    def start_sync_thread(self):
        self.btn_sync.configure(state="disabled", text="Sincronizando...")
        thread = threading.Thread(target=self.run_sync, daemon=True)
        thread.start()

    def run_sync(self):
        try:
            self.syncer.check_for_updates()
            self.master.after(0, self.finalize_sync)
        except Exception as e:
            self.master.after(0, lambda: self.update_status(f"Erro: {e}"))
            self.master.after(0, lambda: self.btn_sync.configure(state="normal", text="Sincronizar Banco"))

    def finalize_sync(self):
        self.btn_sync.configure(state="normal", text="Sincronizar Banco")
        self.load_root_categories()
        messagebox.showinfo("Sucesso", "Banco atualizado!")

    def on_close(self):
        if self.msx_bridge: self.msx_bridge.stop()
        self.syncer.log = self.original_status_callback
        self.destroy()

    def load_root_categories(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for cat_id, name in self.db.get_categories(None):
            node = self.tree.insert("", "end", text=name, iid=f"cat_{cat_id}", open=False)
            self.tree.insert(node, "end", text="_dummy")

    def on_tree_expand(self, event):
        node_id = self.tree.focus()
        if not node_id.startswith("cat_"): return
        children = self.tree.get_children(node_id)
        if len(children) == 1 and self.tree.item(children[0], "text") == "_dummy":
            self.tree.delete(children[0])
            cat_id = int(node_id.split("_")[1])
            for sid, sname in self.db.get_categories(cat_id):
                snode = self.tree.insert(node_id, "end", text=sname, iid=f"cat_{sid}", open=False)
                self.tree.insert(snode, "end", text="_dummy")

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected or not selected[0].startswith("cat_"): return
        cat_id = int(selected[0].split("_")[1])
        if not self.db.get_categories(cat_id):
            self.btn_download_all.pack(side="right", padx=10)
        else:
            self.btn_download_all.pack_forget()
        self.selected_category_id = cat_id
        self.all_data = self.db.get_all_files(category_id=cat_id)
        self.apply_search()

    def apply_search(self):
        pattern = self.search_entry.get()
        source = self.all_data if self.selected_category_id else self.db.get_all_files()
        if not pattern:
            self.filtered_data = list(source)
        else:
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                self.filtered_data = [f for f in source if regex.search(f)]
            except:
                self.filtered_data = []
        self.current_page = 0
        self.refresh_list()

    def clear_search(self):
        self.search_entry.delete(0, "end")
        self.apply_search()

    def refresh_list(self):
        for widget in self.scroll_frame.winfo_children(): widget.destroy()
        start = self.current_page * self.items_per_page
        page_items = self.filtered_data[start:start+self.items_per_page]
        total_pages = max(1, (len(self.filtered_data) + self.items_per_page - 1) // self.items_per_page)
        self.page_label.configure(text=f"Pag {self.current_page+1}/{total_pages} ({len(self.filtered_data)} arq)")
        for path in page_items:
            row = ctk.CTkFrame(self.scroll_frame)
            row.pack(fill="x", pady=1, padx=2)
            filename = path.split('/')[-1]
            ctk.CTkLabel(row, text=filename, anchor="w").pack(side="left", fill="x", expand=True, padx=5)
            local_path = os.path.join("downloads", path.replace("/", os.sep))
            actions_frame = ctk.CTkFrame(row, fg_color="transparent")
            actions_frame.pack(side="right")
            if os.path.exists(local_path):
                ctk.CTkButton(actions_frame, text="Exec", width=60, fg_color="#2E7D32",
                              command=lambda lp=local_path, rp=path: self.execute_file(lp, rp)).pack(side="right", padx=2)
                ctk.CTkButton(actions_frame, text="Config", width=60,
                              command=lambda p=path: self.open_file_config(p)).pack(side="right", padx=2)
            else:
                ctk.CTkButton(actions_frame, text="Baixar", width=60,
                              command=lambda p=path: self.handle_download(p)).pack(side="right", padx=2)

    def handle_download(self, path, silent=False):
        status = self.syncer.download_file(path)
        if status in ["success", "warning"]:
            if not silent: self.refresh_list()
            return True
        return False

    def download_all_current(self):
        if not self.filtered_data: return
        if messagebox.askyesno("Confirmar", f"Baixar {len(self.filtered_data)} arquivos?"):
            self.btn_download_all.configure(state="disabled", text="Baixando...")
            for path in self.filtered_data:
                local_path = os.path.join("downloads", path.replace("/", os.sep))
                if not os.path.exists(local_path):
                    self.handle_download(path, silent=True)
                    self.update_idletasks()
            self.btn_download_all.configure(state="normal", text="Baixar Todos")
            self.refresh_list()

    def open_file_config(self, relative_path):
        # Determinamos o mestre (janela principal) de forma segura
        if hasattr(self, 'master') and self.master:
            master = self.master.winfo_toplevel()
        elif hasattr(self, 'winfo_toplevel'):
            master = self.winfo_toplevel()
        else:
            # Fallback caso esteja em modo embed e self não seja widget
            master = None

        FileConfigWindow(master, self.db, relative_path)

    def open_disk_manager(self):
        DiskManagerWindow(self)

    def next_page(self):
        if (self.current_page + 1) * self.items_per_page < len(self.filtered_data):
            self.current_page += 1
            self.refresh_list()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_list()

    def quit_application(self):
        self.on_close()
        self.master.winfo_toplevel().destroy()