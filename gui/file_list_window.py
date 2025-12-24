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


class AllFilesWindow(ctk.CTkToplevel):
    def __init__(self, parent, db, syncer, embed=False):
        if embed:
            # Inicializamos como um "objeto" mas precisamos que ele se comporte como widget
            # A melhor forma de manter o suporte híbrido é garantir a inicialização básica.
            self.master = parent
            # Se não chamarmos super().__init__, precisamos garantir que métodos de widget funcionem
            # ou redirecionar as chamadas.
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

        # Backup do callback original do syncer para restaurar ao fechar
        self.original_status_callback = self.syncer.log
        self.syncer.log = self.update_status

        self.setup_ui(embed=embed)
        self.load_root_categories()
        self.apply_search()  # Carrega inicial

        # Protocolo para fechar a janela corretamente
        if not embed:
            self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self, embed=False):
        # Definimos onde os widgets serão desenhados
        container = self.master if embed else self

        if embed:
            # Buscamos a janela principal (root) de forma segura
            root_window = self.master.winfo_toplevel()
            root_window.geometry("1200x800")
            root_window.title("FileHunter MSX Manager - Explorer")

        # 1. Barra Superior (Busca e Ações)
        top_frame = ctk.CTkFrame(container)
        top_frame.pack(side="top", fill="x", padx=10, pady=10)

        ctk.CTkButton(top_frame, text="Sair", width=80, fg_color="#A13333", hover_color="#7A2626",
                      command=self.quit_application).pack(side="left", padx=5)

        # Correção aqui: Se estiver embutido, usamos o master para achar o root.
        # Caso contrário, o próprio self.winfo_toplevel() funciona.
        def get_root():
            return self.master.winfo_toplevel() if embed else self.winfo_toplevel()

        ctk.CTkButton(top_frame, text="Configurações", width=120,
                      command=lambda: get_root().open_settings()).pack(side="left", padx=5)

        ctk.CTkButton(top_frame, text="Discos", width=100, fg_color="#1f538d",
                      command=self.open_disk_manager).pack(side="left", padx=5)

        # Botão de Sincronização com referência para desabilitar durante o processo
        self.btn_sync = ctk.CTkButton(top_frame, text="Sincronizar Banco", width=140, fg_color="#2E7D32",
                                      hover_color="#1B5E20", command=self.start_sync_thread)
        self.btn_sync.pack(side="left", padx=5)

        self.search_entry = ctk.CTkEntry(top_frame, placeholder_text="Filtrar nesta pasta (Regex)...")
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.search_entry.bind("<Return>", lambda e: self.apply_search())

        ctk.CTkButton(top_frame, text="Buscar", width=80, command=self.apply_search).pack(side="left", padx=2)
        ctk.CTkButton(top_frame, text="Limpar", width=80, fg_color="#A13333", command=self.clear_search).pack(
            side="left", padx=2)

        # 2. Console de Status
        self.status_box = ctk.CTkTextbox(container, height=100)
        self.status_box.pack(side="bottom", fill="x", padx=10, pady=(0, 10))

        # 3. Container Principal (Split Central)
        self.main_container = ctk.CTkFrame(container, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=0)

        # Painel Esquerdo (Árvore de Diretórios)
        self.left_panel = ctk.CTkFrame(self.main_container, width=300)
        self.left_panel.pack(side="left", fill="y", padx=(0, 5))

        ctk.CTkLabel(self.left_panel, text="Diretórios", font=("Arial", 14, "bold")).pack(pady=5)

        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        self.tree = ttk.Treeview(self.left_panel, show="tree")
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<<TreeviewOpen>>", self.on_tree_expand)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Painel Direito (Listagem de Arquivos)
        self.right_panel = ctk.CTkFrame(self.main_container)
        self.right_panel.pack(side="right", fill="both", expand=True)

        # Paginação (Rodapé do painel direito)
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

        # Área de Scroll dos arquivos
        self.scroll_frame = ctk.CTkScrollableFrame(self.right_panel)
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

    def update_status(self, message):
        """Atualiza o console de status na interface"""
        if hasattr(self, "status_box") and self.status_box.winfo_exists():
            try:
                self.status_box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
                self.status_box.see("end")
            except Exception:
                pass

    def start_sync_thread(self):
        """Inicia a sincronização em uma thread separada para não travar a UI"""
        self.btn_sync.configure(state="disabled", text="Sincronizando...")
        self.update_status("Iniciando sincronização em segundo plano...")
        thread = threading.Thread(target=self.run_sync)
        thread.daemon = True
        thread.start()

    def run_sync(self):
        """Executa a lógica de sincronização pesada"""
        # Definimos qual objeto de UI usaremos para o .after()
        ui_root = self.master if hasattr(self, "master") and self.master else self

        try:
            self.syncer.check_for_updates()
            # Volta para a thread principal para atualizar a UI
            ui_root.after(0, self.finalize_sync)
        except Exception as e:
            ui_root.after(0, lambda: self.update_status(f"Erro na sincronização: {e}"))
            ui_root.after(0, lambda: self.btn_sync.configure(state="normal", text="Sincronizar Banco"))

    def open_disk_manager(self):
        """Abre a janela de gerenciamento de discos"""
        # Se estiver embutido, usamos o toplevel real (a janela principal) como pai
        master_window = self.master.winfo_toplevel() if hasattr(self, 'master') else self
        DiskManagerWindow(master_window)

    def quit_application(self):
        """Fecha a aplicação com segurança, limpando recursos se necessário"""
        # Se estiver em modo embutido, precisamos referenciar a janela principal (master)
        # para encontrar o topo da hierarquia de widgets.
        try:
            top_level = self.winfo_toplevel()

            # Se for uma janela Toplevel independente
            if isinstance(self, ctk.CTkToplevel):
                self.on_close()
            else:
                # Se estiver embutido ou for a raiz, encerra a janela que a contém
                top_level.destroy()
        except (AttributeError, RuntimeError):
            # Fallback caso o sistema de widgets já esteja sendo destruído
            if hasattr(self, 'master') and self.master:
                try:
                    self.master.winfo_toplevel().destroy()
                except:
                    pass

    def finalize_sync(self):
        """Finaliza a interface após a sincronização"""
        self.btn_sync.configure(state="normal", text="Sincronizar Banco")
        self.load_root_categories()
        messagebox.showinfo("Sincronização", "O banco de dados foi atualizado com sucesso!")

    def on_close(self):
        """Restaura o callback original do syncer antes de fechar"""
        self.syncer.log = self.original_status_callback
        self.destroy()

    def load_root_categories(self):
        # Limpa a árvore antes de carregar (importante após sincronizar)
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

            # Container para botões de ação
            actions_frame = ctk.CTkFrame(row, fg_color="transparent")
            actions_frame.pack(side="right")

            if os.path.exists(local_path):
                ctk.CTkButton(actions_frame, text="Exec", width=60, fg_color="#2E7D32",
                              command=lambda lp=local_path, rp=path: self.execute_file(lp, rp)).pack(side="right",
                                                                                                     padx=2)

            # O botão baixar vira "Configurar" se o arquivo existe
            if os.path.exists(local_path):

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
        elif status == "danger":
            if not silent:
                messagebox.showerror("ERRO DE INTEGRIDADE", f"O SHA1 não confere em:\n{path}")
            return False
        return False

    def download_all_current(self):
        if not self.filtered_data: return

        confirm = messagebox.askyesno(
            "Confirmar Download em Massa",
            f"Deseja baixar todos os {len(self.filtered_data)} arquivos desta pasta?"
        )

        if confirm:
            self.btn_download_all.configure(state="disabled", text="Baixando...")
            self.update_idletasks()
            for path in self.filtered_data:
                local_path = os.path.join("downloads", path.replace("/", os.sep))
                if not os.path.exists(local_path):
                    self.handle_download(path, silent=True)
                    self.update_idletasks()

            self.btn_download_all.configure(state="normal", text="Baixar Todos")
            messagebox.showinfo("Finalizado", "Todos os downloads foram processados!")
            self.refresh_list()

    def execute_file(self, local_path, relative_path=None):
        try:
            config = self.db.get_config()
            if not config or not config.get('openmsx_exe'):
                messagebox.showwarning("Configuração", "Configure o executável do openMSX primeiro.")
                return

            openmsx_exe = os.path.abspath(config.get('openmsx_exe'))

            # Tenta obter configuração específica do arquivo
            file_cfg = self.db.get_file_config(relative_path) if relative_path else None

            if file_cfg:
                machine = file_cfg[0]
                media_type = file_cfg[1]
                exts = [file_cfg[2], file_cfg[3]]
            else:
                machine = config.get('default_msx_machine')
                media_type = "Auto"
                exts = [config.get(f'ext{i}') for i in range(1, 5)]

            cmd = [openmsx_exe]

            if machine and machine != "_nenhuma_":
                cmd.extend(["-machine", machine])

            for ext in exts:
                if ext and ext != "_nenhuma_":
                    cmd.extend(["-ext", ext])

            abs_local_path = os.path.abspath(local_path)
            path_upper = local_path.upper()

            # Lógica de Mídia baseada na configuração salva ou Auto
            if media_type == "ROM" or (
                    media_type == "Auto" and any(path_upper.endswith(e) for e in [".ROM", ".MX1", ".MX2"])):
                cmd.extend(["-carta", abs_local_path])
            elif media_type == "DSK" or (media_type == "Auto" and path_upper.endswith(".DSK")):
                cmd.extend(["-diska", abs_local_path])
            elif media_type == "CAS" or (media_type == "Auto" and path_upper.endswith(".CAS")):
                cmd.extend(["-cassetteplayer", abs_local_path])
            elif media_type == "DirAsDisk":
                # Se for um zip, openMSX aceita como diretório em algumas versões,
                # mas o ideal é passar a pasta se for DirAsDisk
                cmd.extend(["-diska", abs_local_path])
            else:
                # Fallback para o comportamento atual se for Auto e não identificado
                if f"{os.sep}DSK{os.sep}" in path_upper:
                    cmd.extend(["-diska", abs_local_path])
                elif f"{os.sep}ROM{os.sep}" in path_upper:
                    cmd.extend(["-carta", abs_local_path])
                else:
                    cmd.append(abs_local_path)

            # Log para conferência
            display_cmd = " ".join([f'"{arg}"' if " " in arg else arg for arg in cmd])
            self.update_status(f"Lançando comando: {display_cmd}")

            # Execução melhorada:
            # 1. Usamos caminhos absolutos para tudo
            # 2. Definimos o diretório de trabalho para a pasta do executável
            # 3. No Windows, usamos creationflags para desvincular o processo

            exe_dir = os.path.dirname(openmsx_exe)

            if platform.system() == "Windows":
                # DETACHED_PROCESS = 0x00000008 para o processo não morrer com o app
                subprocess.Popen(cmd, cwd=exe_dir, creationflags=0x00000008)
            else:
                subprocess.Popen(cmd, cwd=exe_dir)

            self.update_status("Status: Solicitação de execução enviada.")

        except Exception as e:
            error_msg = f"Erro crítico na execução: {str(e)}"
            self.update_status(error_msg)
            messagebox.showerror("Erro ao Executar", error_msg)

    def open_file_config(self, relative_path):
        # Se estiver embutido, self não é um widget real, então usamos self.master
        parent = self.master if hasattr(self, 'master') and self.master else self
        FileConfigWindow(parent, self.db, relative_path)

    def next_page(self):
        if (self.current_page + 1) * self.items_per_page < len(self.filtered_data):
            self.current_page += 1
            self.refresh_list()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_list()