import customtkinter as ctk
from database.manager import DatabaseManager
from database.syncer import FileHunterSyncer
from gui.settings_window import SettingsWindow
from gui.file_list_window import AllFilesWindow
from tkinter import messagebox

class FileHunterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FileHunter MSX Manager")
        self.geometry("600x400")

        self.db = DatabaseManager()
        self.syncer = FileHunterSyncer(self.db, self.update_status)

        self.setup_ui()
        self.apply_initial_config()

    def setup_ui(self):
        self.label = ctk.CTkLabel(self, text="FileHunter MSX Manager", font=("Arial", 24, "bold"))
        self.label.pack(pady=20)

        # Botão AllFiles
        self.btn_all = ctk.CTkButton(self, text="AllFiles (Gerenciar)", command=self.open_all_files)
        self.btn_all.pack(pady=10)

        # Botão Sync
        self.btn_sync = ctk.CTkButton(self, text="Sincronizar Banco de Dados", command=self.syncer.check_for_updates)
        self.btn_sync.pack(pady=10)

        # Botão Settings
        self.btn_settings = ctk.CTkButton(self, text="Configurações", command=self.open_settings)
        self.btn_settings.pack(pady=10)

        # Botão Sair (Novo)
        self.btn_exit = ctk.CTkButton(self, text="Sair do Programa", fg_color="#A13333", hover_color="#7A2626",
                                      command=self.destroy)
        self.btn_exit.pack(pady=10)

        # Console de Status
        self.status_box = ctk.CTkTextbox(self, height=120)

    def apply_initial_config(self):
        config = self.db.get_config()
        if config:
            ctk.set_appearance_mode(config[1])
            ctk.set_default_color_theme(config[2])

    def update_status(self, message):
        self.status_box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.status_box.see("end")

    def open_settings(self):
        SettingsWindow(self, self.db, self.apply_initial_config)

    def open_all_files(self):
        if self.db.is_database_empty():
            messagebox.showwarning("Aviso", "O banco está vazio. Sincronize primeiro!")
            return
        AllFilesWindow(self, self.db, self.syncer)

from datetime import datetime
if __name__ == "__main__":
    app = FileHunterApp()
    app.mainloop()