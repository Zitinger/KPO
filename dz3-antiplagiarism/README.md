# Домашнее задание №3 - Синхронное межсервисное взаимодействие
#### Дьяков Иван Михайлович - БПИ 244

---

Программа написана на Python (FastAPI), + Docker / docker-compose - 
3 сервиса (2 бизнес‑микросервиса + API Gateway) - 
Доп. требование на 10 баллов: облако слов через QuickChart Word Cloud API

По ТЗ студент отправляет **файл работы** на проверку, система фиксирует факт сдачи в СУБД 
(кто / когда / по какому заданию), сохраняет файл на сервере. После загрузки запускается анализ, 
создается отчет и тоже сохраняется локально на сервере.

---

## 1) Структура проекта

```
dz3-antiplagiarism/
  docker-compose.yml
  requirements.txt
  .gitignore

  api_gateway/             # API Gateway (единая точка входа)
    app.py
    Dockerfile

  file_storing_service/    # бизнес‑сервис 1: хранение работ (файлы + метаданные)
    app.py
    Dockerfile

  file_analysis_service/   # бизнес‑сервис 2: анализ (антиплагиат + отчеты)
    app.py
    Dockerfile

  db/                      # локальные базы SQLite (создаются при запуске, если их нет)
    .gitkeep
    file_storing.db        
    file_analysis.db      

  storage/
    file_storing/          # локальное хранилище файлов работ
      .gitkeep 
      [unique_id]_[orig_filename]      
```

---

## 2) Как запустить (Docker)

### 2.1 Требования

- установлен Docker
- установлен docker compose (плагин)

### 2.2 Запуск

В корне проекта:

```
docker compose up --build
```

Остановка:

```
docker compose down
```

### 2.3 Swagger

Требование выполнено через Swagger (`/docs`) у каждого сервиса:

- **API Gateway:** `http://localhost:8080/docs`
- **File Storing Service:** `http://localhost:8081/docs`
- **File Analysis Service:** `http://localhost:8082/docs`

---

## 3) Архитектура системы

Система состоит из 3 сервисов:

### 3.1 API Gateway (порт 8080)

Единая точка входа для клиента. AG
- принимает загрузку файла от студента
- пересылает файл в сервис хранения
- запускает анализ в сервисе анализа
- собирает ответ и отдает клиенту
- если внутренний сервис недоступен возвращает 503

### 3.2 File Storing Service (порт 8081)

Хранит:
- файл работы на диске (локально на сервере)
- факт сдачи и метаданные в SQLite (кто/когда/по какому заданию + путь к файлу)

### 3.3 File Analysis Service (порт 8082)

Делает:
- скачивает файл работы из File Storing Service
- извлекает текст (/md/csv/json/xml/yaml/txt + docx + pdf)
- сравнивает работу с другими работами
- сохраняет отчет в SQLite (и хранит историю отчетов)

---

## 4) Пользовательские сценарии

### Сценарий A - студент сдает работу на проверку
1) Студент вызывает ***API Gateway***: `POST /works` (multipart/form-data: `student_id`, `title`, `file`) 
2) Gateway отправляет файл в ***File Storing Service***: `POST /works` 
3) File Storing Service:
   - сохраняет файл в `./storage/file_storing/`
   - создает запись в SQLite `works` (кто/когда/по какому заданию + путь к файлу)
4) Gateway запускает анализ в ***File Analysis Service***: `POST /reports` с `work_id` 
5) File Analysis Service:
   - скачивает файл: `GET` из File Storing Service (`/works/{id}/file`)
   - считает отчет и сохраняет его в SQLite `reports`
6) Gateway возвращает студенту JSON: `work + report`

---

### Сценарий B - преподаватель получает последний отчет по работе

В API Gateway: - 
`GET /works/{work_id}/report` -> возвращает `work + последний report`.

---

### Сценарий C - преподаватель получает *все* отчеты по работе (история отчетов)

В API Gateway: - 
`GET /works/{work_id}/reports` -> возвращает `work + список reports[]`, где у каждого отчета есть:
- `status` (например, `"OK"` или `"PLAGIARISM"`)
- `is_plagiarism` (true / false)

---

