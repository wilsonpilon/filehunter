# FileHunter MSX Manager 🎮

O **FileHunter MSX Manager** é um frontend moderno em Python desenvolvido para gerenciar e sincronizar a base de dados de arquivos do repositório [File-Hunter](https://www.file-hunter.com/), um dos maiores acervos dedicados à plataforma MSX.

## 📋 Sobre o Projeto

Este software automatiza o processo de catalogação de arquivos (ROMs, Disk Images, etc), baixando as listagens oficiais (`allfiles.txt` e `sha1sums.txt`) e armazenando-as em um banco de dados local SQLite. Ele permite que usuários de MSX mantenham uma cópia local organizada e sempre atualizada da estrutura de arquivos do site.

## ✨ Funcionalidades Atuais

- **Sincronização Inteligente**: Compara a data da última atualização local com o servidor para baixar novos dados apenas quando necessário.
- **Interface Moderna**: Construído com `CustomTkinter` para uma aparência dark/light mode nativa e elegante.
- **Gerenciamento de Banco de Dados**: Utiliza SQLite para armazenamento rápido de milhares de registros e hashes SHA1.
- **Configurações Personalizáveis**: Permite definir diretórios padrão e temas visuais que persistem entre sessões.
- **Resiliência de Conexão**: Implementação de Headers (User-Agent) para garantir downloads estáveis diretamente do servidor.

## 🚀 Como Usar

### Pré-requisitos
- Python 3.10 ou superior.
- Virtualenv (recomendado).

### Instalação
1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/filehunter-msx-manager.git
   cd filehunter-msx-manager
   ```

2. Crie e ative seu ambiente virtual:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/Mac:
   source .venv/bin/activate
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

### Execução
Inicie a aplicação principal:
```bash
python main.py
```