FROM alpine:3.17

RUN apk add --no-cache git=2.36.3-r0 openssh-client=9.0_p1-r2

COPY *.sh /

ENTRYPOINT ["/entrypoint.sh"]
