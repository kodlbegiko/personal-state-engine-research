#!/usr/bin/env node
import fs from 'node:fs';
import readline from 'node:readline';
import { env, pipeline, AutoTokenizer } from '@huggingface/transformers';

const modelId = process.env.PSE_MODEL_ID;
const revision = process.env.PSE_MODEL_REVISION;
const dtype = process.env.PSE_MODEL_DTYPE || 'q4';
const cacheDir = process.env.PSE_HF_CACHE || '.external-data/hf-cache';

if (!modelId || !revision || !/^[0-9a-f]{40}$/.test(revision)) {
  console.error('PSE_MODEL_ID and exact 40-hex PSE_MODEL_REVISION are required');
  process.exit(2);
}

fs.mkdirSync(cacheDir, { recursive: true });
env.cacheDir = cacheDir;
env.allowLocalModels = false;
env.useBrowserCache = false;

function flattenLength(value) {
  if (value == null) return 0;
  if (Array.isArray(value)) {
    if (value.length && Array.isArray(value[0])) return value[0].length;
    return value.length;
  }
  if (value.data && typeof value.data.length === 'number') return value.data.length;
  if (value.input_ids) return flattenLength(value.input_ids);
  return 0;
}

function extractGeneratedText(result) {
  const row = Array.isArray(result) ? result[0] : result;
  const generated = row?.generated_text;
  if (typeof generated === 'string') return generated;
  if (Array.isArray(generated)) {
    const last = generated.at(-1);
    if (last && typeof last.content === 'string') return last.content;
  }
  throw new Error('model output has no generated text');
}

const tokenizer = await AutoTokenizer.from_pretrained(modelId, { revision });
const generator = await pipeline('text-generation', modelId, {
  revision,
  dtype,
  device: 'cpu',
});

process.stdout.write(JSON.stringify({
  status: 'ready',
  model_id: modelId,
  model_revision: revision,
  dtype,
  cache_directory: cacheDir,
  runtime: '@huggingface/transformers',
}) + '\n');

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of rl) {
  if (!line.trim()) continue;
  let request;
  try {
    request = JSON.parse(line);
    const messages = [
      { role: 'system', content: request.system_prompt || '' },
      ...(request.messages || []),
    ];
    const tokenized = tokenizer.apply_chat_template(messages, {
      add_generation_prompt: true,
      tokenize: true,
      return_dict: false,
    });
    const inputTokens = flattenLength(tokenized);
    const userText = (request.messages || []).map((message) => message.content || '').join('\n');
    const historyText = userText.includes('Question date:') ? userText.split('Question date:')[0] : '';
    const retrievalTokens = historyText ? flattenLength(tokenizer.encode(historyText, { add_special_tokens: false })) : 0;
    const started = performance.now();
    const result = await generator(messages, {
      max_new_tokens: request.manifest?.token_budget ?? 64,
      do_sample: false,
      return_full_text: false,
    });
    const latencyMs = performance.now() - started;
    const text = extractGeneratedText(result).trim();
    const outputTokens = flattenLength(tokenizer.encode(text, { add_special_tokens: false }));
    process.stdout.write(JSON.stringify({
      request_id: request.request_id,
      text,
      usage: {
        input_tokens: inputTokens,
        output_tokens: outputTokens,
        retrieval_tokens: retrievalTokens,
      },
      latency_ms: latencyMs,
      raw_generation: result,
      model_id: modelId,
      model_revision: revision,
      dtype,
    }) + '\n');
  } catch (error) {
    process.stdout.write(JSON.stringify({
      request_id: request?.request_id ?? 'unparsed-request',
      error: error instanceof Error ? error.message : String(error),
    }) + '\n');
  }
}
