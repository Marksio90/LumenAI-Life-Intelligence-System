# 🐍 LumenAI - Mamba Environment Setup

## Czym jest Mamba?

**Mamba** to ultraszybka alternatywa dla Conda - package managera dla Pythona. Szczególnie polecana dla projektów ML/AI, ponieważ:

✅ **Szybkość** - nawet 10x szybsza niż Conda
✅ **Lepsza rezolucja zależności** - mniej konfliktów
✅ **Kompatybilność** - pełna zgodność z Conda
✅ **Izolacja środowisk** - każdy projekt w osobnym środowisku

## Szybki Start

### Opcja 1: Automatyczna instalacja (Zalecane)

```bash
# Jeden skrypt zrobi wszystko
make mamba-setup

# Lub bezpośrednio:
./setup_mamba.sh
```

Ten skrypt:
1. Sprawdzi czy Mamba jest zainstalowana
2. Jeśli nie - zainstaluje Miniforge (zawiera Mambę)
3. Stworzy środowisko LumenAI z wszystkimi zależnościami
4. Zainstaluje frontend dependencies (jeśli Node.js dostępny)

### Opcja 2: Manualna instalacja

#### 1. Zainstaluj Miniforge (zawiera Mambę)

**Linux:**
```bash
curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
bash Miniforge3-Linux-x86_64.sh
source ~/.bashrc
```

**macOS (Intel):**
```bash
curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh"
bash Miniforge3-MacOSX-x86_64.sh
source ~/.bashrc
```

**macOS (Apple Silicon):**
```bash
curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh"
bash Miniforge3-MacOSX-arm64.sh
source ~/.bashrc
```

#### 2. Stwórz środowisko

**Pełne środowisko (ML, Vision, Audio):**
```bash
mamba env create -f environment.yml
```

**Minimalne środowisko (tylko core):**
```bash
mamba env create -f environment-minimal.yml
```

#### 3. Aktywuj środowisko

```bash
# Pełne
mamba activate lumenai

# Minimalne
mamba activate lumenai-minimal
```

## Dostępne środowiska

### 1. Pełne środowisko (`lumenai`)

**Plik:** `environment.yml`

Zawiera wszystko:
- Core framework (FastAPI, Uvicorn)
- LLM libraries (OpenAI, Anthropic, LangChain, LlamaIndex)
- ML/AI (PyTorch, scikit-learn, transformers)
- Vector DB (ChromaDB, Pinecone)
- Audio processing (Whisper, FFmpeg, librosa)
- Vision (OpenCV, Tesseract OCR, Pillow)
- Development tools (Jupyter, pytest, black)
- Database (MongoDB, Redis, SQLAlchemy)

**Rozmiar:** ~5-7 GB
**Zalecane dla:** Pełnego developmentu, ML research

### 2. Minimalne środowisko (`lumenai-minimal`)

**Plik:** `environment-minimal.yml`

Zawiera tylko essentials:
- Core framework (FastAPI, Uvicorn)
- LLM basics (OpenAI, Anthropic, LangChain)
- Database essentials (MongoDB, Redis, ChromaDB)
- WebSocket support
- Basic utilities

**Rozmiar:** ~1-2 GB
**Zalecane dla:** Lekkiego developmentu, testowania, CI/CD

## Użycie z Makefile

```bash
# Wyświetl wszystkie komendy
make help

# Automatyczna instalacja
make mamba-setup

# Utwórz pełne środowisko
make mamba-install

# Utwórz minimalne środowisko
make mamba-minimal

# Zaktualizuj istniejące środowisko
make mamba-update

# Usuń środowiska
make mamba-clean

# Lista środowisk
make mamba-list
```

## Workflow deweloperski

### 1. Pierwsze uruchomienie

```bash
# Instalacja środowiska
make mamba-setup

# Aktywacja
mamba activate lumenai

# Skopiuj i skonfiguruj .env
cp .env.example .env
# Dodaj API keys do .env

# Uruchom backend
make backend-dev
```

W osobnym terminalu:
```bash
# Frontend (nie wymaga Mamba)
make frontend-dev
```

### 2. Codzienna praca

```bash
# Aktywuj środowisko
mamba activate lumenai

# Uruchom backend
cd backend
uvicorn gateway.main:app --reload

# Lub użyj Makefile
make backend-dev
```

### 3. Dodawanie nowych pakietów

**Przez Mamba:**
```bash
mamba activate lumenai
mamba install nazwa-pakietu
```

