import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
 testDir:'../tests', testMatch:'*.spec.ts', fullyParallel:false, workers:1, timeout:30000,
 use:{baseURL:'http://127.0.0.1:4321',trace:'retain-on-failure'},
 reporter:[['list'],['html',{open:'never'}]],
 projects:[{name:'desktop',use:{...devices['Desktop Chrome']}},{name:'mobile',use:{...devices['Pixel 7']}}],
 webServer:{command:'node ../deploy/test-server.mjs',url:'http://127.0.0.1:4321',reuseExistingServer:false,timeout:60000},
});
