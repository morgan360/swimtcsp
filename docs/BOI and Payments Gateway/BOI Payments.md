# Credit Card Details

4242 4242 4242 4242


---
description: https://developer.bankofireland.com/#!/
---

# BOIP

Hosted Payment Page Integration is designed for technologically enabled merchants who manage systems that provide and manage the full customer shopping experience, but do not have PCI Compliant environments to process payment cards and other cardholder sensitive data. The primary feature of this integration method with the Gateway is that the merchant incorporates the Gateway’s Hosted Payment Page into the website’s checkout page.

The Hosted Payment Page will provide for card payments and alternate payment methods.

Merchants may have:

* eCommerce websites or apps where their customers shop and pay for goods and services online – ECOM transactions
* and/or Customer Order Management system where merchant operators take orders over the phone or from other remote communications methods – MOTO transactions

The merchant’s applications use the Gateway to process payment authorisations and the supporting functionality (captures, voids, refunds, etc.) and 3DS authentications.

An additional feature of this integration method is a Hybrid Integration, where Hosted Payment Page Integrated merchants will also use the Direct API integration in other scenarios (e.g. for repeat transactions (recurring) using a stored card token generated using the Hosted Payment Page).

There are 3 integration modes available for the Hosted Payment Page:

**1. HostedPayPage** (a standard payment page with static **BOIPA/EVO** branding), fully redirected from the merchant site;

**2. Standalone** iFrame (a customisable payment page where fonts/colours may be changed), fully redirected from the merchant site;

**3. Embedded** iFrame (a customisable payment page where fonts/colours may be changed), embedded in a container within the merchant site;

merchant ID: 100121

The Merchant id is 100121, Its Brand id is 1001210000, API password is u0AYACBNI2643G87wk4o

New Message UAT Test Mode

MID: 100121 Brand ID: 1001210000 API Password: qWGEJQQAkhROSTGpwS5O

Please ensure test mode is ticked on the back end. Card Number: 4111 1111 1111 1111 CVV: 111 Expiry: 12/23\

### create local tunnel
npx localtunnel --port 8000
update .env


BOIPA Sandbox

BOIPA offers a free Sandbox test environment for integration testing – you just need to register on their developer portal. In sandbox mode, no real cards are charged, and you can use special test card numbers to trigger specific outcomes. It’s highly recommended to use this sandbox for safe, production-like testing of payment flows. The sandbox HPP behaves like the production gateway, including performing 3D Secure authentication, but uses simulated issuers and outcomes.

3D Secure Test Cards

According to BOIPA’s official test cases, the outcome of a transaction is determined by the card details (and sometimes the inputted 3DS PIN) used. This allows you to script different 3DS v2 scenarios by choosing the right test card.

✅ 3DS Challenge – Successful
Card: Visa 4111 1111 1111 1111 or Mastercard 5454 5454 5454 5454
1. CVV: 123
2. PIN at 3DS screen: 1234
This simulates the customer passing the OTP challenge. It triggers a full 3DS v2 challenge flow and then authorizes the payment successfully. The transaction will complete as a successful payment after the challenge is passed.

❌ 3DS Challenge – Failed
Use the same cards as above
PIN at 3DS screen: 1111
This simulates a failed 3DS authentication, causing the payment to be declined.

✅ 3DS Frictionless – Successful
1. Visa: 4539 7976 0551 9795
2. Mastercard: 5307 8081 6763 5130
3. CVV: 123
These cards trigger a frictionless 3DS v2 flow, meaning no challenge is shown and the payment is authorized immediately — ideal for automated test cases.

❌ 3DS Frictionless – Rejected
Visa: 4923 8429 6241 0313
Mastercard: 5498 9257 1667 5612
CVV: 123
These go through a frictionless flow but are rejected by the issuer, simulating authentication failure without a challenge.

🛑 Cardholder Cancel Scenario
If the user starts a payment with 4111 1111 1111 1111 and cancels at the 3DS prompt, the transaction is canceled. This tests how your app handles mid-flow interruptions or cancellations gracefully.

BOIPA Documentation

All the above test cards and behaviors are defined in BOIPA/EVO’s documentation. Using them in the sandbox HPP simulates the full 3DS v2 protocol (either frictionless or challenge), including redirects to the ACS (Access Control Server) simulator for 3DS input when applicable.

Other Test Triggers

In addition to 3DS scenarios, the BOIPA UAT environment supports amount-based authorization triggers:

0.08 → returns a "Do not honor" error
0.05 → returns an "Invalid merchant" error
These are useful for testing how your system handles declines or error responses. (Note: amount-based triggers apply mostly in direct API use. If you're only using HPP with normal amounts, you’ll rely mainly on test cards.)


