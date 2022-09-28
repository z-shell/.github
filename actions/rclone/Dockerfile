ARG VERSION=latest
FROM alpine:${VERSION}

LABEL version="1.0.0"
LABEL repository="http://github.com/z-shell/.github"
LABEL homepage="http://github.com/z-shell/.github"
LABEL maintainer="Z-Shell"
LABEL "com.github.actions.name"="Rclone"
LABEL "com.github.actions.description"="Run rclone to sync files and directories from different cloud storage providers"
LABEL "com.github.actions.icon"="arrow-up"
LABEL "com.github.actions.color"="green"

# trunk-ignore(hadolint/DL4006)
RUN apk --no-cache \
bash=5.1.16-r2 \
curl=7.83.1-r3 \
unzip=6.0-r9 \
ca-certificates=20220614-r0 \
fuse=2.9.9-r1 \
openssh=9.0_p1-r2 \
&& wget -qO- https://rclone.org/install.sh | bash \
&& apk del bash curl unzip


COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
