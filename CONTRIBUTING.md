# Run Services Instruction

## Содержание

- [Запуск сервисов локально](#запуск)
- [Запуск сервисов в kubernetes](#Kubernetes)


## Зависимости

- python 3.12.1
- poetry 2.1.4

Установка зависимостей через poetry
```shell
poetry install
```

## Запуск
### Запуск сервисов
Запуск antifraud-service смотреть в contributing.md соответствующего сервиса.

Для запуска можно просмотреть CONTRIBUTING.md расположенный в каждом service,
либо открыть весь проект через workspace vscode`а.
Для этого рядом с данным файлом contributing должен быть файл <file_name>.code-workspace.
Содержание данного файла должно быть таким:
```json
{
	"folders": [
		{
			"path": "./data-service"
		},
		{
			"path": "./flow-selection-service"
		},
		{
			"path": "./scoring-service"
		},
		{
			"path": "./antifraud-service"
		},
		{
			"path": "."
		}
	],
	"settings": {
		"python.defaultInterpreterPath": ".venv/Scripts/python"
	}
}
```
Далее можно будет запускать все тесты через Testing vscode`а.

### Запуск всех сервисов через Docker
Из домашней дериктории проекта
```shell
docker compose up -d --build
```

## Kubernetes
Все манифесты для запуска в домашней директории /home/aabalymov .
Файлы манифестов разложены по папкам своих сервисов в папке manifests.

Для запуска сервиса перейти в нужную папку и ввести:
```
kubectl apply -f . -n test
```

### HELM
Для запуска сервиса при помощи helm использовать папку helm со всеми директория сервисов на сервере, либо папки helm в каждом из сервисов репозитория.
Команда запуска для одноге сервиса:
```sh
helm install -n test <название-релиза> <путь/до/папки/где/лежит/файл/chart.yaml>
```
Пример для data-service:
```sh
helm install -n test data-service-aabalymov helm/data-service
```
Команда удаления образа запущенного при помощи helm:
```sh
helm delete -n test <название-релиза>
```
Пример для data-service:
```sh
helm delete -n test data-service-aabalymov
```
По-умолчанию kubernetes скачивает образы с тэгом 1348db91