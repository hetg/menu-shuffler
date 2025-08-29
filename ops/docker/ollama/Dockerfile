FROM ollama/ollama:latest

VOLUME /root/.ollama

COPY ops/docker/ollama/start-ollama.sh /start-ollama.sh
RUN chmod +x /start-ollama.sh

EXPOSE 11434

ENTRYPOINT ["/start-ollama.sh"]