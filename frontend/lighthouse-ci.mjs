// Direct, current Lighthouse API avoids the old LHCI CLI's vulnerable dependency tree.
import lighthouse from 'lighthouse';
import * as chromeLauncher from 'chrome-launcher';
import {chromium} from 'playwright';
import {spawn} from 'node:child_process';
import {mkdirSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import assert from 'node:assert/strict';
import config from './lighthouse.config.mjs';
const root=resolve(import.meta.dirname,'..');
const server=spawn('node',['deploy/test-server.mjs'],{cwd:root,stdio:'inherit'});
let chrome;
try{
 let healthy=false;
 for(let i=0;i<120;i++){
  try{if((await fetch(config.urls[0])).ok){healthy=true;break;}}catch{/* Startup */}
  await new Promise(resolve=>setTimeout(resolve,250));
 }
 assert(healthy,'Test services did not start');
 chrome=await chromeLauncher.launch({chromePath:process.env.CHROME_PATH || chromium.executablePath(),chromeFlags:['--headless','--no-sandbox','--disable-dev-shm-usage']});
 const output=resolve(root,'lighthouse-report');mkdirSync(output,{recursive:true});
 for(const url of config.urls){
  const reports=[];
  for(let run=0;run<config.runs;run++){
   const result=await lighthouse(url,{port:chrome.port,output:['html','json'],logLevel:'error',onlyCategories:config.categories,formFactor:'mobile',screenEmulation:{mobile:true,width:390,height:844,deviceScaleFactor:1,disabled:false}});
   assert(result,'Lighthouse returned no result');
   const slug=new URL(url).pathname.replaceAll('/','-') || '-';
   writeFileSync(resolve(output,`${slug}-${run+1}.html`),result.report[0]);
   writeFileSync(resolve(output,`${slug}-${run+1}.json`),result.report[1]);
   reports.push(result.lhr);
  }
  const median=values=>values.toSorted((a,b)=>a-b)[Math.floor(values.length/2)];
  for(const category of config.categories){const score=median(reports.map(r=>r.categories[category].score));console.log(url,category,score);assert(score>=config.minimumScore,`${url} ${category} is below ${config.minimumScore}`);}
  const lcp=median(reports.map(r=>r.audits['largest-contentful-paint'].numericValue));
  const cls=median(reports.map(r=>r.audits['cumulative-layout-shift'].numericValue));
  assert(lcp<=config.maximumLcpMs,`${url} LCP ${lcp} exceeds target`);
  assert(cls<=config.maximumCls,`${url} CLS ${cls} exceeds target`);
 }
}finally{chrome?.kill();server.kill('SIGTERM');}
