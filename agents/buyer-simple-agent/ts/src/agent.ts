/**
 * Interactive CLI buyer agent using LangGraph ReAct agent.
 *
 * Tools are plain (no requiresPayment) — the buyer generates x402 tokens
 * internally and sends them to the seller. The x402 flow happens inside
 * the purchase_data tool.
 *
 * Usage:
 *   npm run agent
 */

import { config } from 'dotenv'
config({ path: '../.env' })

import * as readline from 'readline'
import { tool } from '@langchain/core/tools'
import { ChatOpenAI } from '@langchain/openai'
import { createReactAgent } from '@langchain/langgraph/prebuilt'
import { z } from 'zod'

import { Payments } from '@nevermined-io/payments'

// --- Configuration ---
const NVM_API_KEY = process.env.NVM_API_KEY || ''
const NVM_PLAN_ID = process.env.NVM_PLAN_ID || ''
const NVM_AGENT_ID = process.env.NVM_AGENT_ID || ''
const NVM_ENVIRONMENT = process.env.NVM_ENVIRONMENT || 'sandbox'
const SELLER_URL = process.env.SELLER_URL || 'http://localhost:3000'

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

// --- Buyer tools (plain — no requiresPayment) ---

const discoverPricing = tool(
  async (args: { seller_url?: string }) => {
    const url = args.seller_url || SELLER_URL
    try {
      const resp = await fetch(`${url}/pricing`)
      if (!resp.ok) {
        return `Failed to fetch pricing from ${url}: ${resp.status} ${resp.statusText}`
      }
      const data = await resp.json()
      const tiers = (data as any).tiers || []
      let text = `Pricing tiers from ${url}:\n`
      for (const tier of tiers) {
        text += `  - ${tier.tool}: ${tier.credits} credit(s) — ${tier.description}\n`
      }
      text += `\nPlan ID: ${(data as any).plan_id || 'N/A'}`
      return text
    } catch (err: any) {
      return `Error contacting seller at ${url}: ${err.message}`
    }
  },
  {
    name: 'discover_pricing',
    description: 'Discover a seller\'s available data services and pricing tiers. Call this first.',
    schema: z.object({
      seller_url: z.string().optional().describe('Base URL of the seller (defaults to SELLER_URL)'),
    }),
  },
)

const checkBalance = tool(
  async () => {
    try {
      const balance = await payments.plans.getPlanBalance(NVM_PLAN_ID)
      const { isSubscriber, balance: credits } = balance
      return (
        `Nevermined balance for plan ${NVM_PLAN_ID}:\n` +
        `  Subscribed: ${isSubscriber}\n` +
        `  Credits remaining: ${credits ?? 'N/A'}`
      )
    } catch (err: any) {
      return `Error checking balance: ${err.message}`
    }
  },
  {
    name: 'check_balance',
    description: 'Check your Nevermined credit balance for the configured plan.',
    schema: z.object({}),
  },
)

const purchaseData = tool(
  async (args: { query: string; seller_url?: string }) => {
    const url = args.seller_url || SELLER_URL
    try {
      // Generate x402 access token
      const tokenResult = await payments.x402.getX402AccessToken(
        NVM_PLAN_ID,
        NVM_AGENT_ID || undefined,
      )
      const accessToken = tokenResult.accessToken
      if (!accessToken) {
        return 'Failed to generate x402 access token. Check your subscription.'
      }

      // Send request with payment token
      const resp = await fetch(`${url}/data`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'payment-signature': accessToken,
        },
        body: JSON.stringify({ query: args.query }),
      })

      if (!resp.ok) {
        return `Seller returned ${resp.status}: ${await resp.text()}`
      }

      const data = (await resp.json()) as any
      let text = `Purchase successful!\n\nResponse: ${data.response || JSON.stringify(data)}`

      // Check settlement receipt
      const prResponse = resp.headers.get('payment-response')
      if (prResponse) {
        const settlement = JSON.parse(Buffer.from(prResponse, 'base64').toString('utf-8'))
        text += `\n\nCredits charged: ${settlement.creditsRedeemed ?? 'N/A'}`
        text += `\nRemaining balance: ${settlement.remainingBalance ?? 'N/A'}`
      }

      return text
    } catch (err: any) {
      return `Error purchasing data: ${err.message}`
    }
  },
  {
    name: 'purchase_data',
    description: 'Purchase data from a seller using x402 payment. Generates a token and sends the query.',
    schema: z.object({
      query: z.string().describe('The data query to send to the seller'),
      seller_url: z.string().optional().describe('Base URL of the seller (defaults to SELLER_URL)'),
    }),
  },
)

// --- LangGraph ReAct agent ---
const llm = new ChatOpenAI({ model: 'gpt-4o-mini', temperature: 0 })

const graph = createReactAgent({
  llm,
  tools: [discoverPricing, checkBalance, purchaseData],
  prompt:
    'You are a data buying agent. You help users discover and purchase data from sellers ' +
    'using the x402 HTTP payment protocol.\n\n' +
    'Your workflow:\n' +
    '1. discover_pricing — Call this first to see what the seller offers.\n' +
    '2. check_balance — Check credit balance before purchasing.\n' +
    '3. purchase_data — Buy data by sending an x402-protected HTTP request.\n\n' +
    'Always discover pricing first, then check balance, then confirm cost with the user before purchasing.',
})

// --- Interactive CLI ---
async function main() {
  console.log('='.repeat(60))
  console.log('Data Buying Agent (TypeScript/LangGraph) — Interactive CLI')
  console.log('='.repeat(60))
  console.log(`Plan ID: ${NVM_PLAN_ID}`)
  console.log(`Seller:  ${SELLER_URL}`)
  console.log('\nType your queries (or "quit" to exit):')
  console.log('Examples:')
  console.log('  "What data services are available?"')
  console.log('  "How many credits do I have?"')
  console.log('  "Search for the latest AI agent trends"')
  console.log()

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  })

  const ask = (prompt: string): Promise<string> =>
    new Promise((resolve) => rl.question(prompt, resolve))

  while (true) {
    const userInput = (await ask('You: ')).trim()

    if (!userInput) continue
    if (['quit', 'exit', 'q'].includes(userInput.toLowerCase())) {
      console.log('Goodbye!')
      break
    }

    try {
      const result = await graph.invoke({
        messages: [{ role: 'human', content: userInput }],
      })
      const messages = result.messages || []
      if (messages.length > 0) {
        const final = messages[messages.length - 1]
        const answer = typeof final.content === 'string' ? final.content : JSON.stringify(final.content)
        console.log(`\nAgent: ${answer}\n`)
      } else {
        console.log('\nAgent: No response generated.\n')
      }
    } catch (err: any) {
      console.error(`\nError: ${err.message}\n`)
    }
  }

  rl.close()
}

main().catch(console.error)
