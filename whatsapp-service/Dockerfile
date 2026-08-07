FROM node:20-slim

WORKDIR /app

# One of Baileys' dependencies (libsignal-node) is pinned to a git+ssh:// URL.
# There are no SSH keys in this build, so rewrite GitHub SSH URLs to HTTPS -
# the repo is public, no auth needed once npm goes through git that way.
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && git config --global url."https://github.com/".insteadOf "ssh://git@github.com/" \
    && git config --global url."https://github.com/".insteadOf "git@github.com:"

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY src ./src

RUN mkdir -p /app/sessions

EXPOSE 4000

CMD ["node", "src/index.js"]