**Przez pip (w środowisku Mamba):**
```bash
mamba activate lumenai
pip install nazwa-pakietu
```

**Zapisz zmiany:**
```bash
# Eksportuj środowisko
mamba env export > environment-new.yml

# Lub dodaj ręcznie do environment.yml
```

## Zarządzanie środowiskami

### Lista środowisk
```bash
mamba env list
```

### Aktywacja
```bash
mamba activate lumenai
```

### Deaktywacja
```bash
mamba deactivate
```

### Aktualizacja środowiska
```bash
mamba env update -f environment.yml --prune
```

### Usunięcie środowiska
```bash
mamba env remove -n lumenai
```

### Klonowanie środowiska
```bash
mamba create --name lumenai-backup --clone lumenai
```

## Eksport środowiska

### Pełny eksport (z wersjami)
```bash
mamba env export > environment-full.yml
```

### Tylko główne pakiety
```bash
mamba env export --from-history > environment-minimal.yml
```

### Cross-platform (bez build strings)
```bash
mamba env export --no-builds > environment-cross.yml
```

## Docker vs Mamba - kiedy co używać?

### Użyj Mamba gdy:
✅ Rozwijasz lokalnie
✅ Ekserymentujesz z ML modelami
✅ Potrzebujesz Jupyter notebooks
✅ Chcesz szybkich iteracji
✅ Debugujesz kod

### Użyj Docker gdy:
✅ Deployujesz na produkcję
✅ Chcesz pełnej izolacji
✅ Pracujesz w zespole (jednolite środowisko)
✅ Testujesz integracje
✅ Potrzebujesz wszystkich serwisów (MongoDB, Redis, etc.)

### Hybrydowe podejście (Najlepsze!)
```bash
# Development: Mamba
mamba activate lumenai
cd backend && uvicorn gateway.main:app --reload

# Produkcja: Docker
docker-compose up --build
```

## Rozwiązywanie problemów

### Mamba nie instaluje pakietu
```bash
# Spróbuj przez conda
conda install -c conda-forge nazwa-pakietu

# Lub przez pip
pip install nazwa-pakietu
```

### Konflikty zależności
```bash
# Usuń środowisko i utwórz od nowa
mamba env remove -n lumenai
mamba env create -f environment.yml
```

### Wolna instalacja
```bash
# Wyczyść cache
mamba clean --all

# Użyj libmamba solver (jeszcze szybciej)
conda config --set solver libmamba
```

### Środowisko nie aktywuje się
```bash
# Reinicjalizuj shell
conda init bash
source ~/.bashrc

# Lub zsh
conda init zsh
source ~/.zshrc
```

## Zaawansowane

### Tworzenie środowiska dla specific Python version
```bash
mamba create -n lumenai-py310 python=3.10
mamba activate lumenai-py310
mamba install -f environment.yml
```

### Używanie z VS Code
1. Zainstaluj Python extension
2. Ctrl+Shift+P → "Python: Select Interpreter"
3. Wybierz interpreter z środowiska Mamba: `~/miniforge3/envs/lumenai/bin/python`

### Używanie z PyCharm
1. Settings → Project → Python Interpreter
2. Add Interpreter → Conda Environment
3. Wybierz Existing environment: `~/miniforge3/envs/lumenai`

## Performance Tips

1. **Używaj Mamba zamiast Conda** - 10x szybciej
2. **Cache packages** - `mamba clean --all` tylko gdy potrzeba
3. **Używaj `--strict-channel-priority`** dla lepszej rezolucji
4. **Instaluj dużo pakietów naraz** zamiast pojedynczo

## Porównanie rozmiaru

| Środowisko | Rozmiar na dysku | Czas instalacji (Mamba) | Pakiety |
|------------|------------------|-------------------------|---------|
| Minimalne  | ~1.5 GB          | ~3-5 min                | ~150    |
| Pełne      | ~6 GB            | ~10-15 min              | ~350    |

## Najlepsze praktyki

✅ **Jedno środowisko = jeden projekt**
✅ **Zapisuj environment.yml w repo**
✅ **Używaj `--from-history` dla cross-platform**
✅ **Regularnie aktualizuj pakiety**
✅ **Testuj w czystym środowisku przed deployem**

## Linki

- [Mamba Documentation](https://mamba.readthedocs.io/)
- [Miniforge GitHub](https://github.com/conda-forge/miniforge)
- [Conda-forge packages](https://conda-forge.org/)

---

**Pro tip:** Mamba + VS Code + Jupyter = idealne środowisko do ML developmentu! 🚀
