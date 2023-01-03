FROM alpine:3.17

RUN apk --no-cache add \
  fuse=~2.9 \
  bash=~5.2 \
  rclone=~1.60 \
  coreutils=~9.1 \
  ca-certificates=~20220614 \
  openssh-client-default=~9.1

COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
