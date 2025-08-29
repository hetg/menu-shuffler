#!/bin/sh

ollama serve

ollama pull hetg/llama3-nutrition

exec ollama serve