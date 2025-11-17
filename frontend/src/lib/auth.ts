import { NextAuthOptions } from 'next-auth'
import GoogleProvider from 'next-auth/providers/google'

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: 'openid email profile https://www.googleapis.com/auth/classroom.courses.readonly https://www.googleapis.com/auth/classroom.coursework.students.readonly https://www.googleapis.com/auth/classroom.student-submissions.students.readonly',
        },
      },
      httpOptions: {
        timeout: 10000, // 10 seconds instead of 3.5
      },
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      // Persist the OAuth access_token to the token right after signin
      if (account) {
        token.accessToken = account.access_token
        token.refreshToken = account.refresh_token
        token.expiresAt = account.expires_at
        
        // Send Google tokens to backend
        try {
          console.log('Syncing tokens with backend...');
          const response = await fetch(`${process.env.BACKEND_API_URL || 'http://localhost:8000'}/api/v1/auth/google/token`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              token: account.id_token,
              access_token: account.access_token,
              refresh_token: account.refresh_token,
              expires_in: account.expires_at ? (account.expires_at - Math.floor(Date.now() / 1000)) : 3600,
            }),
          });
          
          if (response.ok) {
            const data = await response.json();
            console.log('Backend token received:', data.access_token ? 'Yes' : 'No');
            token.backendToken = data.access_token;
          } else {
            const errorText = await response.text();
            console.error('Backend auth failed:', response.status, errorText);
          }
        } catch (error) {
          console.error('Failed to sync with backend:', error);
        }
      }
      return token
    },
    async session({ session, token }) {
      // Send properties to the client
      session.accessToken = token.accessToken as string
      session.backendToken = token.backendToken as string
      return session
    },
  },
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error',
  },
  session: {
    strategy: 'jwt',
  },
}