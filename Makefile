.PHONY: build run
CONFIG_PATH ?= "$$PWD/example_config.json"
IMAGE_NAME ?= et_discord_bot

all: build test

build:
	docker build . -t ${IMAGE_NAME}

test:
	docker run -v "${CONFIG_PATH}":/app/config.json:ro ${IMAGE_NAME} pytest

run_debug:
	docker run -it -v "${CONFIG_PATH}":/app/config.json:ro ${IMAGE_NAME}
