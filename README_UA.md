# local-dev-rag

**Перевикористовуваний локальний RAG-стек (Retrieval-Augmented Generation) для AI-агентів розробки в рамках кількох програмних проєктів.**

Система індексує артефакти проєкту — документацію, архітектурні рішення (ADR), OpenAPI-специфікації, вихідний код та міграції бази даних — у локальну векторну базу даних. AI-агенти (Cursor, VS Code + Roo Code) запитують цей індекс через MCP-інструменти перед внесенням змін до коду чи архітектури, отримуючи актуальний контекст, специфічний для проєкту, замість покладання виключно на загальні знання з тренування.

---

## Стек технологій

| Компонент | Роль |
|---|---|
| **Qdrant** | Локальна векторна база даних. Зберігає та обслуговує embedding-вектори для семантичного пошуку. |
| **LM Studio** | Локальний OpenAI-сумісний сервер ембедингів. Генерує текстові ембединги без залежності від хмарних сервісів. |
| **FastMCP** | MCP (Model Context Protocol) сервер. Надає RAG-пошук як інструменти, доступні для Cursor/Roo Code. |
| **uv** | Менеджер пакетів Python і віртуального середовища. Замінює pip + venv. |
| **watchfiles** | Спостерігач за файловою системою. Запускає інкрементальну переіндексацію під час розробки. |

---

## 1. Архітектура

```
Cursor / VS Code + Roo Code / Continue
        |
        | MCP-виклики (search_project_docs, search_project_code)
        v
MCP-сервер local-dev-rag
        |
        | семантичний векторний пошук
        v
Qdrant
  ├── rag_docs_knowledge    (документація, ADR, OpenAPI-специфікації, архітектура)
  └── rag_code_knowledge    (вихідний код, міграції, тести)
        ^
        |
Індексер / Watcher          (читає файли проєкту, генерує ембединги, записує у Qdrant)
        ^
        |
Файли проєкту
  ├── docs/
  ├── ADR/
  ├── OpenAPI specs
  ├── вихідний код
  └── міграції
```

### Колекції Qdrant

| Колекція | Вміст |
|---|---|
| `rag_docs_knowledge` | Markdown-документи, ADR, архітектурні файли, документація дизайн-системи, OpenAPI-специфікації |
| `rag_code_knowledge` | Файли вихідного коду, SQL-міграції, тести, реалізація frontend/backend |

### Схема метаданих чанку

Кожен індексований чанк зберігається в Qdrant з таким набором метаданих:

| Поле | Опис |
|---|---|
| `project_id` | Унікальний ідентифікатор проєкту-джерела |
| `project_name` | Людино-читабельна назва проєкту |
| `workspace_path` | Абсолютний шлях до кореня проєкту на диску |
| `knowledge_type` | `docs` або `code` |
| `reusable_scope` | Чи є чанк специфічним для проєкту, чи загально перевикористовуваним |
| `source_path` | Відносний шлях до файлу-джерела |
| `language` | Мова програмування або розмітки |
| `module` | Логічний модуль або підсистема в межах проєкту |
| `content_hash` | SHA-хеш вмісту чанку; використовується watcher'ом для виявлення змін |
| `content` | Власне текст чанку |

---

## 2. Вимоги до середовища виконання

### Для повноцінної роботи RAG необхідно:

1. Docker (запущений)
2. Контейнер Qdrant (запущений у Docker)
3. LM Studio Local Server (запущений)
4. Модель ембедингів, завантажена у LM Studio
5. *(Опційно)* Процес watcher'а — для реального часу переіндексації
6. *(Опційно)* MCP-сервер — запускається автоматично Cursor/Roo за потреби

### Мінімум для індексування:
```
Docker + Qdrant + точка доступу LM Studio embeddings
```

### Мінімум для MCP-пошуку з Cursor/Roo:
```
Qdrant + точка доступу LM Studio embeddings + MCP-сервер
```

---

## 3. Початкове налаштування

