# Onboarding dla Programisty

## Wprowadzenie

Projekt **Bidirectional Voice Agent** to kompleksowe rozwiązanie do dwukierunkowej komunikacji głosowej z wykorzystaniem:

- **Nova2 Sonic** - model głosowy od Amazon
- **Strands Agents** - framework do budowy agentów
- **AgentCore Runtime** - środowisko uruchomieniowe AWS Bedrock

Projekt składa się z trzech głównych komponentów:

1. **Backend** - WebSocket endpoint (Python/FastAPI)
2. **CDK** - Infrastructure as Code dla AWS (TypeScript)
3. **CLI** - Aplikacja kliencka do testowania (Python)

## Wymagania wstępne

### Narzędzia do zainstalowania

1. **Python 3.12+**
   ```bash
   python --version  # Sprawdź wersję
   ```

2. **uv** - nowoczesny menedżer pakietów Python
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Node.js 18+** (dla CDK)
   ```bash
   node --version
   ```

4. **AWS CLI** - skonfigurowany z odpowiednimi credentials
   ```bash
   aws configure
   ```

5. **AWS CDK CLI**
   ```bash
   npm install -g aws-cdk
   ```

6. **Docker** (opcjonalnie, do testowania kontenerów)
   ```bash
   docker --version
   ```

### Wymagane uprawnienia AWS

- Dostęp do AWS Bedrock (model Nova2 Sonic)
- Uprawnienia do tworzenia zasobów AgentCore Runtime
- Uprawnienia do ECR (Elastic Container Registry)
- Uprawnienia do CloudFormation (dla CDK)


## Struktura projektu

```text
BidirectionalVoiceAgent/
├── backend/          # WebSocket endpoint
│   ├── app/
│   │   └── main.py   # Główny plik aplikacji
│   ├── Dockerfile    # Obraz Docker dla AgentCore
│   └── pyproject.toml
├── cdk/              # Infrastructure as Code
│   ├── lib/
│   │   └── backend.ts # Definicja stacku CDK
│   └── bin/
│       └── bidi_voice_chat.ts
└── cli/              # Aplikacja kliencka
    ├── app/
    │   └── main.py   # CLI do testowania
    └── pyproject.toml
```


## Konfiguracja środowiska deweloperskiego

### 1. Backend - Setup lokalny

```bash
cd backend
uv venv
source .venv/bin/activate  # Na Windows: .venv\Scripts\activate
uv sync
```

**Konfiguracja AWS credentials:**

Jeśli nie masz jeszcze skonfigurowanych AWS credentials, wykonaj następujące kroki:

1. **Zainstaluj AWS CLI** (jeśli jeszcze nie masz):
   ```bash
   # Linux/macOS
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   ```

2. **Skonfiguruj credentials:**
   ```bash
   aws configure
   ```
   
   Wprowadź:
   - **AWS Access Key ID** - Twój klucz dostępu AWS
   - **AWS Secret Access Key** - Twój sekretny klucz
   - **Default region** - np. `ap-northeast-1`, `us-east-1` (region, w którym chcesz używać Bedrock)
   - **Default output format** - np. `json`

3. **Alternatywnie - zmienne środowiskowe:**
   
   Jeśli wolisz używać zmiennych środowiskowych zamiast `aws configure`:
   ```bash
   export AWS_ACCESS_KEY_ID="twoj-access-key-id"
   export AWS_SECRET_ACCESS_KEY="twoj-secret-access-key"
   export AWS_DEFAULT_REGION="ap-northeast-1"
   ```
   
   Jeśli używasz temporary credentials (np. z AWS SSO):
   ```bash
   export AWS_SESSION_TOKEN="twoj-session-token"
   ```

4. **Weryfikacja konfiguracji:**
   ```bash
   aws sts get-caller-identity
   ```
   
   Powinieneś zobaczyć informacje o swoim koncie AWS.

**Uruchomienie lokalnego serwera:**

```bash
# Upewnij się, że masz skonfigurowane AWS credentials (patrz wyżej)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080
```

**Testowanie z Docker:**
```bash
# Build obrazu (ARM64)
docker buildx create --use
docker buildx build --platform linux/arm64 -t backend-agent:arm64 --load .

# Uruchomienie
docker run --platform linux/arm64 -p 8080:8080 \
  -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  -e AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
  -e AWS_REGION="$AWS_REGION" \
  backend-agent:arm64
```

### 2. CLI - Setup lokalny

```bash
cd cli
uv venv
source .venv/bin/activate
uv sync
```

**Uruchomienie CLI:**
```bash
# Połączenie z lokalnym serwerem (ws://localhost:8080/ws)
.venv/bin/python app/main.py

# Połączenie z AgentCore Runtime (wymaga AWS credentials)
.venv/bin/python app/main.py --agent_arn 'arn:aws:bedrock-agentcore:ap-northeast-1:...:runtime/...'
```

**Parametry CLI:**

- `--debug` - włącza tryb debug (wyświetla wszystkie typy eventów)
- `--endpoint` - niestandardowy endpoint WebSocket (domyślnie: `ws://localhost:8080/ws`)
- `--agent_arn` - ARN AgentCore Runtime (jeśli podany, używa tego zamiast endpoint)


### 3. CDK - Setup

```bash
cd cdk
npm install
npm run build
```

**Deploy stacku:**
```bash
npx cdk deploy
```

**Inne przydatne komendy:**
```bash
npx cdk diff      # Porównaj z wdrożoną wersją
npx cdk synth     # Wygeneruj CloudFormation template
npx cdk destroy   # Usuń stack
```

## Architektura i kluczowe komponenty

### Backend (`backend/app/main.py`)

**Główne elementy:**

