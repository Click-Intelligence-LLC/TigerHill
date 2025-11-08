const path = require('path');
const fs = require('fs');
const Module = require('module');

const observerModulePath = path.resolve(__dirname, 'node_observer.js');
const { wrapGenerativeModel } = require(observerModulePath);

const originalLoad = Module._load;

Module._load = function(request, parent, isMain) {
  const exports = originalLoad.apply(this, arguments);

  if (request === '@google/generative-ai') {
    console.log('[TigerHill Observer] Instrumenting @google/generative-ai');

    const { GoogleGenerativeAI } = exports;

  if (exports.GenerativeModel) {
    console.log('[TigerHill Observer] Wrapping GenerativeModel export');
    exports.GenerativeModel = wrapGenerativeModel(exports.GenerativeModel, {
      autoExport: true,
      exportPath: process.env.TIGERHILL_CAPTURE_PATH || path.resolve(process.cwd(), 'prompt_captures')
    });
  }

    exports.GoogleGenerativeAI = new Proxy(GoogleGenerativeAI, {
      construct(target, args) {
        const instance = new target(...args);
        const originalGetModel = instance.getGenerativeModel.bind(instance);

        instance.getGenerativeModel = function(...modelArgs) {
          const model = originalGetModel(...modelArgs);

          const exportDir = process.env.TIGERHILL_CAPTURE_PATH || path.resolve(process.cwd(), 'prompt_captures');
          fs.mkdirSync(exportDir, { recursive: true });

          console.log('[TigerHill Observer] getGenerativeModel called');
          const WrappedModel = wrapGenerativeModel(model.constructor, {
            autoExport: true,
            exportPath: exportDir
          });

          return new WrappedModel(model.model);
        };

        return instance;
      }
    });
  }

  return exports;
};

console.log('[TigerHill Observer] Gemini CLI shim active.');
