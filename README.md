# smartArg
Система мониторинга и интеллектуальной обработки сообщений учебных Telegram‑чатов.

smartArg автоматически собирает сообщения из групп и каналов Telegram, анализирует их с помощью локальной LLM (Ollama) и векторной базы (Qdrant), извлекает важные объявления, дедлайны, ссылки и структурирует их в базу знаний. Проект полезен студентам и преподавателям: помогает не пропускать важную информацию и хранить историю задач в удобном виде.

Снапшоты страницы загружаются при запуске локльного репозитория т.к. pythonanywhere не даёт достаточных мощностей, а крутить полный проект на своих мощностях я, к сожалению, не могу себе позволить. https://justerror40.github.io/smartArg/

## Технологии
* **Python 3.10**
* **Django 4.2**
* **Celery + Redis** — асинхронная обработка задач
* **PostgreSQL** — основная база данных
* **Aiogram** — Telegram bot (polling)
* **Ollama** — локальная LLM / эмбеддинги (nomic-embed-text-v2-moe)
* **Qdrant** — векторная база для семантического поиска
* **langchain, qdrant-client, langchain-ollama** — интеграция с LLM и векторной БД

## Скриншоты


<img width="1997" height="1402" alt="изображение" src="https://github.com/user-attachments/assets/08531235-477b-47f2-aca9-84c91647e456" />


<img width="2253" height="1220" alt="изображение" src="https://github.com/user-attachments/assets/d20d0a61-165a-47d8-bac8-f49e1b45797d" />


## Как запустить проект локально (Docker Compose)
Инструкция предназначена для разработчика, который хочет развернуть проект локально в контейнерах.

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/smartArg.git
cd smartArg
```

2. (Рекомендуется) создайте файл `.env` в корне и задайте секреты:
```text
TELEGRAM_BOT_TOKEN=123456:ABCDEF
AI_PROVIDER=ollama
AI_BASE_URL=http://ollama:11434/v1
AI_MODEL_NAME=nomic-embed-text-v2-moe
QDRANT_URL=http://qdrant:6333
DATABASE_URL=postgres://postgres:postgres@db:5432/telegram_analyzer
```

3. Сборка и запуск всех сервисов (Docker Compose):
```bash
docker compose up -d --build
```

4. Примените миграции и создайте суперпользователя (если нужно):
```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

5. Логи и проверка работы бота:
```bash
docker compose logs -f bot
```

6. Откройте веб-интерфейс:
Перейдите: http://127.0.0.1:8000/

## Быстрая локальная проверка (альтернатива без Docker)
1. Создайте виртуальное окружение и активируйте его.
2. Установите зависимости:
```bash
pip install -r requirements.txt
```
3. Настройте переменные окружения аналогично `.env` и выполните миграции.

## Архитектура (кратко)
* `bot/` — обработчики Telegram-сообщений (`Aiogram`).
* `analysis/` — AI-слой: промпты, LLM-интеграция, логика обработки и структура базы знаний.
* `core/` — общие модели: `Chat`, `Message`.
* `web/` — Django views и шаблоны для отображения задач и базы знаний.
* `analysis/vector_db.py` — интеграция с Qdrant и генерация/поиск эмбеддингов через Ollama.

## Как это работает (рабочий поток)
1. Бот получает сообщения и сохраняет их в БД.
2. Когда определяется сообщение от преподавателя или ответ преподавателя на вопрос — формируется `IngestionData` и ставится в очередь Celery.
3. Worker вызывает `AIService`, который отправляет контент в Ollama и получает структурированный JSON (название задачи, дедлайны, ссылки, действие: new/update/cancel и т.д.).
4. Система ищет похожие задачи в Qdrant по эмбеддингу; если находится совпадение — задача обновляется, иначе создаётся новая `CourseTask`.
5. Все найденные детали записываются в `KnowledgeEntry` и отображаются в веб-интерфейсе.

## Команды управления (Docker)
```bash
# Запустить сервисы
docker compose up -d --build

# Просмотр логов бота
docker compose logs -f bot

# Выполнить миграции
docker compose exec web python manage.py migrate

# Остановить все сервисы
docker compose down
```

## Тестирование
Запустить тесты Django внутри контейнера `web`:
```bash
docker compose exec web python manage.py test
```

## Ограничения и идеи для улучшения
* UI можно расширить (редактирование задач, история изменений, фильтры по дате и приоритету).
* Поддержка вебхуков для Telegram вместо polling — для продакшн-окружения.
* Улучшение логики слияния/обновления задач (учёт переносов дедлайнов и версионность).

## Авторы и контакты
* Автор: Батуев Тимофей
* Email: tim@batuev.com

## Лицензия
MIT — смотрите файл `LICENSE`.
# smartArg
Система сбора и классификации данных по открытым источникам с подсветкой важных событи 
