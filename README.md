# 🖥️ MyVPS

> Painel de telemetria e monitoramento em tempo real para VPS e servidores Linux/Windows. Leve, autossuficiente, sem dependência de banco de dados e pronto para rodar em menos de 1 minuto.

---

## ✨ Recursos

- **Métricas em Tempo Real via WebSocket**: Atualizações instantâneas e contínuas sem sobrecarregar a CPU.
- **Hardware & Sistema Operacional**:
  - Utilização de CPU total e detalhada núcleo a núcleo (vCPUs).
  - Memória RAM e Swap (consumo, porcentagem e livres).
  - Armazenamento em disco raiz (`/`) e taxas de I/O de leitura/gravação.
  - Tráfego de rede por interface de rede ativa.
  - Carga média do sistema (*load average* de 1m, 5m e 15m) e tempo de atividade (*uptime*).
- **Contêineres Docker**: Status do daemon Docker e listagem de contêineres ativos/parados com portas e imagens.
- **Processos & Sessões**: Top 10 processos que mais consomem CPU/RAM e usuários logados via terminal/SSH.
- **Interface Moderna**: Tema escuro terminal/minimalista, responsivo, bilíngue (Português/Inglês) e com nome da instância customizável.
- **Segurança Opcional**: Autenticação HTTP Basic Auth configurável em 1 linha de ambiente.

---

## 📋 Pré-requisitos

