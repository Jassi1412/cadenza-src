# Servizio singolo: UN monitor RML, UNA specifica.
# Un processo SWI-Prolog regge una sola specifica; Render espone una porta per servizio.
# USO
#   docker build -f RML_DOCS/RML_TESTS/monitor/Dockerfile -t cadenza-monitor .
#   docker run -e METRIC=pitch-range -e PORT=8080 -p 8080:8080 cadenza-monitor
#   POST / con evento JSON -> {"error":false}/{"error":true}; GET / non usare.
# Errori passati: base swipl/swipl:stable inesistente; http_monitor.pl richiede path assoluto;
# http_server/2 ritorna e fa halt: usare -g 'sleep(...)' per tenere vivo il processo.
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends swi-prolog-nox \
 && rm -rf /var/lib/apt/lists/*

COPY RML_DOCS/RML_TESTS/monitor/ /opt/rml/
COPY RML_DOCS/RML_TESTS/metrics/*.pl /opt/specs/

ENV METRIC=pitch-range
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "exec swipl -O -g 'sleep(31536000.0)' -p monitor=/opt/rml /opt/rml/http_monitor.pl -- /opt/specs/${METRIC}.pl ${PORT}"]