### 3.1 Встановлення uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
uv --version
```

### 3.2 Встановлення Python-залежностей

З кореня проєкту:

```bash
uv sync
```

Якщо залежності відсутні, додайте їх явно:

```bash
uv add fastmcp qdrant-client openai python-dotenv pydantic pyyaml watchfiles
uv add --dev pytest
```

### 3.3 Створення файлу `.env`

Скопіюйте приклад:

```bash
cp .env.example .env
```

Заповніть значення:

```env
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=замініть-на-локальний-секрет

DOCS_COLLECTION=rag_docs_knowledge
CODE_COLLECTION=rag_code_knowledge

EMBEDDING_BASE_URL=http://localhost:1234/v1
EMBEDDING_API_KEY=lm-studio
EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5

PROJECTS_CONFIG=./config/projects.yaml
```

Згенеруйте випадковий локальний API-ключ для Qdrant:

```bash
openssl rand -hex 32
```

Використовуйте однаковий ключ у `.env` і `docker-compose.yml`.

---

## 4. Конфігурація проєктів

Проєкти оголошуються у `config/projects.yaml`. Кожен запис визначає, які файли індексувати для документації та коду, за допомогою glob-шаблонів.

```yaml
projects:
  - project_id: customui
    project_name: CustomUI
    workspace_path: /абсолютний/шлях/до/customui
    tags:
      - fastapi
      - react
      - typescript
      - postgresql
    docs:
      include:
        - docs/**/*.md
        - apps/**/openapi*.json
      exclude:
        - "**/.env*"
        - "**/secrets/**"
        - "**/node_modules/**"
    code:
      include:
        - apps/**/*.py
        - apps/**/*.ts
        - apps/**/*.sql
      exclude:
        - "**/node_modules/**"
        - "**/.venv/**"
        - "**/dist/**"
        - "**/.git/**"

  - project_id: _global
    project_name: Global Engineering Knowledge
    workspace_path: /абсолютний/шлях/до/global-knowledge
    tags:
      - architecture
    docs:
      include:
        - "**/*.md"
      exclude:
        - "**/.env*"
    code:
      include: []
      exclude: []
