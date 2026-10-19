# Use a specific version tag for the base image
FROM alpine:3.24@sha256:294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6

# Combine RUN commands into a single line to reduce the number of layers
RUN apk --update --no-cache add \
    fuse \
    bash \
    rclone \
    coreutils \
    ca-certificates \
    openssh-client-default

# Set the working directory
WORKDIR /app

# Copy entrypoint script and set ownership
COPY --chown=root:root entrypoint.sh /entrypoint.sh

# Add a HEALTHCHECK to monitor the container's health
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD pgrep rclone || exit 1

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]