import customtkinter as ctk
import re
import os
import subprocess
import platform
from tkinter import messagebox


class AllFilesWindow(ctk.CTkToplevel):
    def __init__(self, parent, db, syncer):
        super().__init__(parent)
        self.title("FileHunter - Gerenciador de Arquivos")
        self.geometry("1100x750")
        self.db = db
        self.syncer = syncer

        # Dados e Controle
        self.all_data = self.db.get_all_files()
        self.filtered_data = list(self.all_data)
        self.sort_asc = True
        self.current_page = 0
        self.items_per_page = 50

        self.attributes("-topmost", True)
        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        # Barra Superior de Comandos
        cmd_frame = ctk.CTkFrame(self)
        cmd_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkButton(cmd_frame, text="⬅ Voltar", width=100, fg_color="gray",
                      command=self.destroy).pack(side="left", padx=5)

        self.search_entry = ctk.CTkEntry(cmd_frame, placeholder_text="Busca Regex (ex: .*msx2.*)")
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)

        ctk.CTkButton(cmd_frame, text="Limpar", width=80, fg_color="#A13333",
                      command=self.clear_search).pack(side="left", padx=5)

        ctk.CTkButton(cmd_frame, text="Buscar", width=100,
                      command=self.apply_search).pack(side="left", padx=5)

        # Barra de Filtros/Ordem
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(filter_frame, text="Ordenar A-Z / Z-A", width=150,
                      command=self.toggle_sort).pack(side="right", padx=5)

        # Container de Paginação (Inferior)
        self.pagination_frame = ctk.CTkFrame(self)
        self.pagination_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        self.btn_prev = ctk.CTkButton(self.pagination_frame, text="<< Anterior", command=self.prev_page)
        self.btn_prev.pack(side="left", padx=20)

        self.page_label = ctk.CTkLabel(self.pagination_frame, text="Página 1")
        self.page_label.pack(side="left", expand=True)

        self.btn_next = ctk.CTkButton(self.pagination_frame, text="Próximo >>", command=self.next_page)
        self.btn_next.pack(side="right", padx=20)

        # Container de Listagem
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=0)

    def clear_search(self):
        self.search_entry.delete(0, "end")
        self.apply_search()

    def apply_search(self):
        pattern = self.search_entry.get()
        self.current_page = 0
        if not pattern:
            self.filtered_data = list(self.all_data)
        else:
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                self.filtered_data = [f for f in self.all_data if regex.search(f)]
            except Exception as e:
                messagebox.showerror("Erro Regex", f"Expressão inválida: {e}")
                return
        self.refresh_list()

    def toggle_sort(self):
        self.sort_asc = not self.sort_asc
        self.filtered_data.sort(reverse=not self.sort_asc)
        self.current_page = 0
        self.refresh_list()

    def refresh_list(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_items = self.filtered_data[start:end]

        total_pages = max(1, (len(self.filtered_data) + self.items_per_page - 1) // self.items_per_page)
        self.page_label.configure(
            text=f"Página {self.current_page + 1} de {total_pages} ({len(self.filtered_data)} itens)")

        for path in page_items:
            row = ctk.CTkFrame(self.scroll_frame)
            row.pack(fill="x", pady=2, padx=5)

            ctk.CTkLabel(row, text=path, anchor="w").pack(side="left", fill="x", expand=True, padx=10)

            # Verifica se o arquivo já existe localmente
            local_path = os.path.join("downloads", path.replace("/", os.sep))

            if os.path.exists(local_path):
                btn_text = "Executar"
                btn_color = "#2E7D32"  # Verde escuro
                btn_cmd = lambda p=local_path: self.execute_file(p)
            else:
                btn_text = "Download"
                btn_color = None  # Default
                btn_cmd = lambda p=path: self.handle_download(p)

            btn = ctk.CTkButton(row, text=btn_text, width=100, fg_color=btn_color, command=btn_cmd)
            btn.pack(side="right", padx=10, pady=5)

        self.scroll_frame._parent_canvas.yview_moveto(0)

    def handle_download(self, path):
        status = self.syncer.download_file(path)
        if status in ["success", "warning"]:
            # Se baixou com sucesso, atualiza a lista para mostrar o botão "Executar"
            self.refresh_list()
            if status == "success":
                messagebox.showinfo("Sucesso", "Download e Verificação SHA1 concluídos!")
        elif status == "danger":
            messagebox.showerror("ERRO DE INTEGRIDADE", "O SHA1 não confere! Perigo de arquivo corrompido.")

    def execute_file(self, local_path):
        try:
            if platform.system() == "Windows":
                os.startfile(local_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", local_path])
            else:  # Linux
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