### Сценарий D - преподаватель скачивает исходный файл работы

В API Gateway: - 
`GET /works/{work_id}/file` -> скачивает сохраненный файл.

---

## 5) Технические сценарии микросервисов

### 5.1 API Gateway - основные эндпоинты

- `POST /works` - принять файл, сохранить, запустить анализ, вернуть отчет
- `GET /works` - список работ (метаданные)
- `GET /works/{id}` - метаданные конкретной работы
- `GET /works/{id}/file` - скачать файл
- `GET /works/{id}/report` - последний отчет
- `GET /works/{id}/reports` - история отчетов по работе

Gateway не хранит данные у себя, он только маршрутизирует запросы и собирает ответы.

---

### 5.2 File Storing Service - хранение работ

- `POST /works` - сохранить файл на диск + записать метаданные в SQLite
- `GET /works` - список метаданных всех работ
- `GET /works/{id}` - метаданные работы
- `GET /works/{id}/file` - выдать сохраненный файл

**Таблица works (SQLite):**
- `student_id` - кто сдал
- `title` - по какому заданию
- `created_at` - когда
- `original_filename`, `content_type`, `file_size`, `file_path` - что именно сохранили

---

### 5.3 File Analysis Service - анализ и отчеты

- `POST /reports` - сделать анализ по `work_id` и сохранить новый отчет
- `GET /reports` - список отчетов (для просмотра)
- `GET /reports/{work_id}` - последний отчет по работе
- `GET /reports/{work_id}/all` - все отчеты по работе (история)

**Таблица reports (SQLite):**
- `work_id`
- `plagiarism_score` (проценты)
- `max_similarity_work_id` (id самой похожей работы или null)
- `word_count`, `unique_word_count`
- `wordcloud_url`
- `created_at`

---

## 6) Алгоритм определения плагиата

Алгоритм работает через коэффициент Жаккара:

1) Из файла извлекается текст:
- `./.md/.csv/.json/.xml/.yml/.yaml/.txt` -> просто декодируем в текст
- `.docx` -> читаем параграфы
- `.pdf` -> извлекаем текст со страниц

2) Токенизация:
- берем все слова
- приводим к нижнему регистру

3) Для сравнения используем **коэффициент Жаккара** по множествам уникальных слов:

**sim(A, B) = |A ∩ B| / |A ∪ B|**

Где `A` - множество уникальных слов текущей работы, `B` - другой работы.

4) Берем максимальную схожесть со всеми другими работами:
- `plagiarism_score = sim_max * 100`
- `max_similarity_work_id` - id самой похожей работы

5) Флаг и статус:
- порог берется из `PLAGIARISM_THRESHOLD` (по умолчанию 50%, можно изменить env PLAGIARISM_THRESHOLD в docker-compose)
- если `plagiarism_score >= threshold` -> `is_plagiarism=true`, `status="PLAGIARISM"`
- иначе -> `is_plagiarism=false`, `status="OK"`

---

## 7) Облако слов (QuickChart Word Cloud API)

В json отчета есть поле `wordcloud_url`. Это ссылка на картинку облака слов.
Ее можно просто открыть в браузере.

---

## 8) Примеры запросов (через curl)

### Загрузка файла через API Gateway
```
curl -X POST "http://localhost:8080/works" \
  -F "student_id=ivanov" \
  -F "title=KR-1 Teorver" \
  -F "file=@./my_work.pdf"
```

### Последний отчет по работе
```
curl "http://localhost:8080/works/1/report"
```

### Все отчеты по работе (история)
```
curl "http://localhost:8080/works/1/reports"
```

### Скачать файл работы
```
curl -OJ "http://localhost:8080/works/1/file"
```

---

## 9) Ошибки и отказ одного из сервисов

Если один из внутренних сервисов недоступен (не запущен / упал / не отвечает),
то API Gateway возвращает:

- `503 Service Unavailable`
- текст ошибки вида: `"Один из внутренних сервисов недоступен"`

Также:
- если `work_id` не существует -> `404 Not Found`

---

## 10) Примечания

- Сейчас хранение файла сделано локально на сервере (папка `storage/`) 
- Проект рассчитан на запуск через Docker Compose.