This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the marketing home. The signed-in assistant lives at [`/chat`](http://localhost:3000/chat).

### Marketing site (GTM)

- **Routes (English):** `/`, `/features`, `/how-it-works`, `/pricing` (includes **live caps** from `GET /config`), `/faq`, `/about`, `/blog` (stub), `/contact` (optional `NEXT_PUBLIC_CONTACT_EMAIL`).
- **Hindi:** same paths under `/hi/…` (e.g. `/hi/pricing`). Header **हिंदी / EN** toggles locale. Copy lives in `lib/marketingBundles.ts`.
- **S3 / static hosting:** These pages are server-rendered Next.js by default. To mirror them on S3, use `output: 'export'` (if you drop fully dynamic APIs from those routes) or publish a static snapshot; keep `/chat` on a host that can run the Next.js app and call your API. A common pattern is CloudFront with two origins: static bucket for marketing paths and the App Runner / Vercel URL for `/chat` and API proxies.

Edit copy in `lib/marketingBundles.ts` (or add MDX under `app/blog` later).

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
