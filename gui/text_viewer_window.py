import customtkinter as ctk
import tkinter as tk


class TextViewerWindow(ctk.CTkToplevel):
    def __init__(self, parent, file_path, title="Visualizador de Texto"):
        super().__init__(parent)
        self.title(f"FileHunter - {title}")
        self.geometry("900x700")
        self.configure(fg_color="#f0f0f0")  # Fundo claro para o "papel"

        # Tenta ler o conteúdo do arquivo
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            content = f"Erro ao carregar arquivo: {e}"

        # Layout principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Container para o Papel Zebrado
        self.paper_container = ctk.CTkFrame(self, fg_color="#e0e0e0", corner_radius=0)
        self.paper_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.paper_container.grid_columnconfigure(0, weight=1)
        self.paper_container.grid_rowconfigure(0, weight=1)

        # Canvas para desenhar as listras e furos
        self.canvas = tk.Canvas(self.paper_container, bg="white", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # Texto (Usamos Text do Tkinter para controle total de transparência e scroll)
        # Fonte: 'Dot Matrix' ou 'Consolas'/'Courier' como fallback.
        # 'Fixedsys' também dá um ar bem retro.
        font_retro = ("Consolas", 12)

        self.text_area = tk.Text(
            self.canvas,
            font=font_retro,
            wrap="none",
            bg="white",
            fg="#1a1a1a",
            padx=50,  # Espaço para os furos
            pady=20,
            borderwidth=0,
            highlightthickness=0,
            undo=False
        )

        # Scrollbar customizada
        self.scrollbar = ctk.CTkScrollbar(self.paper_container, command=self.text_area.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.text_area.configure(yscrollcommand=self.scrollbar.set)

        self.text_area.insert("1.0", content)
        self.text_area.configure(state="disabled")

        # Posiciona o widget de texto dentro do canvas de forma expansível
        self.canvas.create_window((0, 0), window=self.text_area, anchor="nw", tags="text_window")

        # Bind para redesenhar o fundo quando redimensionar ou scrollar
        self.text_area.bind("<Configure>", lambda e: self.draw_zebra())
        self.text_area.bind("<Key>", lambda e: self.draw_zebra())  # Para garantir em alguns casos

        # Botão Sair
        self.btn_close = ctk.CTkButton(self, text="Fechar Impressão", fg_color="#A13333",
                                       hover_color="#7A2626", command=self.destroy)
        self.btn_close.grid(row=1, column=0, pady=10)

        self.after(200, self.focus_force)

    def draw_zebra(self):
        """Desenha as faixas verdes e os furos de tração lateral"""
        self.canvas.delete("zebra")

        width = self.text_area.winfo_width()
        height = self.text_area.winfo_height()

        line_height = 20  # Ajuste conforme o tamanho da fonte

        # Cores do papel zebrado clássico
        green_bar = "#e8f5e9"  # Verde bem clarinho

        # Desenha as faixas
        num_lines = int(height / line_height) + 2
        for i in range(num_lines):
            y_start = i * line_height
            if i % 2 == 0:
                self.canvas.create_rectangle(0, y_start, width, y_start + line_height,
                                             fill=green_bar, outline="", tags="zebra")

            # Desenha os furos laterais (Esquerda e Direita)
            hole_size = 8
            padding = 15
            # Furo esquerda
            self.canvas.create_oval(padding, y_start + 6, padding + hole_size, y_start + 6 + hole_size,
                                    fill="#d0d0d0", outline="#b0b0b0", tags="zebra")
            # Furo direita
            self.canvas.create_oval(width - padding - hole_size, y_start + 6, width - padding, y_start + 6 + hole_size,
                                    fill="#d0d0d0", outline="#b0b0b0", tags="zebra")

        # Garante que o texto fique por cima das listras
        self.canvas.tag_raise("text_window")

        # Atualiza a área do canvas para o scroll
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        # Ajusta o tamanho da janela de texto para o tamanho do canvas
        self.canvas.itemconfig("text_window", width=width, height=max(height, num_lines * line_height))
