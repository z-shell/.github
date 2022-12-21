FROM alpine:3.17

RUN apk add --no-cache git=2.38.2-r0 openssh-client-default=9.1_p1-r1

COPY *.sh /

ENTRYPOINT ["/entrypoint.sh"]
