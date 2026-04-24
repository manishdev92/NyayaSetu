# NS-S6-01 — Next.js (build + `next start`; no standalone output required)
FROM --platform=linux/amd64 node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
# Public browser URL of this Next app (use CloudFront URL, not App Runner) so metadata and Clerk match the address bar
ARG NEXT_PUBLIC_APP_URL=
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_APP_URL=$NEXT_PUBLIC_APP_URL
RUN npm run build
EXPOSE 3000
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
CMD ["npm", "run", "start"]
