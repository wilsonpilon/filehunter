import customtkinter as ctk
from tkinter import filedialog


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, db_manager, on_save_callback):
        super().__init__(parent)
        self.title("Configurações do Sistema")
        self.geometry("450x400")
        self.db_manager = db_manager
        self.on_save_callback = on_save_callback

        self.attributes("-topmost", True)
        self.grab_set()

        ctk.CTkLabel(self, text="Configuração do Sistema", font=("Arial", 20, "bold")).pack(pady=15)

        # Container para Seleção de Diretório
        dir_frame = ctk.CTkFrame(self, fg_color="transparent")
        dir_frame.pack(pady=10, padx=20, fill="x")

        self.dir_entry = ctk.CTkEntry(dir_frame, placeholder_text="Caminho do diretório...", width=280)
        self.dir_entry.pack(side="left", padx=(0, 5))

        self.btn_browse = ctk.CTkButton(dir_frame, text="Buscar", width=60, command=self.browse_directory)
        self.btn_browse.pack(side="left")

        # Menu de Modo (Light/Dark)
        ctk.CTkLabel(self, text="Modo de Aparência:").pack(pady=(10, 0))
        self.appearance_option = ctk.CTkOptionMenu(self, values=["System", "Dark", "Light"])
        self.appearance_option.pack(pady=5)

        # Menu de Temas de Cores (Blue/Dark-Blue/Green)
        ctk.CTkLabel(self, text="Tema de Cores:").pack(pady=(10, 0))
        self.color_option = ctk.CTkOptionMenu(self, values=["blue", "dark-blue", "green"])
        self.color_option.pack(pady=5)

        # Carregar dados atuais
        current_config = self.db_manager.get_config()
        if current_config:
            self.dir_entry.insert(0, current_config[0])
            self.appearance_option.set(current_config[1])
            self.color_option.set(current_config[2])

        # Botões de ação
        btn_save = ctk.CTkButton(self, text="Salvar Configurações", fg_color="green", command=self.save)
        btn_save.pack(pady=(25, 5))

        btn_cancel = ctk.CTkButton(self, text="Cancelar", fg_color="gray", command=self.destroy)
        btn_cancel.pack(pady=5)

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, directory)

    def save(self):
        directory = self.dir_entry.get()
        appearance = self.appearance_option.get()
        color = self.color_option.get()

        self.db_manager.save_config(directory, appearance, color)

        # Aplica as mudanças imediatamente
        ctk.set_appearance_mode(appearance)
        ctk.set_default_color_theme(color)

        self.on_save_callback()
        self.destroy()