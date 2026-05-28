FROM node:22-slim AS build

WORKDIR /repo

RUN corepack enable && corepack prepare pnpm@8.15.4 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/admin-web/package.json apps/admin-web/pnpm-lock.yaml ./apps/admin-web/
RUN pnpm install --frozen-lockfile

COPY apps/admin-web ./apps/admin-web
RUN pnpm --filter @capital-index/admin-web build

FROM node:22-slim AS runner

WORKDIR /repo/apps/admin-web

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=8080

COPY --from=build /repo /repo

EXPOSE 8080

CMD ["node", "node_modules/next/dist/bin/next", "start", "-p", "8080"]
