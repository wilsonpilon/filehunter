import customtkinter as ctk
import threading
from database.manager import DatabaseManager
from database.syncer import FileHunterSyncer
from gui.settings_window import SettingsWindow


class FileHunterApp(ctk.CTk):
    def __init__(self):
        self.db_manager = DatabaseManager()
        config = self.db_manager.get_config()
        if config:
            ctk.set_appearance_mode(config[1])
            ctk.set_default_color_theme(config[2])

        super().__init__()
        self.title("FileHunter MSX Frontend")
        self.geometry("700x500")

        # UI Elements
        self.label = ctk.CTkLabel(self, text="FileHunter MSX Manager", font=("Arial", 22, "bold"))
        self.label.pack(pady=10)

        # Área de Log/Status
        self.status_box = ctk.CTkTextbox(self, width=600, height=200, font=("Consolas", 12))
        self.status_box.pack(pady=10, padx=20)
        self.status_box.configure(state="disabled")

        self.btn_sync = ctk.CTkButton(self, text="Sincronizar Banco", command=self.start_sync_thread)
        self.btn_sync.pack(pady=5)

        self.btn_settings = ctk.CTkButton(self, text="Configurações", command=self.open_settings)
        self.btn_settings.pack(pady=5)

        self.btn_exit = ctk.CTkButton(self, text="Sair", fg_color="#880000", command=self.quit)
        self.btn_exit.pack(pady=5)

        self.after(500, self.auto_check)

    def log_status(self, message):
        """Atualiza a caixa de texto de forma segura para threads"""
        timestamp = threading.current_thread().name  # Apenas para exemplo
        self.status_box.configure(state="normal")
        self.status_box.insert("end", f"> {message}\n")
        self.status_box.see("end")
        self.status_box.configure(state="disabled")

    def start_sync_thread(self):
        self.btn_sync.configure(state="disabled")
        syncer = FileHunterSyncer(self.db_manager, self.log_status)
        thread = threading.Thread(target=lambda: self.run_sync(syncer), daemon=True)
        thread.start()

    def run_sync(self, syncer):
        syncer.check_for_updates()
        self.btn_sync.configure(state="normal")

    def auto_check(self):
        config = self.db_manager.get_config()
        if not config:
            self.open_settings()
        else:
            self.start_sync_thread()

    def open_settings(self):
        SettingsWindow(self, self.db_manager, lambda: self.log_status("Configurações salvas."))


if __name__ == "__main__":
    app = FileHunterApp()
    app.mainloop()