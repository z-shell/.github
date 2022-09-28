ARG VERSION=edge
FROM alpine:${VERSION}

LABEL repository="http://github.com/z-shell/.github"
LABEL homepage="http://github.com/z-shell/.github"
LABEL maintainer="<Z-Shell Community>"
LABEL email="<team@zshell.dev>"
LABEL "com.github.actions.name"="GitHub Action - rclone"
LABEL "com.github.actions.description"="Pass commands for rclone to sync files and directories from different cloud storage providers"
LABEL "com.github.actions.icon"="arrow-up"
LABEL "com.github.actions.color"="green"

# trunk-ignore(hadolint/DL3018)
RUN apk --no-cache add coreutils \
bash ca-certificates fuse openssh-client rclone \
&& rclone selfupdate -q

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
