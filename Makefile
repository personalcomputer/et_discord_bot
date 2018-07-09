.PHONY: build run
CONFIG_PATH ?= "$$PWD/test_config.json"
IMAGE_NAME ?= et_discord_bot
DOCKER_CONFIG_MOUNT_ARGS = -e CONFIG_PATH=/etc/et_discord_bot/config.json -v "${CONFIG_PATH}":/etc/et_discord_bot/config.json:ro

all: build test

build:
	docker build . -t ${IMAGE_NAME}

test:
	docker run -it ${DOCKER_CONFIG_MOUNT_ARGS} ${IMAGE_NAME} pytest

run_debug:
	docker run -it ${DOCKER_CONFIG_MOUNT_ARGS} -v "et_discord_bot_data:/var/et_discord_bot_data/" ${IMAGE_NAME}
