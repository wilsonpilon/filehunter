import customtkinter as ctk
from tkinter import ttk  # Para o Treeview
import re
import os
import subprocess
import platform
import threading
from tkinter import messagebox
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

    def send_msx_command(self):
        """Lê o comando da interface e envia para o openMSX via bridge"""
        if not hasattr(self, 'msx_entry'):
            return

        command = self.msx_entry.get().strip()
        if not command:
            return

        if self.msx_bridge and self.msx_bridge.is_running():
            self.msx_bridge.send_command(command)
            self.msx_entry.delete(0, "end")
        else:
            self.update_status("Erro: openMSX não está em execução ou bridge não iniciada.")

    def setup_ui(self, embed=False):
        container = self.master if embed else self

        if embed:
            root_window = self.master.winfo_toplevel()
            root_window.geometry("1200x800")
            root_window.title("FileHunter MSX Manager - Explorer")

        # 1. Barra Superior
        top_frame = ctk.CTkFrame(container)
        top_frame.pack(side="top", fill="x", padx=10, pady=10)

        ctk.CTkButton(top_frame, text="Sair", width=80, fg_color="#A13333", hover_color="#7A2626",
                      command=self.quit_application).pack(side="left", padx=5)

        def get_root():
            return self.master.winfo_toplevel() if embed else self.winfo_toplevel()

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

    def update_status(self, message):
        if hasattr(self, "status_box") and self.status_box.winfo_exists():
            try:
                prefix = "openMSX >> " if "openMSX:" not in message and "> Enviado" not in message else ""
                self.status_box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {prefix}{message}\n")
                self.status_box.see("end")
            except Exception:
                pass

    def start_sync_thread(self):
        self.btn_sync.configure(state="disabled", text="Sincronizando...")
        self.update_status("Iniciando sincronização...")
        thread = threading.Thread(target=self.run_sync)
        thread.daemon = True
        thread.start()

    def run_sync(self):
        ui_root = self.master if hasattr(self, "master") and self.master else self
        try:
            self.syncer.check_for_updates()
            ui_root.after(0, self.finalize_sync)
        except Exception as e:
            ui_root.after(0, lambda: self.update_status(f"Erro na sincronização: {e}"))
            ui_root.after(0, lambda: self.btn_sync.configure(state="normal", text="Sincronizar Banco"))

    def finalize_sync(self):
        self.btn_sync.configure(state="normal", text="Sincronizar Banco")
        self.load_root_categories()
        messagebox.showinfo("Sincronização", "Banco de dados atualizado!")

    def on_close(self):
        if self.msx_bridge:
            self.msx_bridge.stop()
        self.syncer.log = self.original_status_callback
        self.destroy()

    def load_root_categories(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        roots = self.db.get_categories(None)
        for cat_id, name in roots:
            node = self.tree.insert("", "end", text=name, iid=f"cat_{cat_id}", open=False)
            self.tree.insert(node, "end", text="_dummy")

    def on_tree_expand(self, event):
        node_id = self.tree.focus()
        if not node_id or not node_id.startswith("cat_"): return
        children = self.tree.get_children(node_id)
        if len(children) == 1 and self.tree.item(children[0], "text") == "_dummy":
            self.tree.delete(children[0])
            cat_id = int(node_id.split("_")[1])
            subcats = self.db.get_categories(cat_id)
            for sid, sname in subcats:
                snode = self.tree.insert(node_id, "end", text=sname, iid=f"cat_{sid}", open=False)
                self.tree.insert(snode, "end", text="_dummy")

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected or not selected[0].startswith("cat_"): return
        node_id = selected[0]
        cat_id = int(node_id.split("_")[1])
        has_subcats = len(self.db.get_categories(cat_id)) > 0
        if not self.db.has_files_in_category(cat_id):
            self.tree.item(node_id, open=True)
            self.on_tree_expand(None)
        if not has_subcats:
            self.btn_download_all.pack(side="right", padx=10)
        else:
            self.btn_download_all.pack_forget()
        self.selected_category_id = cat_id
        self.current_page = 0
        self.all_data = self.db.get_all_files(category_id=self.selected_category_id)
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
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_items = self.filtered_data[start:end]
        total_pages = max(1, (len(self.filtered_data) + self.items_per_page - 1) // self.items_per_page)
        self.page_label.configure(text=f"Pag {self.current_page + 1}/{total_pages} ({len(self.filtered_data)} arq)")
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
                ctk.CTkButton(actions_frame, text="Configurar", width=80,
                              command=lambda p=path: self.open_file_config(p)).pack(side="right", padx=2)
            else:
                ctk.CTkButton(actions_frame, text="Baixar", width=60,
                              command=lambda p=path: self.handle_download(p)).pack(side="right", padx=2)

    def handle_download(self, path, silent=False):
        status = self.syncer.download_file(path)
        if status in ["success", "warning"]:
            if not silent:
                self.refresh_list()
                if status == "success":
                    messagebox.showinfo("Sucesso", f"Download concluído:\n{path}")
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

    def execute_file(self, local_path, relative_path=None):
        try:
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

        except Exception as e:
            self.update_status(f"Erro: {e}")
            messagebox.showerror("Erro", str(e))

    def open_file_config(self, relative_path):
        parent = self.master if hasattr(self, 'master') and self.master else self
        FileConfigWindow(parent, self.db, relative_path)

    def open_disk_manager(self):
        master_window = self.master.winfo_toplevel() if hasattr(self, 'master') else self
        DiskManagerWindow(master_window)

    def next_page(self):
        if (self.current_page + 1) * self.items_per_page < len(self.filtered_data):
            self.current_page += 1
            self.refresh_list()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_list()

    def quit_application(self):
        try:
            top_level = self.winfo_toplevel()
            if isinstance(self, ctk.CTkToplevel):
                self.on_close()
            else:
                top_level.destroy()
        except:
            pass