Para rodar via Docker (recomendado):
- [Docker](https://docs.docker.com/engine/install/) e [Docker Compose v2](https://docs.docker.com/compose/) instalados.
  > Verifique com: `docker compose version`

Para rodar diretamente no sistema (Bare-Metal):
- Python 3.10 ou superior (`python3 --version`).

---

## 🚀 Passo a Passo: Instalação com Docker (Recomendado)

Siga estes 3 passos simples no terminal da sua máquina ou VPS:

```bash
# Passo 1: Clone o repositório
git clone https://github.com/BrunoSaintClair/my-vps.git
cd my-vps

# Passo 2: Crie o arquivo de configuração a partir do modelo
cp .env.example .env

# Passo 3: Suba a aplicação em segundo plano
docker compose up -d --build
```

🎉 **Pronto!** Acesse no seu navegador:
```text
http://IP_DA_SUA_VPS:8000
```
*(A rota raiz `/` redireciona automaticamente para o dashboard interativo)*.

> 💡 **Nota sobre Firewall:** Caso o painel não carregue no navegador, certifique-se de que a porta `8000` está liberada no firewall da sua VPS (`sudo ufw allow 8000/tcp`) ou no Security Group do seu provedor de nuvem (AWS, Oracle Cloud, Hetzner, etc.).

---

## ⚙️ Configuração Personalizada (`.env`)

Você pode editar o arquivo `.env` para ajustar o comportamento da aplicação:

```bash
nano .env
```

| Variável | Valor Padrão | Descrição |
| :--- | :--- | :--- |
| `PORT` | `8000` | Porta externa onde o dashboard estará acessível. |
| `SERVER_NAME` | `MyVPS` | Nome de exibição da VPS no cabeçalho e título da aba (ex: `VPS Produção`). |
| `UPDATE_INTERVAL` | `3.0` | Intervalo em segundos entre atualizações via WebSocket. |
| `AUTH_USERNAME` | *(vazio)* | Usuário para login no painel (HTTP Basic Auth). |
| `AUTH_PASSWORD` | *(vazio)* | Senha para login no painel (HTTP Basic Auth). |

> 🔒 **Dica de Segurança:** Se a sua VPS possui IP público exposto diretamente na internet sem proxy com autenticação ou VPN, configure `AUTH_USERNAME` e `AUTH_PASSWORD`. O navegador exibirá a janela de login nativa antes de dar acesso ao painel e à API.

Após alterar o `.env`, aplique as mudanças com:
```bash
docker compose up -d
```

---

## 🛠️ Comandos Úteis do Dia a Dia

Dentro da pasta do projeto:

```bash
# Ver logs em tempo real
docker compose logs -f

# Reiniciar a aplicação
docker compose restart

# Parar a aplicação
docker compose down

# Atualizar para a versão mais recente do código
git pull origin main
docker compose up -d --build
```

---

## 🐍 Rodando sem Docker (Bare-Metal / Python puro)

Caso prefira rodar diretamente no sistema operacional sem Docker:

```bash
# 1. Crie e ative o ambiente virtual
python3 -m venv venv
source venv/bin/activate  # No Windows: .\venv\Scripts\activate

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Configure as variáveis de ambiente (opcional)
export SERVER_NAME="Minha VPS"
export PORT=8000

# 4. Inicie o servidor
uvicorn app:app --host 0.0.0.0 --port 8000
```

### Configurar como Serviço `systemd` (Linux)

Para manter o MyVPS rodando continuamente em segundo plano e iniciando automaticamente no boot:

1. Crie o arquivo de serviço:
```bash
sudo nano /etc/systemd/system/my-vps.service
```

2. Cole o conteúdo abaixo (ajuste o caminho para o local onde você clonou o projeto):
```ini
[Unit]
Description=MyVPS System Monitoring
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/my-vps
EnvironmentFile=/opt/my-vps/.env
ExecStart=/opt/my-vps/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

3. Ative e inicie o serviço:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now my-vps
```

---

## 🌐 Configuração com Proxy Reverso e Domínio

Se você deseja acessar via domínio (ex: `https://monitor.seudominio.com`) com certificado SSL automático:

### Caddy

O Caddy gerencia SSL automaticamente e suporta WebSocket de forma nativa:

```caddy
monitor.seudominio.com {
    reverse_proxy localhost:8000
}
```

### Nginx

Certifique-se de repassar os cabeçalhos de WebSocket (`Upgrade` e `Connection`):

```nginx
server {
    listen 80;
    server_name monitor.seudominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Traefik com Rede Docker Externa

Se você já utiliza uma rede Docker compartilhada (como `proxy`), descomente as linhas indicadas no [docker-compose.yml](docker-compose.yml):

```yaml
    networks:
      - default
      - proxy

networks:
  proxy:
    external: true
```

---

## 🔄 Deploy Contínuo Automatizado (GitHub Actions)

O repositório já inclui um workflow pronto em [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml).

Para ativar o deploy automático a cada push na branch `main`:
1. No seu repositório no GitHub, acesse **Settings > Secrets and variables > Actions**.
2. Adicione os segredos:
   - `SSH_HOST`: IP público ou hostname da VPS.
   - `SSH_USER`: Usuário de acesso SSH (ex: `root` ou `ubuntu`).
   - `SSH_PRIVATE_KEY`: Chave privada SSH autorizada na VPS (`~/.ssh/authorized_keys`).
   - `SSH_PORT`: Porta SSH (opcional, padrão `22`).

---

## 📡 Endpoints da API

| Rota | Método | Descrição |
| :--- | :--- | :--- |
| `/` | `GET` | Redireciona diretamente para o `/dashboard/`. |
| `/dashboard/` | `GET` | Interface web em tempo real do painel de monitoramento. |
| `/health` | `GET` | Health check aberto (`{"status": "healthy"}`) para uptime monitors. |
| `/data` | `GET` | Retorna o payload completo de métricas em formato JSON. |
| `/ws/data` | `WebSocket` | Stream contínuo de telemetria em tempo real com intervalo configurável. |
| `/docs` | `GET` | Documentação interativa Swagger/OpenAPI. |

---

## 📄 Licença

Distribuído sob a licença MIT. Consulte o arquivo [LICENSE](LICENSE) para mais detalhes. Sinta-se livre para usar, modificar e distribuir para monitorar suas próprias máquinas e servidores.