```

> Використовуйте `_global` для перевикористовуваних інженерних знань (патерни, стандарти, конвенції). Не розміщуйте там специфічну доменну логіку проєкту.

---

## 5. Lifecycle-скрипти

Всі операційні команди обгорнуті в shell-скрипти у директорії `scripts/`. Зробіть їх виконуваними один раз:

```bash
chmod +x scripts/*.sh
```

| Скрипт | Дія |
|---|---|
| `rag-up.sh` | Запустити контейнер Qdrant + забезпечити наявність колекцій |
| `rag-down.sh` | Зупинити контейнер Qdrant (дані зберігаються) |
| `rag-restart.sh` | Повний перезапуск: down → up → забезпечення колекцій |
| `rag-index-all.sh` | Проіндексувати всі проєкти з `projects.yaml` |
| `rag-index-project.sh <id>` | Проіндексувати один проєкт за `project_id` |
| `rag-watch.sh` | Запустити watcher для реального часу |
| `rag-test.sh [project_id]` | Запустити тестовий набір проти живих сервісів |
| `rag-status.sh` | Вивести інформацію про колекції Qdrant і список моделей LM Studio |
| `rag-clear-project.sh <id>` | Видалити всі точки Qdrant для конкретного проєкту |
| `rag-clear-all.sh` | ⚠️ Знищити всі дані Qdrant і відтворити порожні колекції |

### Рекомендований чистий старт

```bash
./scripts/rag-up.sh
# Потім вручну запустіть LM Studio Local Server
```

### Ручна послідовність запуску

```bash
# 1. Запустити Qdrant
docker compose up -d

# 2. LM Studio → Developer / Local Server → Start Server
# Завантажте модель: text-embedding-nomic-embed-text-v1.5

# 3. Перевірити відповідь LM Studio
curl http://localhost:1234/v1/models

# 4. Створити колекції Qdrant (ідемпотентна операція)
uv run python -m local_dev_rag.qdrant_admin

# 5. Запустити повну індексацію
uv run python -m local_dev_rag.indexer

# 6. (Опційно) Запустити watcher
uv run python -m local_dev_rag.watcher
```

### Зупинка

```bash
./scripts/rag-down.sh
# або: docker compose down
```

Постійні дані Qdrant зберігаються у `data/qdrant/` і переживають перезапуски контейнера.

---

## 6. Індексування

### Повна індексація

Запускайте при: першому налаштуванні, додаванні нового проєкту, масових змінах файлів, якщо watcher не працював, або після відновлення даних Qdrant.

```bash
./scripts/rag-index-all.sh
```

### Індексація одного проєкту

Запускайте коли: змінився тільки один проєкт або оновились правила include/exclude.

```bash
./scripts/rag-index-project.sh customui
```

### Реальночасова інкрементальна індексація (watcher)

Запускайте під час активної розробки для автоматичного підтримання індексу в актуальному стані.

```bash
./scripts/rag-watch.sh
```

**Логіка роботи watcher'а:**

1. Виявляє події файлової системи
2. Застосовує debounce-затримку для уникнення зайвих операцій
3. Обчислює `content_hash` для змінених файлів
4. Пропускає файли, хеш яких не змінився
5. Видаляє старі точки Qdrant для зміненого файлу
6. Вставляє нові чанки з ембедингами

### Коли повторно запускати `qdrant_admin`

Запускайте лише у цих випадках — не при кожній зміні вихідних файлів:

- Перше налаштування
- Колекції були видалені
- Змінилась модель ембедингів і розмірність вектора
- Змінилась схема або конфігурація індексів колекції

```bash
uv run python -m local_dev_rag.qdrant_admin
```

---

## 7. Очищення даних

### Очистити один проєкт

Видаляє всі точки Qdrant з `project_id = <id>` з обох колекцій. Використовуйте коли змінився шлях до проєкту, проєкт видалено або потрібна чиста переіндексація.

```bash
./scripts/rag-clear-project.sh customui
```

### Очистити всі дані ⚠️

Знищує `data/qdrant/` і відтворює порожні колекції. Використовуйте лише коли змінилась розмірність моделі ембедингів, дані пошкоджені або потрібна повна перебудова.

```bash
./scripts/rag-clear-all.sh
# Потім:
./scripts/rag-up.sh
./scripts/rag-index-all.sh
```

---

## 8. Перевірка стану

### Перевірка колекцій Qdrant

```bash
./scripts/rag-status.sh
# або вручну:
curl http://localhost:6333/collections -H "api-key: $QDRANT_API_KEY"
```

Очікується: обидві колекції `rag_docs_knowledge` і `rag_code_knowledge` присутні.

### Перевірка LM Studio

```bash
curl http://localhost:1234/v1/models
```

Очікується: модель ембедингів присутня у відповіді.

### Перевірка розмірності ембедингів

```bash
uv run python -c "from local_dev_rag.embeddings import get_embedding_dimension; print(get_embedding_dimension())"
```

Очікується: ціле число (наприклад, `768`). Повинно збігатись із розміром вектора в колекціях Qdrant.

### Перевірка кількості точок у колекції

```bash
curl http://localhost:6333/collections/rag_code_knowledge -H "api-key: $QDRANT_API_KEY"
```

Очікується: `points_count > 0` після індексації.

---

## 9. Запуск тестів

Тести перевіряють повний живий стек. Передумови перед запуском:

1. Контейнер Qdrant запущений
2. LM Studio Local Server запущений
3. Модель ембедингів завантажена
4. Колекції існують
5. Індексація вже виконувалась принаймні один раз

```bash
./scripts/rag-test.sh customui
# або:
TEST_PROJECT_ID=customui uv run pytest -v
```

**Покриття тестів:**

- Доступність Qdrant
- Наявність і непустота необхідних колекцій
- Доступність точки ембедингів
- Відповідність розмірності ембедингів розміру вектора в Qdrant
- RAG-запити для `docs` і `code` повертають результати
- Payload містить усі необхідні поля метаданих
- Секрети відсутні в індексованому вмісті
- MCP-функції повертають валідні результати

---

## 10. MCP-сервер

MCP-сервер надає RAG-функціональність у вигляді інструментів, які можуть викликати Cursor/Roo Code. Зазвичай запускається автоматично середовищем розробки, але може бути запущений вручну:

```bash
uv run python -m local_dev_rag.server
```

### Доступні MCP-інструменти

| Інструмент | Опис |
|---|---|
| `list_rag_projects` | Список усіх проіндексованих проєктів |
| `search_project_docs` | Семантичний пошук по документації, ADR, OpenAPI-специфікаціях |
| `search_project_code` | Семантичний пошук по вихідному коду та міграціях |
| `get_rag_usage_policy` | Повертає рекомендовану політику використання агентом |

### Рекомендована поведінка агента

- Перед змінами архітектури, API, бази даних, деплою або UI → викликати `search_project_docs`
- Перед редагуванням вихідного коду → викликати `search_project_code`, потім відкрити реальний файл

---

## 11. Інтеграція з IDE

### Cursor

Створіть `<корінь_проєкту>/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "local-dev-rag": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/абсолютний/шлях/до/local-dev-rag",
        "python",
        "-m",
        "local_dev_rag.server"
      ],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_API_KEY": "замініть-на-локальний-секрет",
        "DOCS_COLLECTION": "rag_docs_knowledge",
        "CODE_COLLECTION": "rag_code_knowledge",
        "EMBEDDING_BASE_URL": "http://localhost:1234/v1",
        "EMBEDDING_API_KEY": "lm-studio",
        "EMBEDDING_MODEL": "text-embedding-nomic-embed-text-v1.5",
        "PROJECTS_CONFIG": "/абсолютний/шлях/до/local-dev-rag/config/projects.yaml"
      }
    }
  }
}
```

> Не комітьте `.cursor/mcp.json`, якщо він містить локальні абсолютні шляхи або секрети.

### VS Code + Roo Code

Налаштуйте через: Roo Code sidebar → MCP Servers → Configure MCP Servers. Використовуйте ту саму JSON-структуру.

**Рекомендована кастомна інструкція для Roo:**

```
Використовуй local-dev-rag перед змінами цього проєкту. Використовуй project_id="customui".

Перед редагуванням вихідного коду:
1. Викличи search_project_code
2. Перевір source_path і діапазон рядків у результатах
3. Відкрий реальний файл у VS Code
4. Редагуй лише після перевірки реального файлу

Перед архітектурними/дизайнерськими/API/БД/деплой-рішеннями:
1. Викличи search_project_docs
2. Надавай перевагу специфічним знанням проєкту над глобальними перевикористовуваними
```

---

## 12. Pipeline переранжування

Pipeline пошуку використовує **двоетапну архітектуру** для підвищення якості результатів:

```
запит
  → ембединг
  → векторний пошук Qdrant   (щільний пошук, топ RETRIEVAL_TOP_K кандидатів)
  → cross-encoder reranker   (перевизначає рейтинг за семантичною релевантністю)
  → фільтрація за порогом    (відсіває результати нижче RERANK_THRESHOLD)
  → фінальні результати      (топ RERANK_TOP_K)
```

Переранжування особливо корисне для довгих документів, неоднозначних запитів та перекриваючих чанків.

### Конфігурація

```env
ENABLE_RERANK=true
RETRIEVAL_TOP_K=50
RERANK_TOP_K=3
RERANK_THRESHOLD=0.5
```

| Змінна | Опис |
|---|---|
| `ENABLE_RERANK` | Увімкнути або вимкнути етап переранжування |
| `RETRIEVAL_TOP_K` | Кількість кандидатів, отриманих з Qdrant для переранжування |
| `RERANK_TOP_K` | Кількість фінальних результатів після переранжування |
| `RERANK_THRESHOLD` | Мінімальна оцінка реранкера для включення результату |

### Модель переранжування за замовчуванням

```
BAAI/bge-reranker-base
```

Модель завантажується автоматично при першому використанні (~100 МБ – 1 ГБ залежно від варіанту моделі).

### Компроміси

| Режим | Точність | Затримка |
|---|---|---|
| Переранжування увімкнено | Вища, менше шуму | ~1–5 сек (CPU) |
| Переранжування вимкнено | Нижча, більше шуму | ~100–300 мс |

### Налаштування

```env
# Підвищити recall (більше кандидатів)
RETRIEVAL_TOP_K=80

# Підвищити точність (суворіший поріг, менше результатів)
RERANK_THRESHOLD=0.6
RERANK_TOP_K=2

# Вимкнути переранжування для швидших відповідей
ENABLE_RERANK=false

# Кеш для зберігання ембедингів
RERANK_CACHE_DIR=.cache/fastembed
```

**Примітки:**
- Оцінка реранкера не залежить від cosine-similarity score Qdrant.
- Порогова фільтрація застосовується після переранжування.
- Якщо всі результати нижче порогу, fallback повертає топ-результати без фільтрації.

---

## 13. Типові проблеми

### LM Studio: відмова з'єднання

**Причина:** LM Studio Local Server не запущений.  
**Рішення:** LM Studio → Developer / Local Server → Start Server.  
**Перевірка:** `curl http://localhost:1234/v1/models`

### Continue: модель не завантажена

**Причина:** Chat/completion модель не завантажена в LM Studio.  
**Рішення:** Завантажте chat-модель у LM Studio, запустіть Local Server, перевірте через `/v1/models`.

### Qdrant: API-ключ з небезпечним з'єднанням

Прийнятно для локальної розробки. Для продакшну або віддаленого доступу використовуйте HTTPS або приватну мережу.

### Невідповідність розміру вектора

**Причина:** Модель ембедингів змінилась і генерує вектори іншої розмірності.  
**Рішення:**
```bash
./scripts/rag-clear-all.sh
./scripts/rag-index-all.sh
```

### VS Code: помилки імпорту / підкреслені імпорти

**Рішення:** `Ctrl+Shift+P` → Python: Select Interpreter → виберіть `.venv/bin/python`, потім запустіть `uv sync`.

### Реранкер не працює

```bash
uv add fastembed
```

---

## 14. Опційно: підтримка CLI для індексації одного проєкту

Якщо `indexer.py` ще не підтримує аргумент `--project-id`, додайте точку входу:

```python
# src/local_dev_rag/indexer.py

import argparse

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--docs-only", action="store_true")
    parser.add_argument("--code-only", action="store_true")
    args = parser.parse_args()

    include_docs = not args.code_only
    include_code = not args.docs_only

    if args.project_id:
        index_project(args.project_id, include_docs=include_docs, include_code=include_code)
    else:
        for project in load_projects():
            index_project(project.project_id, include_docs=include_docs, include_code=include_code)
```

Для очищення конкретного проєкту додайте `src/local_dev_rag/clear_project.py`, що використовує `qdrant_client.delete()` з фільтром по `project_id`.

---

## 15. Python-інтерпретатор у VS Code

Якщо імпорти модулів підкреслені як помилки:

```
Ctrl+Shift+P → Python: Select Interpreter → .venv/bin/python
```

Перевірка:

```bash
uv run python -c "from local_dev_rag.settings import get_settings; print('OK')"
```

---

## 16. Контроль версій: що комітити

### Комітити

```
pyproject.toml
uv.lock
docker-compose.yml
src/
tests/
scripts/
config/projects.yaml   # лише якщо не містить секретів
.env.example
README.md
.gitignore
```

### НЕ комітити

```
.env                   # містить секрети та локальні шляхи
.venv/                 # Python-віртуальне середовище
data/qdrant/           # дані локальної векторної бази
.cursor/               # IDE-конфіг з локальними шляхами
*.code-workspace
secrets/
приватні ключі
```

---

## 17. Рекомендований щоденний робочий процес

```bash
# 1. Запустити Qdrant і забезпечити наявність колекцій
./scripts/rag-up.sh

# 2. Вручну запустити LM Studio Local Server

# 3. Перевірити всі сервіси
./scripts/rag-status.sh

# 4. Проіндексувати всі проєкти (один раз або після змін)
./scripts/rag-index-all.sh

# 5. Під час розробки: тримати watcher запущеним
./scripts/rag-watch.sh

# 6. Запустити тести для валідації стеку
./scripts/rag-test.sh customui

# 7. Кінець сесії: зупинити Qdrant
./scripts/rag-down.sh
```
