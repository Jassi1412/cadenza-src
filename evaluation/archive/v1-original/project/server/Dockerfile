# Servizio unico Cadenza: Python + SWI-Prolog nella stessa immagine.
# Verdetto a fine esecuzione: join.py poi swipl in batch, sette exit code.
# USO LOCALE
#   docker build -f server/Dockerfile -t cadenza-service .
#   docker run -e PORT=8080 -p 8080:8080 cadenza-service
#   curl -X POST localhost:8080/ -H 'Content-Type: application/json' -d @req.json

# Stage 1: i .rml diventano Prolog (unica fonte).
# Compiler vendorizzato in vendor/rml-compiler/: evita Gradle e ~300 MB di deps.
# Java serve solo qui.
FROM eclipse-temurin:21-jdk AS specs

COPY vendor/rml-compiler/ /opt/rmlc/
COPY rml/metrics/ /src/

RUN set -e; \
    mkdir -p /specs; \
    # Git non conserva il bit +x su clone Windows: chmod qui.
    chmod +x /opt/rmlc/bin/rml-compiler; \
    for f in /src/*.rml; do \
        /opt/rmlc/bin/rml-compiler --input "$f" --output "/specs/$(basename "$f" .rml).pl"; \
    done; \
    n=$(ls -1 /specs/*.pl | wc -l); \
    echo "specifiche compilate: $n"; \
    test "$n" -eq 7 || { echo "ATTESE 7, TROVATE $n"; exit 1; }

# Stage 2: runtime.
# Immagine Python minimale, dipendenze esplicite in requirements.txt.
FROM python:3.12-slim

# swi-prolog-nox: SWI-Prolog senza GUI. `swipl/swipl:stable` non esiste su Docker Hub.
RUN apt-get update && apt-get install -y --no-install-recommends swi-prolog-nox \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

# Prima le dipendenze: layer riutilizzabile.
COPY server/requirements.txt /opt/requirements.txt
RUN pip install --no-cache-dir -r /opt/requirements.txt

COPY rml/monitor/ /opt/rml/
COPY --from=specs /specs/             /opt/specs/
COPY server/alignment/join.py   /opt/join.py
COPY server/alignment/server.py /opt/server.py
COPY server/batch.pl     /opt/batch.pl

# Una specifica mancante/vuota deve far fallire la build.
RUN test "$(ls -1 /opt/specs/*.pl | wc -l)" -eq 7 \
 && ! grep -qs ':- dynamic' /opt/specs/*.pl \
 && for f in /opt/specs/*.pl; do test -s "$f"; done

ENV RML_MONITOR=/opt/rml
ENV RML_SPECS=/opt/specs
ENV PORT=8080

# Thread: OpenBLAS/OpenMP leggono core di build, non del container.
# Su Render free, meno di un core: un thread evita oversubscription.
ENV OMP_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV NUMBA_NUM_THREADS=1

EXPOSE 8080

# Render usa CMD, non ENTRYPOINT.
CMD ["python", "/opt/server.py"]
