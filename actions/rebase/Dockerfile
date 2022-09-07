ARG VERSION=latest
FROM alpine:${VERSION}

LABEL version="1.0.0"
LABEL repository="http://github.com/z-shell/.github"
LABEL homepage="http://github.com/z-shell/.github"
LABEL maintainer="Z-Shell"
LABEL "com.github.actions.name"="Rebase"
LABEL "com.github.actions.description"="Rebases pull request on '/rebase'"
LABEL "com.github.actions.icon"="git-commit"
LABEL "com.github.actions.color"="green"

# trunk-ignore(hadolint/DL3018)
RUN apk --no-cache add jq bash curl git git-lfs

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
