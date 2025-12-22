# FileHunter MSX Manager 🎮

![FileHunter Banner](images/filehunter.png)

O **FileHunter MSX Manager** é um frontend moderno em Python desenvolvido para gerenciar e sincronizar a base de dados de arquivos do repositório [File-Hunter](https://www.file-hunter.com/), um dos maiores acervos dedicados à plataforma MSX.

## 📋 Sobre o Projeto

Este software automatiza o processo de catalogação de arquivos (ROMs, Disk Images, etc), baixando as listagens oficiais (`allfiles.txt` e `sha1sums.txt`) e armazenando-as em um banco de dados local SQLite. Ele permite que usuários de MSX mantenham uma cópia local organizada e sempre atualizada da estrutura de arquivos do site, com verificação automática de integridade.

![Interface do Aplicativo](images/application4.png)

## ✨ Funcionalidades Atuais

    - **Interface Híbrida Inteligente**: O gerenciador de arquivos pode ser executado como uma janela independente ou embutido diretamente na tela principal do aplicativo.
        - *Update*: Corrigido erro de hierarquia (`AttributeError: 'AllFilesWindow' object has no attribute 'tk'`) ao acessar configurações em modo embutido.
    - **Navegação Estilo Explorer Clássico**: Painel de diretórios à esquerda e listagem de arquivos à direita para uma experiência intuitiva.
- **Categorização Relacional**: Processamento automático da estrutura de diretórios do servidor para navegação hierárquica.
- **Busca Recursiva por Pastas**: Ao selecionar um diretório, o sistema exibe todos os arquivos contidos nele e em seus subdiretórios (Aggregation View).
- **Splash Screen com Efeito Fade**: Inicialização elegante com redimensionamento dinâmico de imagem e transição suave.
- **Gerenciador de Arquivos Paginado**: Navegação fluida em milhares de registros com suporte a:
    - **Busca por Expressões Regulares (Regex)**: Filtragem poderosa de arquivos.
    - **Download em Massa**: Botão "Baixar Todos" disponível para coleções completas em diretórios finais.
    - **Verificação de Integridade (SHA1)**: Confirmação automática após o download para garantir que o arquivo não foi corrompido.
    - **Execução Direta**: Botão dinâmico que permite abrir o arquivo localmente caso ele já tenha sido baixado.
    - **Temas Customizáveis**: Suporte total a temas Dark/Light via configurações integradas ao banco de dados.

## 🛠️ Estabilidade e Correções Recentes

- **Fix (UI Lifecycle)**: Ajustada a inicialização da `AllFilesWindow` para garantir compatibilidade com o método `winfo_toplevel()`, permitindo que botões de sistema funcionem corretamente mesmo quando a janela está embutida em containers.
- **Fix (Recursão de Log)**: Removidas chamadas de `update_idletasks()` dentro do fluxo de log que causavam instabilidade e recursão infinita em processos de sincronização longos.
- **Melhoria no Gerenciamento de Janelas**: Implementada detecção dinâmica de contexto (`embed mode`) para o fechamento seguro da aplicação e limpeza de callbacks do sincronizador.

## 🚀 Como Usar


### Pré-requisitos
- **Python 3.10** ou superior (testado no 3.14).
- Conexão com a internet para sincronização inicial.

### Instalação
1. **Clone o repositório**:
   ```bash
   git clone https://github.com/seu-usuario/filehunter-msx-manager.git
   cd filehunter-msx-manager
   ```

2. **Crie e ative seu ambiente virtual**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/Mac:
   source .venv/bin/activate
   ```

3. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

### Execução e Fluxo de Trabalho
1. **Inicie o App**:
   ```bash
   python main.py
   ```
2. **Sincronize o Banco**: Na primeira execução, clique em **Sincronizar Banco**. O app baixará as definições do servidor File-Hunter e populará seu banco de dados local (`database/filehunter.db`).
3. **Navegue e Baixe**: Use a árvore de diretórios para explorar as categorias. Clique em "Baixar" para obter um arquivo individual ou use a busca para encontrar itens específicos.
4. **Execute**: Após o download bem-sucedido e a verificação do SHA1, o botão mudará para "Exec", permitindo abrir o arquivo diretamente no seu emulador ou visualizador padrão.

## 🛠️ Tecnologias Utilizadas

- **Python 3.14**
- **CustomTkinter**: Interface gráfica moderna com widgets customizados.
- **SQLite3**: Banco de dados relacional para indexação e cache.
- **Requests**: Gestão de downloads e comunicação com o servidor.
- **Pillow (PIL)**: Processamento de imagens da interface e splash screen.
- **Hashlib**: Cálculo de SHA1 para segurança de dados.

---
*Este projeto não possui vínculo oficial com o site File-Hunter, sendo uma ferramenta feita por fãs para a comunidade MSX.*