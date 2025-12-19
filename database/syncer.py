import requests
from datetime import datetime


class FileHunterSyncer:
    BASE_URL = "https://download.file-hunter.com/"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    def __init__(self, db_manager, status_callback):
        self.db = db_manager
        self.log = status_callback

    def check_for_updates(self):
        self.log("Verificando atualizações no servidor...")
        try:
            response = requests.get(f"{self.BASE_URL}allfiles.txt", headers=self.HEADERS, stream=True)
            remote_date = response.headers.get('Last-Modified')

            # Fechamos a conexão do stream pois só queríamos o header por enquanto
            response.close()

            config = self.db.get_config()
            # Agora config[3] contém o last_update corretamente
            last_update = config[3] if config and len(config) > 3 else None

            # Verificamos se as tabelas estão vazias
            db_empty = self.db.is_database_empty()

            if db_empty or last_update != remote_date:
                motivo = "Banco vazio" if db_empty else "Nova data detectada"
                self.log(f"Sincronização necessária: {motivo}")
                self.log(f"Data remota: {remote_date}")

                self.sync_files()
                self.db.update_last_sync(remote_date)
                self.log("Sincronização concluída com sucesso!")
            else:
                self.log("O banco de dados já está atualizado (Data e Conteúdo ok).")
        except Exception as e:
            self.log(f"Erro na sincronização: {str(e)}")

    def sync_files(self):
        # 1. Processando allfiles.txt
        self.log("Baixando allfiles.txt...")
        r = requests.get(f"{self.BASE_URL}allfiles.txt", headers=self.HEADERS)
        lines = [l.strip() for l in r.text.splitlines() if l.strip()]
        self.log(f"Populando {len(lines)} registros em allfiles...")
        self.db.clear_and_populate_files("allfiles", lines)

        # 2. Processando sha1sums.txt
        self.log("Baixando sha1sums.txt...")
        r = requests.get(f"{self.BASE_URL}sha1sums.txt", headers=self.HEADERS)
        sha_data = []
        for line in r.text.splitlines():
            parts = line.split(None, 1)  # Divide no primeiro espaço/tab
            if len(parts) == 2:
                sha_data.append((parts[0].strip(), parts[1].strip()))

        self.log(f"Populando {len(sha_data)} hashes SHA1...")
        self.db.clear_and_populate_files("sha1sums", sha_data)