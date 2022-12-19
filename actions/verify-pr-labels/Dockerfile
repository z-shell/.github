FROM python:3.11.1-alpine3.17

RUN pip install --no-cache-dir pygithub==1.57

COPY verify_pr_lables.py /verify_pr_lables.py

ENV ENV PIP_ROOT_USER_ACTION=ignore
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/verify_pr_lables.py"]
