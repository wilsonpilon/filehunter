import customtkinter as ctk
from tkinter import filedialog, messagebox


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, db_manager, on_save_callback):
        super().__init__(parent)
        self.title("Configurações do Sistema")
        self.geometry("600x650")
        self.db_manager = db_manager
        self.on_save_callback = on_save_callback

        self.attributes("-topmost", True)
        self.grab_set()

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        ctk.CTkLabel(self, text="Configurações", font=("Arial", 24, "bold")).pack(pady=20)

        # Scrollable Frame para os campos
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=20, pady=10)

        # FileHunter URL
        ctk.CTkLabel(scroll, text="Site do FileHunter (URL):").pack(anchor="w", padx=10)
        self.url_entry = ctk.CTkEntry(scroll, placeholder_text="https://...")
        self.url_entry.pack(fill="x", padx=10, pady=(0, 10))

        # OpenMSX Executable
        ctk.CTkLabel(scroll, text="Executável do OpenMSX:").pack(anchor="w", padx=10)
        exe_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        exe_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.exe_entry = ctk.CTkEntry(exe_frame)
        self.exe_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(exe_frame, text="Buscar", width=80, command=self.browse_exe).pack(side="right")

        # MSX Padrão
        ctk.CTkLabel(scroll, text="Máquina MSX Padrão (ex: Boosted_MSX2_EN):").pack(anchor="w", padx=10)
        self.msx_entry = ctk.CTkEntry(scroll)
        self.msx_entry.pack(fill="x", padx=10, pady=(0, 10))

        # Extensões (Grid 2x2)
        ctk.CTkLabel(scroll, text="Extensões Desejadas:").pack(anchor="w", padx=10)
        ext_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        ext_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.ext_entries = []
        for i in range(4):
            entry = ctk.CTkEntry(ext_frame, placeholder_text=f"Extensão {i + 1} (ex: .rom)")
            entry.grid(row=i // 2, column=i % 2, padx=5, pady=5, sticky="ew")
            self.ext_entries.append(entry)
        ext_frame.grid_columnconfigure((0, 1), weight=1)

        # CustomTkinter Theme
        ctk.CTkLabel(scroll, text="Tema (Appearance):").pack(anchor="w", padx=10)
        self.appearance_option = ctk.CTkOptionMenu(scroll, values=["System", "Light", "Dark"])
        self.appearance_option.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(scroll, text="Cor do Tema:").pack(anchor="w", padx=10)
        self.color_option = ctk.CTkOptionMenu(scroll, values=["blue", "dark-blue", "green"])
        self.color_option.pack(fill="x", padx=10, pady=(0, 20))

        # Botões
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", pady=20, padx=20)

        ctk.CTkButton(btn_frame, text="Cancelar", fg_color="#A13333", hover_color="#7A2626",
                      command=self.destroy).pack(side="left", padx=5, expand=True)
        ctk.CTkButton(btn_frame, text="Salvar", fg_color="#2E7D32", hover_color="#1B5E20",
                      command=self.save).pack(side="right", padx=5, expand=True)

    def browse_exe(self):
        filetypes = [("Executáveis", "*.exe"), ("Todos", "*.*")]
        path = filedialog.askopenfilename(title="Selecionar openMSX", filetypes=filetypes)
        if path:
            self.exe_entry.delete(0, "end")
            self.exe_entry.insert(0, path)

    def load_settings(self):
        config = self.db_manager.get_config()
        if config:
            self.url_entry.insert(0, config.get('filehunter_url') or "")
            self.exe_entry.insert(0, config.get('openmsx_exe') or "")
            self.msx_entry.insert(0, config.get('default_msx_machine') or "")
            self.appearance_option.set(config.get('appearance_mode') or "Dark")
            self.color_option.set(config.get('color_theme') or "blue")

            for i in range(4):
                val = config.get(f'ext{i + 1}') or ""
                self.ext_entries[i].insert(0, val)

    def save(self):
        new_config = {
            "filehunter_url": self.url_entry.get(),
            "openmsx_exe": self.exe_entry.get(),
            "default_msx_machine": self.msx_entry.get(),
            "ext1": self.ext_entries[0].get(),
            "ext2": self.ext_entries[1].get(),
            "ext3": self.ext_entries[2].get(),
            "ext4": self.ext_entries[3].get(),
            "appearance_mode": self.appearance_option.get(),
            "color_theme": self.color_option.get()
        }

        try:
            self.db_manager.save_config(new_config)
            ctk.set_appearance_mode(new_config["appearance_mode"])
            # Nota: set_default_color_theme requer reinicialização para aplicar em todos os widgets
            # mas aplicamos para as próximas janelas.
            ctk.set_default_color_theme(new_config["color_theme"])

            if self.on_save_callback:
                self.on_save_callback()

            messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar configurações: {e}")