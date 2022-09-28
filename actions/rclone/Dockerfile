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

# trunk-ignore(hadolint/DL3018)
RUN apk --no-cache add bash ca-certificates fuse openssh-client rclone && rclone selfupdate
#&& wget -qO- https://rclone.org/install.sh | bash

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
