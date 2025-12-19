import customtkinter as ctk
from tkinter import filedialog

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, db_manager, on_save_callback):
        super().__init__(parent)
        self.title("Configurações")
        self.geometry("450x400")
        self.db_manager = db_manager
        self.on_save_callback = on_save_callback

        self.attributes("-topmost", True)
        self.grab_set()

        ctk.CTkLabel(self, text="Configuração do Sistema", font=("Arial", 20, "bold")).pack(pady=15)

        # Diretório
        dir_frame = ctk.CTkFrame(self, fg_color="transparent")
        dir_frame.pack(pady=10, padx=20, fill="x")
        self.dir_entry = ctk.CTkEntry(dir_frame, placeholder_text="Caminho local...", width=280)
        self.dir_entry.pack(side="left", padx=(0, 5))
        ctk.CTkButton(dir_frame, text="Buscar", width=60, command=self.browse_directory).pack(side="left")

        # Aparência
        ctk.CTkLabel(self, text="Modo de Aparência:").pack(pady=(10, 0))
        self.appearance_option = ctk.CTkOptionMenu(self, values=["System", "Dark", "Light"])
        self.appearance_option.pack(pady=5)

        ctk.CTkLabel(self, text="Tema de Cores:").pack(pady=(10, 0))
        self.color_option = ctk.CTkOptionMenu(self, values=["blue", "dark-blue", "green"])
        self.color_option.pack(pady=5)

        # Carregar dados
        config = self.db_manager.get_config()
        if config:
            self.dir_entry.insert(0, config[0] or "")
            self.appearance_option.set(config[1] or "System")
            self.color_option.set(config[2] or "blue")

        ctk.CTkButton(self, text="Salvar", fg_color="green", command=self.save).pack(pady=(25, 5))
        ctk.CTkButton(self, text="Cancelar", fg_color="gray", command=self.destroy).pack(pady=5)

    def browse_directory(self):
        d = filedialog.askdirectory()
        if d:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, d)

    def save(self):
        self.db_manager.save_config(self.dir_entry.get(), self.appearance_option.get(), self.color_option.get())
        ctk.set_appearance_mode(self.appearance_option.get())
        ctk.set_default_color_theme(self.color_option.get())
        self.on_save_callback()
        self.destroy()