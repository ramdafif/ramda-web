import {readdirSync,readFileSync} from 'node:fs';
import {join} from 'node:path';
import assert from 'node:assert/strict';
const source=JSON.parse(readFileSync(new URL('../backend/seed/content.json',import.meta.url)));
const phrases=[];
function collect(value){
 if(Array.isArray(value))value.forEach(collect);
 else if(value && typeof value==='object'){
  if(typeof value.id==='string' && value.id.length>35)phrases.push(value.id);
  Object.values(value).forEach(collect);
 }
}
source.forEach(row=>collect(row.data));
function walk(directory){for(const entry of readdirSync(directory,{withFileTypes:true})){
 const path=join(directory,entry.name);
 if(entry.isDirectory()){if(entry.name!=='i18n')walk(path);continue;}
 const text=readFileSync(path,'utf8');
 for(const phrase of phrases)assert(!text.includes(phrase),`CMS marketing copy leaked into ${path}: ${phrase}`);
}}
walk(new URL('../frontend/src',import.meta.url).pathname);
console.log('CMS marketing copy boundary verified.');
