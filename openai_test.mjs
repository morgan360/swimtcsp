import 'dotenv/config';
import OpenAI from 'openai';

const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  project: process.env.OPENAI_PROJECT,
});

async function go() {
  try {
    const r = await client.responses.create({
      model: 'gpt-4o', // change to gpt-5 if available in your account
      input: 'Write a one-sentence bedtime story about a unicorn.',
    });
    console.log(r.output_text);
  } catch (err) {
    console.error('Request failed:', err?.status || '', err?.message || err);
  }
}

go();

