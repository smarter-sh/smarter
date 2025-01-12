import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'


// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const commonConfig = {
    plugins: [react()],
    build: {
      sourcemap: true,
    },
  };

  if (mode === 'dev') {
    return {
      ...commonConfig,
      base: '/',
      server: {
        port: 3000,
        open: true,
      },
    };
  } else {
    return {
      ...commonConfig,
      base: '/static/',
    };
  }
})
