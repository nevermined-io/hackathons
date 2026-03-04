/**
 * Scripted x402 HTTP client — demonstrates the full buyer payment flow.
 *
 * Shows the complete x402 HTTP protocol against the seller:
 * 1. GET /health        - check the seller is up
 * 2. GET /pricing       - discover pricing tiers
 * 3. POST /data (no token) -> 402 Payment Required
 * 4. Generate x402 access token
 * 5. POST /data (with token) -> 200 OK
 * 6. Decode settlement receipt
 *
 * Usage:
 *   # First start the seller: cd ../seller-simple-agent/ts && npm run server
 *   # Then run this client:
 *   npm run client
 */

import { config } from 'dotenv'
config({ path: '../.env' })

import { Payments } from '@nevermined-io/payments'

const SELLER_URL = process.env.SELLER_URL || 'http://localhost:3000'
const NVM_API_KEY = process.env.NVM_SUBSCRIBER_API_KEY || process.env.NVM_API_KEY || ''
const NVM_PLAN_ID = process.env.NVM_PLAN_ID || ''
const NVM_AGENT_ID = process.env.NVM_AGENT_ID || ''
const NVM_ENVIRONMENT = process.env.NVM_ENVIRONMENT || 'sandbox'

if (!NVM_API_KEY || !NVM_PLAN_ID) {
  console.error('NVM_SUBSCRIBER_API_KEY (or NVM_API_KEY) and NVM_PLAN_ID are required.')
  process.exit(1)
}

function decodeBase64Json(value: string): Record<string, any> {
  return JSON.parse(Buffer.from(value, 'base64').toString('utf-8'))
}

function pretty(obj: Record<string, any>): string {
  return JSON.stringify(obj, null, 2)
}

async function main() {
  console.log('='.repeat(60))
  console.log('x402 Buyer Flow — Data Buying Agent (TypeScript)')
  console.log('='.repeat(60))
  console.log(`\nSeller:  ${SELLER_URL}`)
  console.log(`Plan ID: ${NVM_PLAN_ID}`)

  const payments = Payments.getInstance({
    nvmApiKey: NVM_API_KEY,
    environment: NVM_ENVIRONMENT as any,
  })

  // --- Step 1: Health check ---
  console.log('\n' + '='.repeat(60))
  console.log('STEP 1: Health check')
  console.log('='.repeat(60))

  const healthResp = await fetch(`${SELLER_URL}/health`)
  console.log(`\nGET /health -> ${healthResp.status}`)
  console.log(pretty(await healthResp.json()))

  // --- Step 2: Discover pricing ---
  console.log('\n' + '='.repeat(60))
  console.log('STEP 2: Discover pricing tiers')
  console.log('='.repeat(60))

  const pricingResp = await fetch(`${SELLER_URL}/pricing`)
  console.log(`\nGET /pricing -> ${pricingResp.status}`)
  console.log(pretty(await pricingResp.json()))

  // --- Step 3: Request without token -> 402 ---
  console.log('\n' + '='.repeat(60))
  console.log('STEP 3: Request without payment token')
  console.log('='.repeat(60))

  const resp402 = await fetch(`${SELLER_URL}/data`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: 'AI agent market trends 2025' }),
  })

  console.log(`\nPOST /data -> ${resp402.status} ${resp402.statusText}`)
  console.log(pretty(await resp402.json()))

  if (resp402.status !== 402) {
    console.error(`Expected 402, got ${resp402.status}`)
    process.exit(1)
  }

  // --- Step 4: Decode requirements + generate token ---
  console.log('\n' + '='.repeat(60))
  console.log('STEP 4: Generate x402 access token')
  console.log('='.repeat(60))

  const prHeader = resp402.headers.get('payment-required')
  if (prHeader) {
    console.log('\nDecoded payment-required:')
    console.log(pretty(decodeBase64Json(prHeader)))
  }

  console.log('\nCalling payments.x402.getX402AccessToken()...')
  const tokenResult = await payments.x402.getX402AccessToken(
    NVM_PLAN_ID,
    NVM_AGENT_ID || undefined,
  )
  const accessToken = tokenResult.accessToken
  console.log(`Token generated! Length: ${accessToken.length} chars`)
  console.log(`Preview: ${accessToken.slice(0, 50)}...`)

  // --- Step 5: Request with token -> 200 ---
  console.log('\n' + '='.repeat(60))
  console.log('STEP 5: Purchase data with payment token')
  console.log('='.repeat(60))

  console.log("\nSending POST /data with 'payment-signature' header...")
  const resp200 = await fetch(`${SELLER_URL}/data`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'payment-signature': accessToken,
    },
    body: JSON.stringify({ query: 'AI agent market trends 2025' }),
  })

  console.log(`\nPOST /data -> ${resp200.status} ${resp200.statusText}`)

  if (resp200.status !== 200) {
    console.error(`Expected 200, got ${resp200.status}`)
    console.error(await resp200.text())
    process.exit(1)
  }

  console.log('\nResponse body:')
  console.log(pretty(await resp200.json()))

  // --- Step 6: Settlement receipt ---
  console.log('\n' + '='.repeat(60))
  console.log('STEP 6: Settlement receipt')
  console.log('='.repeat(60))

  const prResponse = resp200.headers.get('payment-response')
  if (prResponse) {
    const settlement = decodeBase64Json(prResponse)
    console.log('\nSettlement receipt:')
    console.log(pretty(settlement))
    console.log('\nKey fields:')
    console.log(`  Credits charged:    ${settlement.creditsRedeemed ?? 'N/A'}`)
    console.log(`  Remaining balance:  ${settlement.remainingBalance ?? 'N/A'}`)
  } else {
    console.log('\nNo payment-response header (settlement may have been skipped)')
  }

  // --- Summary ---
  console.log('\n' + '='.repeat(60))
  console.log('FLOW COMPLETE!')
  console.log('='.repeat(60))
  console.log(`
x402 Buyer Flow Summary:
1. GET  /health              -> Seller is up
2. GET  /pricing             -> Discovered pricing tiers
3. POST /data (no token)     -> 402 Payment Required
4. Generated access token    -> Using Nevermined SDK
5. POST /data (with token)   -> 200 OK + data response
6. Decoded settlement        -> Credits charged & remaining
`)
}

main().catch(console.error)
