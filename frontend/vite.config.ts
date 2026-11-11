import {defineConfig} from 'vitest/config';
export default defineConfig({base:'/data/',server:{host:'127.0.0.1',port:58229,strictPort:true,proxy:{'/api':{target:'http://127.0.0.1:58230',changeOrigin:false},'/healthz':{target:'http://127.0.0.1:58230',changeOrigin:false},'/readyz':{target:'http://127.0.0.1:58230',changeOrigin:false}}},test:{environment:'jsdom',globals:true,restoreMocks:true}});