- `BidiAgent` - agent dwukierunkowy z Strands
- `BidiNovaSonicModel` - model Nova2 Sonic
- WebSocket endpoint (`/ws`) - obsługa komunikacji dwukierunkowej
- Health check endpoint (`/ping`)

**Konfiguracja audio:**

- `INPUT_SAMPLE_RATE` - częstotliwość próbkowania wejścia (domyślnie: 16000)
- `OUTPUT_SAMPLE_RATE` - częstotliwość próbkowania wyjścia (domyślnie: 16000)
- `CHANNELS` - liczba kanałów (domyślnie: 1)
- `FORMAT` - format audio (domyślnie: "pcm")

**Zmienne środowiskowe:**

- `MODEL_ID` - ID modelu Bedrock (domyślnie: "amazon.nova-2-sonic-v1:0")
- `REGION_NAME` - region AWS (domyślnie: "ap-northeast-1")


### CLI (`cli/app/main.py`)

**Klasy główne:**

- `AudioChatManager` - zarządza połączeniem WebSocket i komunikacją
- `AudioStreamer` - obsługuje strumieniowanie audio (mikrofon i głośniki)

**Obsługiwane eventy:**

- `bidi_audio_stream` - strumień audio z agenta
- `bidi_transcript_stream` - transkrypcja tekstowa
- `tool_use_stream` - użycie narzędzi przez agenta
- `bidi_interruption` - przerwanie przez użytkownika (barge-in)
- `bidi_connection_restart` - restart połączenia
- `bidi_error` - błędy


### CDK (`cdk/lib/backend.ts`)

**Główne zasoby:**

- `CfnRuntime` - AgentCore Runtime endpoint
- `DockerImageAsset` - obraz Docker z backendem
- `Role` - rola IAM dla AgentCore Runtime

**Uprawnienia IAM:**

- ECR (pobieranie obrazów)
- CloudWatch Logs (logowanie)
- Bedrock (wywoływanie modeli)
- X-Ray (tracing)


## Workflow deweloperski

### 1. Lokalne testowanie

1. Uruchom backend lokalnie:
   ```bash
   cd backend
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8080
   ```

2. W osobnym terminalu uruchom CLI:
   ```bash
   cd cli
   .venv/bin/python app/main.py
   ```

3. Mów do mikrofonu - powinieneś słyszeć odpowiedzi agenta.

### 2. Testowanie z Docker

1. Zbuduj obraz:
   ```bash
   cd backend
   docker buildx build --platform linux/arm64 -t backend-agent:arm64 --load .
   ```

2. Uruchom kontener z odpowiednimi zmiennymi środowiskowymi AWS.

3. Połącz się z CLI używając endpointu kontenera.

### 3. Deploy na AWS

1. Zbuduj i wdróż CDK stack:
   ```bash
   cd cdk
   npm run build
   npx cdk deploy
   ```

2. Po deployu otrzymasz ARN runtime'u w outputach.

3. Użyj ARN w CLI:
   ```bash
   cd cli
   .venv/bin/python app/main.py --agent_arn 'arn:aws:bedrock-agentcore:...'
   ```

## Debugging

### Backend

- Sprawdź logi serwera FastAPI w terminalu
- Użyj endpointu `/ping` do sprawdzenia, czy serwer działa
- Sprawdź AWS CloudWatch Logs po deployu na AgentCore

### CLI

- Użyj flagi `--debug` aby zobaczyć wszystkie eventy:

  ```bash
  .venv/bin/python app/main.py --debug
  ```

### Typowe problemy

1. **Brak audio:**

   - Sprawdź konfigurację audio (sample rate, channels)
   - Upewnij się, że format jest zgodny między backendem a CLI
   - Sprawdź uprawnienia mikrofonu/głośników w systemie

2. **Błędy AWS:**

   - Sprawdź czy credentials są poprawnie skonfigurowane
   - Sprawdź uprawnienia IAM
   - Sprawdź czy model Nova2 Sonic jest dostępny w Twoim regionie

3. **Problemy z WebSocket:**

   - Sprawdź czy port 8080 jest wolny
   - Sprawdź firewall/security groups
   - Sprawdź logi serwera


## Rozszerzanie funkcjonalności

### Dodawanie narzędzi (tools) do agenta

W `backend/app/main.py` możesz dodać własne narzędzia:

```python
from strands.experimental.bidi.tools import stop_conversation
from strands.experimental.bidi.types.tools import Tool

# Definiuj własne narzędzie
my_tool = Tool(...)

# Dodaj do agenta
voice_agent = BidiAgent(
    model=sonic_model, 
    tools=[stop_conversation, my_tool]
)
```

### Modyfikacja konfiguracji audio

Zmień zmienne środowiskowe w:

- Backend: `backend/app/main.py`
- CDK: `cdk/lib/backend.ts` (w `environmentVariables`)
- CLI: `cli/app/main.py`

**Ważne:** Wszystkie trzy miejsca muszą mieć zgodne wartości!


### Dodawanie nowych eventów

W CLI możesz obsłużyć nowe typy eventów w metodzie `_process_responses()` klasy `AudioChatManager`.

## Przydatne linki

- [Strands Agents Documentation](https://strandsagents.com/latest/documentation/)
- [AWS Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/)
- [Nova2 Sonic Documentation](https://docs.aws.amazon.com/nova/)
- [FastAPI WebSocket](https://fastapi.tiangolo.com/advanced/websockets/)
- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)

## Kontakt i wsparcie

W razie problemów sprawdź:

1. Logi aplikacji
2. AWS CloudWatch Logs (po deployu)
3. Dokumentację poszczególnych komponentów w `README.md` w każdym katalogu

