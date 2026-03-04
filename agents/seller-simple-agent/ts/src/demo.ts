/**
 * LangGraph ReAct agent demo with Nevermined x402 payment-protected tools.
 *
 * Uses createReactAgent() with requiresPayment() on each tool. Shows three
 * credit patterns: static number, arrow function, and named function.
 *
 * Usage:
 *   npm run demo
 */

import { config } from 'dotenv'
config({ path: '../.env' })

import { tool } from '@langchain/core/tools'
import { ChatOpenAI } from '@langchain/openai'
import { createReactAgent } from '@langchain/langgraph/prebuilt'
import { z } from 'zod'

import { Payments } from '@nevermined-io/payments'
import { requiresPayment } from '@nevermined-io/payments/langchain'

// --- Configuration ---
const NVM_API_KEY = process.env.NVM_API_KEY!
const NVM_SUBSCRIBER_API_KEY = process.env.NVM_SUBSCRIBER_API_KEY!
const NVM_PLAN_ID = process.env.NVM_PLAN_ID!
const NVM_AGENT_ID = process.env.NVM_AGENT_ID || ''
const NVM_ENVIRONMENT = process.env.NVM_ENVIRONMENT || 'sandbox'

if (!NVM_API_KEY || !NVM_PLAN_ID) {
  console.error('NVM_API_KEY and NVM_PLAN_ID are required. Set them in ../.env')
  process.exit(1)
}

if (!NVM_SUBSCRIBER_API_KEY) {
  console.error('NVM_SUBSCRIBER_API_KEY is required for demo mode. Set it in ../.env')
  process.exit(1)
}

if (!process.env.OPENAI_API_KEY) {
  console.error('OPENAI_API_KEY is required. Set it in ../.env')
  process.exit(1)
}

// --- Builder payments instance (server side) ---
const payments = Payments.getInstance({
  nvmApiKey: NVM_API_KEY,
  environment: NVM_ENVIRONMENT as any,
})

// --- Pattern 1: Static credits (number literal) ---
const searchData = tool(
  requiresPayment(
    (args: { query: string }) => {
      return (
        `Search results for '${args.query}':\n` +
        `1. AI adoption in enterprise grew 35% in 2025\n` +
        `2. LLM-powered agents are the fastest-growing segment\n` +
        `3. Payment protocols for AI agents emerging as key infrastructure`
      )
    },
    { payments, planId: NVM_PLAN_ID, agentId: NVM_AGENT_ID, credits: 1 },
  ),
  {
    name: 'search_data',
    description: 'Search for data on a given topic. Costs 1 credit.',
    schema: z.object({ query: z.string() }),
  },
)

// --- Pattern 2: Dynamic credits (arrow function based on result size) ---
const summarizeData = tool(
  requiresPayment(
    (args: { text: string }) => {
      return (
        `Summary of provided text:\n` +
        `- AI agent adoption is accelerating rapidly\n` +
        `- Enterprise use cases are driving growth\n` +
        `- Payment infrastructure is a critical enabler`
      )
    },
    {
      payments,
      planId: NVM_PLAN_ID,
      agentId: NVM_AGENT_ID,
      credits: (ctx) => Math.max(2, Math.min(Math.floor(String(ctx.result).length / 100), 10)),
    },
  ),
  {
    name: 'summarize_data',
    description: 'Summarize text into bullet points. Dynamic cost: 2-10 credits.',
    schema: z.object({ text: z.string() }),
  },
)

// --- Pattern 3: Named function for credits ---
function researchCredits(): number {
  return 10
}

const researchTopic = tool(
  requiresPayment(
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
    { payments, planId: NVM_PLAN_ID, agentId: NVM_AGENT_ID, credits: researchCredits },
  ),
  {
    name: 'research_topic',
    description: 'Deep research on a topic. Costs 10 credits.',
    schema: z.object({ topic: z.string() }),
  },
)

async function main() {
  // --- Step 1: Subscriber acquires x402 token ---
  console.log('\n=== Step 1: Acquiring x402 access token ===\n')

  const subscriberPayments = Payments.getInstance({
    nvmApiKey: NVM_SUBSCRIBER_API_KEY,
    environment: NVM_ENVIRONMENT as any,
  })

  const tokenResponse = await subscriberPayments.x402.getX402AccessToken(NVM_PLAN_ID, NVM_AGENT_ID)
  const accessToken = tokenResponse.accessToken
  if (!accessToken) {
    console.error('Failed to get access token. Make sure you have an active subscription.')
    return
  }
  console.log(`Token obtained: ${accessToken.slice(0, 40)}...`)

  // --- Step 2: Create LangGraph ReAct agent ---
  console.log('\n=== Step 2: Create LangGraph ReAct agent ===\n')

  const llm = new ChatOpenAI({ model: 'gpt-4o-mini', temperature: 0 })
  const agent = createReactAgent({
    llm,
    tools: [searchData, summarizeData, researchTopic],
    prompt:
      'You are a data selling agent. Use the available tools to answer questions.\n' +
      'Credit patterns: search=1 (static), summarize=2-10 (dynamic), research=10 (named fn).',
  })

  console.log('Agent created with tools: search_data, summarize_data, research_topic')

  // --- Step 3: Run agent with payment token ---
  console.log('\n=== Step 3: Run agent (autonomous tool selection) ===\n')

  const result = await agent.invoke(
    { messages: [{ role: 'human', content: 'Search for the latest AI trends and summarize what you find.' }] },
    { configurable: { payment_token: accessToken } },
  )

  const messages = result.messages || []
  const finalMessage = messages[messages.length - 1]
  console.log('Agent response:')
  console.log(finalMessage?.content || 'No response generated.')

  console.log('\n=== Done ===')
}

main().catch(console.error)
