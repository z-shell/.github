FROM python:3.15-rc-alpine3.21

RUN pip install \
  --root-user-action=ignore \
  --no-cache-dir pygithub==1.57

COPY verify_pr_lables.py /verify_pr_lables.py

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/verify_pr_lables.py"]
