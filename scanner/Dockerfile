# Read-only status site for stockbreak.up.railway.app: build status and the committed
# reports rendered to static HTML at build time. Railway builds this from the repo
# root (see /railway.json), so paths below are relative to the repo root.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY scanner/requirements-site.txt ./
RUN pip install -r requirements-site.txt

COPY scanner/nsescan ./nsescan
COPY scanner/reports ./reports
COPY scanner/README.md ./README.md

# Railway passes the deployed commit as a build variable; it is shown in the footer.
ARG RAILWAY_GIT_COMMIT_SHA=unknown
RUN SITE_GIT_SHA="$RAILWAY_GIT_COMMIT_SHA" python -m nsescan site

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8080
CMD ["python", "-m", "nsescan", "serve"]
