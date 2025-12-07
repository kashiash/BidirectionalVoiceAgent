# Onboarding dla Instalatora

## Wprowadzenie

Ten dokument zawiera instrukcje instalacji i konfiguracji projektu **Bidirectional Voice Agent** dla osób odpowiedzialnych za wdrożenie i utrzymanie systemu.

## Wymagania systemowe

### Minimalne wymagania

- **System operacyjny:** Linux (Ubuntu 20.04+), macOS, lub Windows 10+
- **Python:** 3.12 lub nowszy
- **Node.js:** 18.x lub nowszy
- **Docker:** 20.10+ (opcjonalnie, dla testowania kontenerów)
- **Pamięć RAM:** minimum 4GB (8GB zalecane)
- **Dostęp do internetu:** wymagany do pobierania zależności

### Wymagania AWS

- **Konto AWS** z aktywną subskrypcją
- **Dostęp do AWS Bedrock** (model Nova2 Sonic)
- **Uprawnienia IAM** do tworzenia:

  - AgentCore Runtime
  - ECR repositories
  - CloudFormation stacks
  - CloudWatch Logs
  - IAM roles


## Instalacja krok po kroku

### Krok 1: Instalacja narzędzi podstawowych

#### Python 3.12+

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev
```

**macOS:**
```bash
brew install python@3.12
```

**Windows:**
Pobierz i zainstaluj z [python.org](https://www.python.org/downloads/)

#### uv (menedżer pakietów Python)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Na Windows użyj PowerShell:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### Node.js 18+

**Linux:**
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**macOS:**
```bash
brew install node@18
```

**Windows:**
Pobierz i zainstaluj z [nodejs.org](https://nodejs.org/)

#### AWS CLI

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

**Weryfikacja:**
```bash
aws --version
```

#### AWS CDK

```bash
npm install -g aws-cdk
cdk --version
```

### Krok 2: Konfiguracja AWS

1. **Skonfiguruj AWS credentials:**
   ```bash
   aws configure
   ```
   
   Wprowadź:

   - AWS Access Key ID
   - AWS Secret Access Key
   - Default region (np. `ap-northeast-1`, `us-east-1`)
   - Default output format (np. `json`)


2. **Sprawdź dostęp do Bedrock:**
   ```bash
   aws bedrock list-foundation-models --region ap-northeast-1
   ```
   
   Upewnij się, że widzisz model `amazon.nova-2-sonic-v1:0`

3. **Sprawdź uprawnienia IAM:**
   ```bash
   aws sts get-caller-identity
   ```

### Krok 3: Instalacja zależności projektu

#### Backend

```bash
cd backend
uv venv
source .venv/bin/activate  # Na Windows: .venv\Scripts\activate
uv sync
```

#### CLI

```bash
cd cli
uv venv
source .venv/bin/activate
uv sync
```

**Uwaga:** Na niektórych systemach może być wymagana instalacja dodatkowych bibliotek systemowych dla PyAudio:

**Linux:**
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
```

**macOS:**
```bash
brew install portaudio
```

**Windows:**
Zainstaluj [PyAudio wheel](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio) odpowiedni dla Twojej wersji Pythona.

#### CDK

```bash
cd cdk
npm install
npm run build
```

### Krok 4: Konfiguracja lokalnego środowiska

#### Backend - zmienne środowiskowe

Utwórz plik `.env` w katalogu `backend/` (opcjonalnie):

```bash
MODEL_ID=amazon.nova-2-sonic-v1:0
REGION_NAME=ap-northeast-1
INPUT_SAMPLE_RATE=16000
OUTPUT_SAMPLE_RATE=16000
CHANNELS=1
```

Lub ustaw zmienne środowiskowe w systemie:
```bash
export MODEL_ID=amazon.nova-2-sonic-v1:0
export REGION_NAME=ap-northeast-1
```

#### CLI - zmienne środowiskowe

```bash
export AWS_DEFAULT_REGION=ap-northeast-1
```

### Krok 5: Testowanie instalacji

#### Test 1: Backend lokalny

```bash
cd backend
source .venv/bin/activate
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080
```

W osobnym terminalu sprawdź:
```bash
curl http://localhost:8080/ping
```

Powinieneś otrzymać: `{"status":"healthy"}`

#### Test 2: CLI z lokalnym backendem

```bash
cd cli
source .venv/bin/activate
.venv/bin/python app/main.py
```

Powinieneś zobaczyć:
```
connected to ws://localhost:8080/ws
Stream initialized successfully
Stream starts! You can now speak into your microphone...
```

## Wdrożenie na AWS (Production)

### Krok 1: Przygotowanie CDK

```bash
cd cdk
npm run build
```

### Krok 2: Bootstrap CDK (tylko pierwszy raz)

```bash
cdk bootstrap aws://ACCOUNT-ID/REGION
```

Przykład:
```bash
cdk bootstrap aws://123456789012/ap-northeast-1
```

### Krok 3: Deploy stacku

```bash
npx cdk deploy
```

**Podczas deployu:**

- CDK utworzy ECR repository
- Zbuduje obraz Docker z backendem
- Wgra obraz do ECR
- Utworzy AgentCore Runtime
- Skonfiguruje IAM roles i permissions


**Czas deployu:** około 10-15 minut

### Krok 4: Pobranie ARN Runtime

Po zakończeniu deployu, CDK wyświetli output z ARN runtime'u:

