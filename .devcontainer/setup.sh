#!/bin/bash

# Upgrade pip und installiere Home Assistant Core + nötige Tools
pip install --upgrade pip
pip install homeassistant colorlog google-generativeai

# Erstelle das HA Config-Verzeichnis, falls es nicht existiert
mkdir -p config

# Erstelle einen Symlink, damit Home Assistant deine Custom Component findet
ln -sfn ${PWD}/custom_components ${PWD}/config/custom_components

# Erstelle eine minimale configuration.yaml für den Start
if [ ! -f config/configuration.yaml ]; then
    echo "default_config:" > config/configuration.yaml
    echo "logger:" >> config/configuration.yaml
    echo "  default: info" >> config/configuration.yaml
    echo "  logs:" >> config/configuration.yaml
    echo "    custom_components.mass_ai_dj: debug" >> config/configuration.yaml
fi