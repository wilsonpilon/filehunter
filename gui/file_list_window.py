import customtkinter as ctk
from tkinter import ttk  # Para o Treeview
import re
import os
import subprocess
import platform
from tkinter import messagebox


class AllFilesWindow(ctk.CTkToplevel):
    def __init__(self, parent, db, syncer):
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

        self.setup_ui()
        self.load_root_categories()
        self.apply_search()  # Carrega inicial

    def setup_ui(self):
        # Barra Superior (Busca)
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(side="top", fill="x", padx=10, pady=10)

        self.search_entry = ctk.CTkEntry(top_frame, placeholder_text="Filtrar nesta pasta (Regex)...")
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.search_entry.bind("<Return>", lambda e: self.apply_search())

        ctk.CTkButton(top_frame, text="Buscar", width=80, command=self.apply_search).pack(side="left", padx=2)
        ctk.CTkButton(top_frame, text="Limpar", width=80, fg_color="#A13333", command=self.clear_search).pack(
            side="left", padx=2)

        # Container Principal (Split)
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=0)

        # Painel Esquerdo (Árvore)
        self.left_panel = ctk.CTkFrame(self.main_container, width=300)
        self.left_panel.pack(side="left", fill="y", padx=(0, 5))

        ctk.CTkLabel(self.left_panel, text="Diretórios", font=("Arial", 14, "bold")).pack(pady=5)

        # Treeview do Tkinter
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)

        self.tree = ttk.Treeview(self.left_panel, show="tree")
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<<TreeviewOpen>>", self.on_tree_expand)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Painel Direito (Arquivos)
        self.right_panel = ctk.CTkFrame(self.main_container)
        self.right_panel.pack(side="right", fill="both", expand=True)

        # Paginação e Rodapé dentro do painel direito
        self.pagination_frame = ctk.CTkFrame(self.right_panel)
        self.pagination_frame.pack(side="bottom", fill="x", padx=5, pady=5)

        self.btn_prev = ctk.CTkButton(self.pagination_frame, text="<<", width=40, command=self.prev_page)
        self.btn_prev.pack(side="left", padx=5)

        self.page_label = ctk.CTkLabel(self.pagination_frame, text="Página 1")
        self.page_label.pack(side="left", expand=True)

        # Botão "Baixar Todos" - Inicialmente oculto
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

    def load_root_categories(self):
        roots = self.db.get_categories(None)
        for cat_id, name in roots:
            node = self.tree.insert("", "end", text=name, iid=f"cat_{cat_id}", open=False)
            self.tree.insert(node, "end", text="_dummy")

    def on_tree_expand(self, event):
        node_id = self.tree.focus()
        if not node_id.startswith("cat_"): return

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

        # Verifica se é o último nível (sem subcategorias)
        has_subcats = len(self.db.get_categories(cat_id)) > 0

        if not self.db.has_files_in_category(cat_id):
            self.tree.item(node_id, open=True)
            self.on_tree_expand(None)

        # Gerencia a visibilidade do botão "Baixar Todos"
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
            if os.path.exists(local_path):
                btn = ctk.CTkButton(row, text="Exec", width=60, fg_color="#2E7D32",
                                    command=lambda p=local_path: self.execute_file(p))
            else:
                btn = ctk.CTkButton(row, text="Baixar", width=60,
                                    command=lambda p=path: self.handle_download(p))
            btn.pack(side="right", padx=5)

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
        if not self.filtered_data:
            return

        confirm = messagebox.askyesno(
            "Confirmar Download em Massa",
            f"Deseja baixar todos os {len(self.filtered_data)} arquivos desta pasta?\n\n"
            "O programa respeitará a estrutura original de diretórios."
        )

        if confirm:
            self.btn_download_all.configure(state="disabled", text="Baixando...")
            self.update_idletasks()

            for path in self.filtered_data:
                local_path = os.path.join("downloads", path.replace("/", os.sep))
                if not os.path.exists(local_path):
                    self.handle_download(path, silent=True)
                    self.update_idletasks() # Mantém a UI responsiva durante o loop

            self.btn_download_all.configure(state="normal", text="Baixar Todos")
            messagebox.showinfo("Finalizado", "Todos os downloads foram processados!")
            self.refresh_list()

    def execute_file(self, local_path):
        try:
            if platform.system() == "Windows":
                os.startfile(local_path)
            elif platform.system() == "Darwin":
                subprocess.call(["open", local_path])
            else:
                subprocess.call(["xdg-open", local_path])
        except Exception as e:
            messagebox.showerror("Erro ao Executar", f"Não foi possível abrir o arquivo: {e}")

    def next_page(self):
        if (self.current_page + 1) * self.items_per_page < len(self.filtered_data):
            self.current_page += 1
            self.refresh_list()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_list()