```
Outputs:
VoiceAgentBackendStack.AgentCoreRuntimeArn = arn:aws:bedrock-agentcore:ap-northeast-1:123456789012:runtime/...
```

Zapisz ten ARN - będzie potrzebny do połączenia z CLI.

### Krok 5: Testowanie z AgentCore Runtime

```bash
cd cli
source .venv/bin/activate
.venv/bin/python app/main.py --agent_arn 'arn:aws:bedrock-agentcore:...'
```

## Konfiguracja produkcji

### Zmienne środowiskowe w AgentCore Runtime

Zmienne są konfigurowane w `cdk/lib/backend.ts`:

```typescript
environmentVariables: {
    "MODEL_ID": "amazon.nova-2-sonic-v1:0",
    "REGION_NAME": "ap-northeast-1",
    "INPUT_SAMPLE_RATE": "16000",
    "OUTPUT_SAMPLE_RATE": "16000",
    "CHANNELS": "1",
}
```

**Ważne:** Te wartości muszą być zgodne z konfiguracją w CLI!

### Modyfikacja konfiguracji

1. Edytuj `cdk/lib/backend.ts`
2. Zmień wartości w `environmentVariables`
3. Rebuild i redeploy:
   ```bash
   cd cdk
   npm run build
   npx cdk deploy
   ```

### Monitoring i logi

**CloudWatch Logs:**
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/YourRuntimeName --follow
```

**CloudWatch Metrics:**
Sprawdź w konsoli AWS CloudWatch → Metrics → bedrock-agentcore

## Rozwiązywanie problemów

### Problem: "Module not found" podczas instalacji

**Rozwiązanie:**
```bash
# Upewnij się, że jesteś w odpowiednim virtual environment
source .venv/bin/activate
uv sync
```

### Problem: "PortAudio not found" (PyAudio)

**Linux:**
```bash
sudo apt-get install portaudio19-dev
```

**macOS:**
```bash
brew install portaudio
```

### Problem: "AWS credentials not found"

**Rozwiązanie:**
```bash
aws configure
# Lub ustaw zmienne środowiskowe:
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...  # Jeśli używasz temporary credentials
```

### Problem: "Model not available in region"

**Rozwiązanie:**
1. Sprawdź dostępność modelu:
   ```bash
   aws bedrock list-foundation-models --region ap-northeast-1 --query "modelSummaries[?modelId=='amazon.nova-2-sonic-v1:0']"
   ```

2. Jeśli model nie jest dostępny, zmień region w konfiguracji.

### Problem: "CDK deploy fails"

**Sprawdź:**
1. Czy masz odpowiednie uprawnienia IAM
2. Czy CDK jest zbootstrappowany w regionie
3. Logi w CloudFormation console

### Problem: "No audio input/output"

**Sprawdź:**
1. Uprawnienia mikrofonu/głośników w systemie
2. Czy urządzenia audio są podłączone i działają
3. Konfigurację audio (sample rate, channels) - musi być zgodna we wszystkich komponentach

## Aktualizacja systemu

### Aktualizacja kodu

```bash
git pull origin main
```

### Aktualizacja zależności

**Backend:**
```bash
cd backend
source .venv/bin/activate
uv sync
```

**CLI:**
```bash
cd cli
source .venv/bin/activate
uv sync
```

**CDK:**
```bash
cd cdk
npm install
npm run build
```

### Redeploy na AWS

```bash
cd cdk
npm run build
npx cdk deploy
```

## Backup i przywracanie

### Backup konfiguracji

Zapisz:

- ARN AgentCore Runtime
- Konfigurację CDK (`cdk/lib/backend.ts`)
- Zmienne środowiskowe


### Przywracanie

1. Przywróć kod z repozytorium
2. Zainstaluj zależności (patrz Krok 3)
3. Skonfiguruj AWS credentials
4. Redeploy stacku (CDK automatycznie odtworzy zasoby)

## Bezpieczeństwo

### Best practices

1. **Nie commituj credentials:**

   - Używaj zmiennych środowiskowych
   - Używaj AWS Secrets Manager dla produkcji

2. **IAM Least Privilege:**

   - Używaj minimalnych wymaganych uprawnień
   - Regularnie przeglądaj IAM policies

3. **Network Security:**

   - Używaj VPC dla produkcji (jeśli wymagane)
   - Konfiguruj security groups odpowiednio

4. **Monitoring:**

   - Włącz CloudWatch alarms
   - Monitoruj koszty AWS


## Wsparcie

W razie problemów:

1. Sprawdź logi aplikacji
2. Sprawdź CloudWatch Logs
3. Sprawdź dokumentację w `README.md` w każdym katalogu
4. Sprawdź dokumentację onboarding dla programistów (`docs/onboarding-programista.md`)


## Checklist instalacji

- [ ] Python 3.12+ zainstalowany
- [ ] uv zainstalowany
- [ ] Node.js 18+ zainstalowany
- [ ] AWS CLI zainstalowany i skonfigurowany
- [ ] AWS CDK zainstalowany
- [ ] Backend zależności zainstalowane
- [ ] CLI zależności zainstalowane
- [ ] CDK zależności zainstalowane
- [ ] Lokalne testy przeszły pomyślnie
- [ ] AWS credentials skonfigurowane
- [ ] CDK zbootstrappowany
- [ ] Stack wdrożony na AWS
- [ ] Test z AgentCore Runtime zakończony sukcesem

