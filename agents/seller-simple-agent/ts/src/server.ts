/**
 * Express server for the seller agent with x402 payment protection.
 *
 * Payment verification and settlement are handled by paymentMiddleware at the
 * HTTP layer — route handlers just run the LangGraph agent.
 *
 * Endpoints:
 *   POST /data    - Query the agent (requires x402 token)
 *   GET  /pricing - Show pricing tiers
 *   GET  /health  - Health check
 *
 * Usage:
 *   npm run server
 */

import { config } from 'dotenv'
config({ path: '../.env' })

import express from 'express'
import { tool } from '@langchain/core/tools'
import { ChatOpenAI } from '@langchain/openai'
import { createReactAgent } from '@langchain/langgraph/prebuilt'
import { z } from 'zod'

import { Payments } from '@nevermined-io/payments'
import { paymentMiddleware } from '@nevermined-io/payments/express'

// --- Configuration ---
const NVM_API_KEY = process.env.NVM_API_KEY || ''
const NVM_PLAN_ID = process.env.NVM_PLAN_ID || ''
const NVM_AGENT_ID = process.env.NVM_AGENT_ID || ''
const NVM_ENVIRONMENT = process.env.NVM_ENVIRONMENT || 'sandbox'
const PORT = parseInt(process.env.PORT || '3000', 10)

if (!NVM_API_KEY || !NVM_PLAN_ID) {
  console.error('NVM_API_KEY and NVM_PLAN_ID are required. Set them in ../.env')
  process.exit(1)
}

if (!process.env.OPENAI_API_KEY) {
  console.error('OPENAI_API_KEY is required. Set it in ../.env')
  process.exit(1)
}

// --- Payments instance ---
const payments = Payments.getInstance({
  nvmApiKey: NVM_API_KEY,
  environment: NVM_ENVIRONMENT as any,
})

// --- Pricing tiers ---
const PRICING = {
  tiers: [
    { tool: 'search_data', credits: 1, description: 'Basic web search' },
    { tool: 'summarize_data', credits: 5, description: 'LLM-powered content summarization' },
    { tool: 'research_topic', credits: 10, description: 'Full market research report' },
  ],
  plan_id: NVM_PLAN_ID,
}

// --- Mock tools (no requiresPayment — middleware handles payment at HTTP layer) ---

const searchData = tool(
  (args: { query: string }) => {
    return (
      `Search results for '${args.query}':\n` +
      `1. AI adoption in enterprise grew 35% in 2025\n` +
      `2. LLM-powered agents are the fastest-growing segment\n` +
      `3. Payment protocols for AI agents emerging as key infrastructure`
    )
  },
  {
    name: 'search_data',
    description: 'Search for data on a given topic. Costs 1 credit.',
    schema: z.object({ query: z.string().describe('The search query') }),
  },
)

const summarizeData = tool(
  (args: { text: string }) => {
    return (
      `Summary of provided text:\n` +
      `- AI agent adoption is accelerating rapidly\n` +
      `- Enterprise use cases are driving growth\n` +
      `- Payment infrastructure is a critical enabler`
    )
  },
  {
    name: 'summarize_data',
    description: 'Summarize text into bullet points. Costs 5 credits.',
    schema: z.object({ text: z.string().describe('The text to summarize') }),
  },
)

const researchTopic = tool(
  (args: { topic: string }) => {
    return (
      `Research report on '${args.topic}':\n\n` +
      `Executive Summary:\n` +
      `The field of ${args.topic} is experiencing rapid transformation. ` +
      `Key drivers include advances in foundation models, ` +
      `the emergence of autonomous agent architectures, ` +
      `and new payment infrastructure enabling agent-to-agent commerce.\n\n` +
      `Key Findings:\n` +
      `1. Market size projected to reach $50B by 2027\n` +
      `2. Enterprise adoption accelerating across all sectors\n` +
      `3. Open-source ecosystem growing 3x year-over-year\n` +
      `4. Regulatory frameworks beginning to take shape`
    )
  },
  {
    name: 'research_topic',
    description: 'Deep research on a topic. Costs 10 credits.',
    schema: z.object({ topic: z.string().describe('The research topic') }),
  },
)

// --- LangGraph ReAct agent ---
const llm = new ChatOpenAI({ model: 'gpt-4o-mini', temperature: 0 })

const graph = createReactAgent({
  llm,
  tools: [searchData, summarizeData, researchTopic],
  prompt:
    'You are a data selling agent. You provide data services at three tiers:\n' +
    '1. search_data (1 credit) — basic web search\n' +
    '2. summarize_data (5 credits) — LLM-powered summarization\n' +
    '3. research_topic (10 credits) — full market research report\n' +
    'Choose the appropriate tool based on the query complexity.',
})

async function runAgent(query: string): Promise<string> {
  const result = await graph.invoke({
    messages: [{ role: 'human', content: query }],
  })
  const messages = result.messages || []
  if (messages.length > 0) {
    const final = messages[messages.length - 1]
    return typeof final.content === 'string' ? final.content : JSON.stringify(final.content)
  }
  return 'No response generated.'
}

// --- Express app ---
const app = express()
app.use(express.json())

// Payment middleware — protects POST /data
app.use(
  paymentMiddleware(payments, {
    'POST /data': {
      planId: NVM_PLAN_ID,
      credits: 1,
      ...(NVM_AGENT_ID && { agentId: NVM_AGENT_ID }),
    },
  }),
)

app.post('/data', async (req, res) => {
  try {
    const { query } = req.body
    if (!query) {
      res.status(400).json({ error: 'Missing "query" in request body' })
      return
    }
    const response = await runAgent(query)
    res.json({ response })
  } catch (error) {
    console.error('Error in /data:', error)
    res.status(500).json({ error: 'Internal server error' })
  }
})

app.get('/pricing', (_req, res) => {
  res.json(PRICING)
})

app.get('/health', (_req, res) => {
  res.json({
    status: 'ok',
    agent: 'seller-simple-agent-ts',
    plan_id: NVM_PLAN_ID,
  })
})

app.listen(PORT, () => {
  console.log(`\nSeller Agent (TypeScript/LangGraph) running on http://localhost:${PORT}`)
  console.log(`Plan ID: ${NVM_PLAN_ID}`)
  console.log(`Agent ID: ${NVM_AGENT_ID || '(not set)'}`)
  console.log('\nPayment protection via x402 paymentMiddleware')
  console.log('\nEndpoints:')
  console.log("  POST /data    - Query the agent (requires x402 'payment-signature' header)")
  console.log('  GET  /pricing - View pricing tiers')
  console.log('  GET  /health  - Health check')
})
