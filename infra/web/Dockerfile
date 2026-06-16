FROM node:20-alpine

RUN corepack enable && corepack prepare pnpm@9.6.0 --activate

WORKDIR /app

# Copy workspace manifests for dep install layer
COPY package.json pnpm-workspace.yaml tsconfig.base.json ./
COPY packages/types/ ./packages/types/

# Copy web app manifests + config (everything except src — src is bind-mounted)
COPY apps/web/package.json apps/web/tsconfig.json ./apps/web/
COPY apps/web/vite.config.ts apps/web/tailwind.config.ts apps/web/postcss.config.cjs ./apps/web/
COPY apps/web/index.html ./apps/web/
COPY apps/web/src/ ./apps/web/src/

# Install all workspace deps — node_modules stay in image layer
RUN pnpm install

WORKDIR /app/apps/web

EXPOSE 5173

# src/ and index.html are bind-mounted for hot reload; node_modules from image
CMD ["node_modules/.bin/vite", "--host", "0.0.0.0", "--port", "5173"]
