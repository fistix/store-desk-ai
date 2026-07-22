import { Html, Head, Main, NextScript } from 'next/document';

export default function Document() {
  return (
    <Html lang="en">
      <Head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Source+Sans+3:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <script src="https://cdn.tailwindcss.com" />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              tailwind.config = {
                theme: {
                  extend: {
                    fontFamily: {
                      display: ['Outfit', 'sans-serif'],
                      sans: ['Source Sans 3', 'sans-serif'],
                    },
                    colors: {
                      ink: {
                        950: '#0b1220',
                        900: '#121a2b',
                        700: '#334155',
                        500: '#64748b',
                        300: '#cbd5e1',
                        100: '#e8eef6',
                        50: '#f4f7fb',
                      },
                      teal: {
                        700: '#0f766e',
                        600: '#0d9488',
                        500: '#14b8a6',
                        100: '#ccfbf1',
                        50: '#f0fdfa',
                      },
                      coral: {
                        600: '#e11d48',
                        500: '#f43f5e',
                        100: '#ffe4e6',
                      },
                    },
                    boxShadow: {
                      panel: '0 1px 0 rgba(15,23,42,0.04), 0 12px 32px -16px rgba(15,23,42,0.28)',
                    },
                  },
                },
              };
            `,
          }}
        />
      </Head>
      <body className="font-sans antialiased">
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
