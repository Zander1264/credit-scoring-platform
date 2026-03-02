# Run Servive Instruction

## Содержание

- [Запуск](#запуск)


## Зависимости

- python 3.12.1
- poetry 2.1.4

Установка зависимостей через poetry
```shell
poetry install
```

## Запуск

Перед запуском нужно либо переоткрыть проект так что-бы домащней дерикторией было
```
scoring-service
```
либо прописать в консоли это:

```shell
cd scoring-service
.venv\Scripts\activate
set PYTHONPATH=%CD%\src;%PYTHONPATH%
```
Тесты
```shell
pytest
```
Обычный запуск
```shell
python src\app\service.py --config config.yaml
```



