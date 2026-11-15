# Архитектура Veridion

## ADR-01 · Модульный монолит с отдельным процессом импорта

Один FastAPI-сервис реализует права, поиск и исследовательские операции. Worker выполняет ограниченный по размеру импорт с очередью PostgreSQL. Воркер захватывает задание через FOR UPDATE SKIP LOCKED. При обрыве транзакции задание снова доступно. Исходные байты небольших документов хранятся в PostgreSQL. Это позволяет сохранить байты и версию атомарно.

## ADR-02 · Историческая доступность и происхождение

SHA-256 вычисляется по исходному файлу. Диапазоны фрагментов относятся к нормализованному Unicode-тексту редакции, с нуля и с исключённой правой границей. PostgreSQL блокирует изменение и удаление редакций и фрагментов. Повторная загрузка учитывает хеш в пределах источника. Индекс идентифицируется версией модели и фрагментации.

## ADR-03 · Два независимых ранга

Запрос ограничивается проектом и множеством выбранных версий до ранжирования. Лексика использует tsvector и ts_rank_cd. Семантика использует multilingual-e5-small и точную косинусную дистанцию pgvector. Гибрид соединяет позиции по reciprocal rank fusion с k=60. Точное сравнение подходит для демонстрационного корпуса. Модель и ревизия входят в метаданные запуска.

## ADR-04 · Цитирование и граница доверия

Локальный Ollama подключается явно. Он получает ограниченный контекст без инструментов и секретов. Ответ проходит независимую проверку структуры и ссылок по идентификаторам из разрешённого контекста. Статус технической целостности и оценка поддержки хранятся отдельно. Извлекающий режим строит результат по сохранённым фрагментам и детерминированным правилам. Для сложной семантики нужен проверяющий.

## ADR-05 · Согласование и воспроизводимость

Решение проверяющего хранится отдельно от ответа. Проверка ревизии и запись решения выполняются под блокировкой записи ответа. Снимок включает параметры, фрагменты, вывод и историю согласования. Исторический снимок доступен для сравнения. Повторный вызов модели может дать другой текст.

## Threat model

| Граница | Риск | Контроль |
| --- | --- | --- |
| Запрос → данные | Доступ к чужому проекту | Членство и проект в запросах к объектам |
| Файл → worker | Избыточная распаковка, запуск активного содержимого | Лимиты, текстовые парсеры, обработка HTML как текста |
| Документ → модель | Инструкция внутри цитируемого текста | Ограниченный контекст локальной модели без инструментов и строгая проверка ссылок |
| Согласование → история | Конкурирующие изменения, перезапись решения | Блокировка, номер ревизии и журнал |

## Access matrix

| Operation | RESEARCHER | ANALYST | REVIEWER | ADMIN |
| --- | --- | --- | --- | --- |
| Read project sources and run analyses | Yes | Yes | Yes | Yes |
| Import, archive, create report or snapshot | Yes | — | — | Yes |
| Submit an answer for review | Yes | Yes | Yes | Yes |
| Record a final decision or request further evidence | — | — | Yes | Yes |
| Assign project roles and inspect audit | — | — | — | Yes |

The application-level admin flag additionally permits user creation. Every project operation still requires membership.

## Ingestion and evidence specifications

The worker decodes or extracts visible text, applies Unicode NFC and collapses whitespace inside lines. The source version keeps raw bytes and SHA-256. Chunks have a 780-character window and nominal 110-character overlap, adjusted to a word boundary when available. Markdown and HTML use blocks and headings, PDF keeps page positions and DOCX keeps paragraph text and heading styles. A parse failure rolls back the version and all dependent rows and completes the job with a generic error. Duplicate content is scoped to the source. An archived source remains available through its historical reference.

The application constructs citations from persisted chunks and compares their quote, hash, offsets and run context to the requested version. Technical integrity remains valid for an unchanged historical excerpt. Category, modality and shared analytical conditions are separate inputs to support assessment. Comparing a target with an observation produces a different-modality classification. A different release or time period is a different context. Conflicting observations with matching context need human review.

[Context and containers](../diagrams/context.mmd) · [Storage model](../diagrams/model.mmd) · [Ingestion sequence](../diagrams/ingestion.mmd) · [Answer sequence](../diagrams/question.mmd) · [Citation sequence](../diagrams/verification.mmd) · [Review sequence](../diagrams/review.mmd) · [State machines](../diagrams/lifecycle.mmd)

The local embedding artifact comes from the [Multilingual E5 model card](https://huggingface.co/intfloat/multilingual-e5-small) and the [ONNX conversion](https://huggingface.co/Xenova/multilingual-e5-small/tree/761b726dd34fb83930e26aab4e9ac3899aa1fa78/onnx). The local generative adapter uses the [Ollama chat API](https://docs.ollama.com/api/chat).
