/**
 * TigerHill Debug Interceptor
 * 用于诊断 gemini-cli 使用的网络 API
 */

const fs = require('fs');
const path = require('path');
const Module = require('module');

console.log('[TigerHill Debug] Starting diagnostics...');

// 1. Hook globalThis.fetch
const originalFetch = globalThis.fetch;
let fetchCallCount = 0;

globalThis.fetch = async function(...args) {
    fetchCallCount++;
    console.log(`[TigerHill Debug] globalThis.fetch called! (count: ${fetchCallCount})`);
    console.log(`[TigerHill Debug] Arguments:`, JSON.stringify(args[0], null, 2).substring(0, 200));
    return originalFetch.apply(this, args);
};

// 2. Hook https.request
try {
    const https = require('https');
    const originalHttpsRequest = https.request;
    let httpsCallCount = 0;

    https.request = function(...args) {
        httpsCallCount++;
        console.log(`[TigerHill Debug] https.request called! (count: ${httpsCallCount})`);
        console.log(`[TigerHill Debug] Options:`, JSON.stringify(args[0], null, 2).substring(0, 200));
        return originalHttpsRequest.apply(this, args);
    };
} catch (e) {
    console.log('[TigerHill Debug] Could not hook https:', e.message);
}

// 3. Hook http.request
try {
    const http = require('http');
    const originalHttpRequest = http.request;
    let httpCallCount = 0;

    http.request = function(...args) {
        httpCallCount++;
        console.log(`[TigerHill Debug] http.request called! (count: ${httpCallCount})`);
        console.log(`[TigerHill Debug] Options:`, JSON.stringify(args[0], null, 2).substring(0, 200));
        return originalHttpRequest.apply(this, args);
    };
} catch (e) {
    console.log('[TigerHill Debug] Could not hook http:', e.message);
}

// 4. Hook Module._load to see what gets loaded
const originalLoad = Module._load;
const loadedModules = new Set();

Module._load = function(request, parent, isMain) {
    if (request.includes('google') || request.includes('genai') || request.includes('auth')) {
        if (!loadedModules.has(request)) {
            console.log(`[TigerHill Debug] Loading module: ${request}`);
            loadedModules.add(request);
        }
    }
    return originalLoad.apply(this, arguments);
};

// 5. 监听进程退出
process.on('exit', () => {
    console.log('\n[TigerHill Debug] Process exiting...');
    console.log(`[TigerHill Debug] globalThis.fetch calls: ${fetchCallCount}`);
    console.log(`[TigerHill Debug] Loaded Google modules:`, Array.from(loadedModules));
});

console.log('[TigerHill Debug] All hooks installed.');
console.log('[TigerHill Debug] Monitoring:');
console.log('[TigerHill Debug]   - globalThis.fetch');
console.log('[TigerHill Debug]   - https.request');
console.log('[TigerHill Debug]   - http.request');
console.log('[TigerHill Debug]   - Module._load');
