FROM alpine:3.17

RUN apk --no-cache add \
  git=~2 \
  openssh-client-default=~9

COPY *.sh /

ENTRYPOINT ["/entrypoint.sh"]
