import sqlite3
import os

class DatabaseManager:
    def __init__(self, db_path="database/filehunter.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self.get_connection() as conn:
            # Tabela de Configuração
            conn.execute("""
                CREATE TABLE IF NOT EXISTS config
                (id INTEGER PRIMARY KEY CHECK (id = 1),
                default_dir TEXT, appearance_mode TEXT, color_theme TEXT,
                last_update TEXT)
            """)
            # Tabelas de dados
            conn.execute("CREATE TABLE IF NOT EXISTS allfiles (filepath TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS sha1sums (hash TEXT, filepath TEXT)")
            conn.commit()

    def clear_and_populate_files(self, table_name, data_list):
        """Limpa e insere dados em massa para performance."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table_name}")
            if table_name == "allfiles":
                cursor.executemany("INSERT INTO allfiles (filepath) VALUES (?)", [(x,) for x in data_list])
            else:
                cursor.executemany("INSERT INTO sha1sums (hash, filepath) VALUES (?, ?)", data_list)
            conn.commit()

    def update_last_sync(self, date_str):
        with self.get_connection() as conn:
            conn.execute("UPDATE config SET last_update = ? WHERE id = 1", (date_str,))
            conn.commit()

    def get_config(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT default_dir, appearance_mode, color_theme, last_update FROM config WHERE id = 1")
            return cursor.fetchone()

    def save_config(self, default_dir, appearance, color):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO config (id, default_dir, appearance_mode, color_theme)
                VALUES (1, ?, ?, ?)
            """, (default_dir, appearance, color))
            conn.commit()

    def is_database_empty(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM allfiles")
            return cursor.fetchone()[0] == 0

    def get_all_files(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT filepath FROM allfiles")
            return [row[0] for row in cursor.fetchall()]

    def get_sha1_for_file(self, filepath):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT hash FROM sha1sums WHERE filepath = ?", (filepath,))
            result = cursor.fetchone()
            return result[0] if result else None

    def add_sha1(self, filepath, sha1_hash):
        with self.get_connection() as conn:
            conn.execute("INSERT INTO sha1sums (hash, filepath) VALUES (?, ?)", (sha1_hash, filepath))
            conn.commit()