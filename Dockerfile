# RCARS — RHDP Content Advisory & Recommendation System
# Multi-stage build using RHEL UBI 9

FROM registry.access.redhat.com/ubi9/python-311:latest AS builder

USER 0
WORKDIR /opt/app-root/src

COPY pyproject.toml README.md ./
COPY src/ src/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[web,analysis]"

FROM registry.access.redhat.com/ubi9/python-311:latest AS runtime

USER 0

# Install git for shallow Showroom clones
RUN dnf install -y --nodocs git-core && \
    dnf clean all

USER 1001
WORKDIR /opt/app-root/src

COPY --from=builder /opt/app-root/lib /opt/app-root/lib
COPY --from=builder /opt/app-root/bin /opt/app-root/bin
COPY src/ src/
COPY prompts/ prompts/

ENV PATH="/opt/app-root/bin:$PATH"

EXPOSE 8080

CMD ["uvicorn", "rcars.web.app:app", "--host", "0.0.0.0", "--port", "8080"]
