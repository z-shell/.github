# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e

FROM --platform=linux/amd64 golang:1.26.5-trixie@sha256:117e07f49461abb984fc8aef661432461ff43d06faa22c3b73af6a49ce325cb9 AS go-build

ENV GOTOOLCHAIN=local \
    GOFLAGS=-mod=readonly
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . ./
RUN mkdir -p /out \
    && go test ./... -count=1 \
    && go vet ./... \
    && CGO_ENABLED=0 go build -buildvcs=false -trimpath -o /out/readme-terminal-demo ./cmd/readme-terminal-demo

FROM --platform=linux/amd64 debian:trixie-slim@sha256:020c0d20b9880058cbe785a9db107156c3c75c2ac944a6aa7ab59f2add76a7bd AS runtime-base

COPY dependencies.env /tmp/dependencies.env
RUN set -eu; \
    . /tmp/dependencies.env; \
    rm -f /etc/apt/sources.list.d/debian.sources; \
    printf '%s\n' \
      "deb [check-valid-until=no] ${DEBIAN_SNAPSHOT_BOOTSTRAP_URL} trixie main" \
      "deb [check-valid-until=no] ${DEBIAN_SECURITY_SNAPSHOT_BOOTSTRAP_URL} trixie-security main" \
      > /etc/apt/sources.list; \
    apt-get -o Acquire::Check-Valid-Until=false update; \
    apt-get install -y --no-install-recommends \
      "ca-certificates=${DEBIAN_CA_CERTIFICATES_VERSION}"; \
    rm -rf /var/lib/apt/lists/*; \
    printf '%s\n' \
      "deb [check-valid-until=no] ${DEBIAN_SNAPSHOT_URL} trixie main" \
      "deb [check-valid-until=no] ${DEBIAN_SECURITY_SNAPSHOT_URL} trixie-security main" \
      > /etc/apt/sources.list; \
    apt-get -o Acquire::Check-Valid-Until=false update; \
    apt-get install -y --no-install-recommends \
      "ca-certificates=${DEBIAN_CA_CERTIFICATES_VERSION}" \
      "chromium=${DEBIAN_CHROMIUM_VERSION}" \
      "curl=${DEBIAN_CURL_VERSION}" \
      "ffmpeg=${DEBIAN_FFMPEG_VERSION}" \
      "fontconfig=${DEBIAN_FONTCONFIG_VERSION}" \
      "fonts-jetbrains-mono=${DEBIAN_FONTS_JETBRAINS_MONO_VERSION}" \
      "fonts-noto-color-emoji=${DEBIAN_FONTS_NOTO_COLOR_EMOJI_VERSION}" \
      "git=${DEBIAN_GIT_VERSION}" \
      "tini=${DEBIAN_TINI_VERSION}" \
      "xz-utils=${DEBIAN_XZ_UTILS_VERSION}" \
      "zsh=${DEBIAN_ZSH_VERSION}"; \
    test "$(dpkg-query -W -f='${Version}' chromium)" = "${DEBIAN_CHROMIUM_VERSION}"; \
    test "$(dpkg-query -S /usr/bin/chromium)" = 'chromium: /usr/bin/chromium'; \
    test "$(stat -c '%u:%a:%F' /usr/bin/chromium)" = '0:755:regular file'; \
    printf '%s  %s\n' "${CHROMIUM_LAUNCHER_SHA256}" /usr/bin/chromium | sha256sum -c -; \
    if dpkg-query -W -f='${db:Status-Abbrev}' chromium-sandbox 2>/dev/null | grep -q '^ii '; then \
      echo 'chromium-sandbox must not be installed' >&2; \
      exit 1; \
    fi; \
    if find /usr -xdev -type f \( -name chrome-sandbox -o -name chromium-sandbox \) -perm /4000 -print -quit | grep -q .; then \
      echo 'setuid browser helper must not exist' >&2; \
      exit 1; \
    fi; \
    rm -rf /var/lib/apt/lists/* /tmp/dependencies.env

FROM runtime-base AS release-assets

COPY dependencies.env /tmp/dependencies.env
COPY scripts/verify-release-assets.sh scripts/verify-release-assets_test.sh /verify/
COPY scripts/verify-gh-assets.sh scripts/verify-gh-assets_test.sh scripts/bootstrap-gh.sh scripts/bootstrap-gh_test.sh /verify/
RUN set -eu; \
    . /tmp/dependencies.env; \
    mkdir -p /assets /out /extract/vhs /extract/eza; \
    curl --fail --location --silent --show-error --output /assets/cosign-linux-amd64 "${COSIGN_LINUX_AMD64_URL}"; \
    curl --fail --location --silent --show-error --output /assets/cosign-linux-amd64.sigstore.json "${COSIGN_BUNDLE_URL}"; \
    curl --fail --location --silent --show-error --output /assets/checksums.txt "${VHS_CHECKSUMS_URL}"; \
    curl --fail --location --silent --show-error --output /assets/checksums.txt.sigstore.json "${VHS_CHECKSUMS_BUNDLE_URL}"; \
    curl --fail --location --silent --show-error --output /assets/vhs_0.11.0_Linux_x86_64.tar.gz "${VHS_LINUX_X86_64_URL}"; \
    /verify/verify-release-assets_test.sh /assets; \
    curl --fail --location --silent --show-error --output /assets/gh_2.96.0_linux_amd64.tar.gz "${GH_CLI_LINUX_AMD64_URL}"; \
    curl --fail --location --silent --show-error --output /assets/gh_2.96.0_checksums.txt "${GH_CLI_CHECKSUMS_URL}"; \
    /verify/verify-gh-assets_test.sh /assets; \
    /verify/bootstrap-gh_test.sh /assets; \
    curl --fail --location --silent --show-error --output /assets/ttyd.x86_64 "${TTYD_X86_64_URL}"; \
    printf '%s  %s\n' "${TTYD_X86_64_SHA256}" /assets/ttyd.x86_64 | sha256sum -c -; \
    curl --fail --location --silent --show-error --output /assets/eza_x86_64-unknown-linux-gnu.tar.gz "${EZA_X86_64_GNU_URL}"; \
    printf '%s  %s\n' "${EZA_X86_64_GNU_SHA256}" /assets/eza_x86_64-unknown-linux-gnu.tar.gz | sha256sum -c -; \
    tar -xzf /assets/vhs_0.11.0_Linux_x86_64.tar.gz -C /extract/vhs; \
    tar -xzf /assets/eza_x86_64-unknown-linux-gnu.tar.gz -C /extract/eza; \
    cp /extract/vhs/vhs_0.11.0_Linux_x86_64/vhs /out/vhs; \
    cp /assets/ttyd.x86_64 /out/ttyd; \
    cp /extract/eza/eza /out/eza; \
    chmod 0755 /out/vhs /out/ttyd /out/eza

FROM runtime-base AS runtime

COPY --from=go-build /out/readme-terminal-demo /usr/local/bin/readme-terminal-demo
COPY --from=release-assets /out/vhs /usr/local/bin/vhs
COPY --from=release-assets /out/ttyd /usr/local/bin/ttyd
COPY --from=release-assets /out/eza /usr/local/bin/eza
COPY testdata/smoke/readme.tape /usr/local/share/readme-terminal-demo/smoke.tape
RUN mkdir -p /landlock-denied \
    && printf 'Landlock must deny this readable file.\n' > /landlock-denied/readable \
    && chmod 0777 /landlock-denied \
    && chmod 0444 /landlock-denied/readable \
    && chmod 0444 /usr/local/share/readme-terminal-demo/smoke.tape \
    && chmod 0755 /usr/local/bin/readme-terminal-demo /usr/local/bin/vhs /usr/local/bin/ttyd /usr/local/bin/eza

USER 65532:65532
WORKDIR /work
ENTRYPOINT ["/usr/bin/tini", "--"]

FROM runtime AS test
RUN set -eu; \
    test "$(/usr/local/bin/vhs --version)" = 'vhs version v0.11.0 (c6af91a)'; \
    vhs_status=0; \
    /usr/local/bin/vhs --definitely-invalid >/tmp/vhs-invalid.out 2>&1 || vhs_status=$?; \
    test "$vhs_status" -eq 1; \
    rm -f /tmp/vhs-invalid.out; \
    printf '%s\n' 'PASS TestPinnedVHSExitStatusContract'
