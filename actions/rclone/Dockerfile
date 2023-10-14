FROM alpine:3

RUN apk --no-cache add \
  fuse \
  bash \
  rclone \
  coreutils \
  ca-certificates \
  openssh-client-default

WORKDIR /app
COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
