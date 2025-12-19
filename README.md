# FileHunter MSX Manager 🎮

![FileHunter Banner](images/filehunter.png)

O **FileHunter MSX Manager** é um frontend moderno em Python desenvolvido para gerenciar e sincronizar a base de dados de arquivos do repositório [File-Hunter](https://www.file-hunter.com/), um dos maiores acervos dedicados à plataforma MSX.

## 📋 Sobre o Projeto

Este software automatiza o processo de catalogação de arquivos (ROMs, Disk Images, etc), baixando as listagens oficiais (`allfiles.txt` e `sha1sums.txt`) e armazenando-as em um banco de dados local SQLite. Ele permite que usuários de MSX mantenham uma cópia local organizada e sempre atualizada da estrutura de arquivos do site, com verificação automática de integridade.

![Interface do Aplicativo](images/application.png)

## ✨ Funcionalidades Atuais

- **Splash Screen Animada**: Inicialização elegante com efeito de fade-out baseada em imagem customizada.
- **Sincronização Inteligente**: Compara a data da última atualização no servidor e limpa prefixos (como `./`) para garantir compatibilidade perfeita entre as listas.
- **Gerenciador de Arquivos Paginado**: Navegação ultra rápida em milhares de registros sem travamentos da interface.
- **Busca por Expressões Regulares (Regex)**: Filtragem poderosa de arquivos por padrões complexos ou nomes simples.
- **Sistema de Downloads Inteligente**:
  - Reconstrói a estrutura de diretórios original do File-Hunter localmente no subdiretório `/downloads`.
  - Verifica automaticamente o **SHA1** após o download para garantir que o arquivo não está corrompido.
  - Altera dinamicamente o botão para **Executar** caso o arquivo já exista localmente.
- **Execução Direta**: Abre arquivos baixados diretamente pelo programa padrão do sistema operacional.
- **Interface Moderna**: Construído com `CustomTkinter` com suporte a temas e modos Dark/Light.

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
Certifique-se de que o arquivo `splashscreen.png` está na pasta raiz e inicie a aplicação principal:
```bash
python main.py
```


## 🛠️ Tecnologias Utilizadas

- **Python 3.14**
- **CustomTkinter**: Interface gráfica moderna.
- **SQLite3**: Banco de dados local para indexação rápida.
- **Requests**: Download de metadados e arquivos.
- **Pillow (PIL)**: Manipulação de imagens e Splash Screen.
- **Hashlib**: Verificação de integridade SHA1.