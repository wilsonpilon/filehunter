import subprocess
import threading
import sys


class OpenMSXBridge:
    def __init__(self, executable="openmsx.exe"):
        self.executable = executable
        self.process = None
        self._stop_event = threading.Event()

    def start(self):
        """Inicia o openMSX com redirecionamento de entrada/saída."""
        try:
            # -control stdio permite enviar comandos XML via stdin
            self.process = subprocess.Popen(
                [self.executable, "-control", "stdio"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            print(f"--- openMSX Bridge Ativa (PID: {self.process.pid}) ---")

            # Thread para ler a saída do openMSX (feedback)
            threading.Thread(target=self._read_output, daemon=True).start()

        except FileNotFoundError:
            print(f"Erro: '{self.executable}' não encontrado. Verifique o PATH.")
        except Exception as e:
            print(f"Erro ao iniciar openMSX: {e}")

    def send_command(self, command):
        """Envia um comando no formato XML esperado pelo openMSX."""
        if self.process and self.process.stdin:
            xml_command = f"<command>{command}</command>\n"
            try:
                self.process.stdin.write(xml_command)
                self.process.stdin.flush()
                # print(f"Enviado: {command}") # Opcional para debug
            except OSError as e:
                print(f"Erro ao enviar comando: {e}")

    def _read_output(self):
        """Lê as respostas do openMSX (ajuda a monitorar o estado)."""
        while self.process and not self._stop_event.is_set():
            line = self.process.stdout.readline()
            if not line:
                break
            # Aqui você poderia processar retornos XML do emulador
            # print(f"openMSX diz: {line.strip()}")

    def stop(self):
        """Fecha o emulador graciosamente."""
        self._stop_event.set()
        if self.process:
            self.process.terminate()
            print("Bridge encerrada.")


if __name__ == "__main__":
    # Exemplo de uso interativo similar ao seu .ps1
    bridge = OpenMSXBridge()
    bridge.start()

    print("Digite o comando MSX (ex: set pause on, screenshot, reset) ou 'exit' para fechar.")

    try:
        while True:
            cmd = input("Comando > ")
            if cmd.lower() in ["exit", "quit"]:
                break
            bridge.send_command(cmd)
    except KeyboardInterrupt:
        pass
    finally:
        bridge.stop()