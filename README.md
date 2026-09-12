# BuyWise AI — Intelligent Financial Decision Agent

> **Know Before You Buy.**

BuyWise AI is an AI-powered financial decision agent designed to determine whether a user can safely afford a requested expense.

Instead of looking only at the user's current account balance, BuyWise AI evaluates the user's broader financial situation, including recurring expenses, pending payments, confirmed income, essential spending, flexible expenses, payment options, financial commitments, and relevant information extracted from messages or images.

The system can recommend whether the user should:

* Pay in full
* Pay partially
* Use installments
* Wait until a safer date
* Reduce flexible spending
* Avoid proceeding with the purchase

The primary goal is **financial safety rather than simply maximizing purchasing power**.

---

## Overview

A simple affordability system might use:

```text
Current Balance >= Purchase Price
```

However, this approach can produce unsafe recommendations.

For example:

```text
Current Balance:        $5,000
Laptop Price:           $4,000
Upcoming Rent:          $2,000
Essential Expenses:    $1,000
Minimum Balance:        $1,000
```

Although the user technically has enough money to purchase the laptop, paying $4,000 immediately could cause the user's future balance to fall below the required safety level.

BuyWise AI therefore evaluates the **future cashflow**, not just the current balance.

---

## Core Objective

For every financial request, BuyWise AI determines:

```text
amount_safe_to_pay
affordability_status
recommended_payment_method
payment_plan
earliest_date_for_full_payment
spending_changes_needed
decision_explanation
```

A recommendation is considered safe only when the proposed payment strategy allows the user to:

1. Complete the required payment plan.
2. Cover essential expenses.
3. Handle known financial commitments.
4. Account for pending payments.
5. Use confirmed income appropriately.
6. Maintain the user's preferred minimum balance throughout the forecast period.

---

## Key Features

### 1. Financial Profile Construction

BuyWise AI creates a structured financial profile containing relevant information such as:

* Current balance
* Confirmed income
* Expected income
* Recurring expenses
* Essential expenses
* Flexible expenses
* Pending payments
* Existing commitments
* Minimum balance preference
* Payment preferences

---

### 2. Request Parsing

The system converts each financial request into structured information.

Conceptually:

```text
User Request
     |
     v
Request Parser
     |
     +---- Purchase Information
     |
     +---- Financial Context
     |
     +---- Payment Preferences
     |
     v
Structured Request
```

---

### 3. CSV Financial Data Processing

The system reads the provided request dataset and converts the input records into structured financial information.

```text
requests.csv
     |
     v
CSV Loader
     |
     v
Request Parser
     |
     v
Financial Profile
```

The implementation is designed to process input data dynamically rather than relying on hardcoded answers for individual test cases.

---

### 4. Message Information Extraction

Relevant financial information can appear inside natural-language messages.

For example:

```text
"My salary will arrive on September 25."
```

The extraction layer can identify:

```text
Type: Income
Date: September 25
Status: Confirmed/Expected
```

This information is then passed to the deterministic financial engine.

---

### 5. Media and Image Information Extraction

When relevant local media or images are provided, the system can use a VLM-based extraction layer to identify financial information such as:

* Amount
* Merchant
* Due date
* Payment status
* Transaction information
* Relevant financial commitments

The extracted information is converted into structured data before entering the financial calculation pipeline.

---

## System Architecture

```text
                    +---------------------+
                    |    requests.csv     |
                    +----------+----------+
                               |
                               v
                    +---------------------+
                    |   Request Parser    |
                    +----------+----------+
                               |
                    +----------+----------+
                    |                     |
                    v                     v
          +----------------+     +----------------+
          | CSV Financial  |     | Message / VLM  |
          | Data           |     | Extractor      |
          +-------+--------+     +-------+--------+
                  |                      |
                  +----------+-----------+
                             |
                             v
                  +----------------------+
                  |  Financial Profile   |
                  +----------+-----------+
                             |
                             v
                  +----------------------+
                  |  Cashflow Forecast   |
                  +----------+-----------+
                             |
                             v
                  +----------------------+
                  | Scenario Simulator   |
                  |                      |
                  | Full Payment         |
                  | Partial Payment      |
                  | Installment          |
                  | Wait                 |
                  | Reduce Spending      |
                  +----------+-----------+
                             |
                             v
                  +----------------------+
                  |  Safety Validator    |
                  +----------+-----------+
                             |
                             v
                  +----------------------+
                  |   Decision Engine    |
                  +----------+-----------+
                             |
                             v
                  +----------------------+
                  |  LLM Explanation     |
                  +----------+-----------+
                             |
                             v
                  +----------------------+
                  |      output.csv      |
                  +----------------------+
```

---

# Architecture Principles

## Deterministic Financial Computation

Financial calculations should not depend entirely on generative AI.

BuyWise AI separates:

```text
AI Reasoning
```

from:

```text
Financial Calculation
```

LLM/VLM components are primarily responsible for:

* Context understanding
* Information extraction
* Natural-language interpretation
* Explanation generation

Deterministic Python components are responsible for:

* Balance calculations
* Cashflow forecasting
* Payment calculations
* Date calculations
* Scenario simulation
* Minimum-balance validation
* Final safety checks

This separation reduces the risk of an LLM generating financially inconsistent numerical decisions.

---

# Financial Decision Pipeline

## Step 1 — Load Request

The system reads a request from the provided dataset.

```text
requests.csv
      |
      v
Request Parser
```

---

## Step 2 — Build Financial Profile

The system gathers available financial information:

```text
Current Balance
Confirmed Income
Recurring Expenses
Essential Expenses
Flexible Expenses
Pending Payments
Financial Commitments
Minimum Balance
Payment Preferences
```

---

## Step 3 — Forecast Cashflow

The system calculates how the user's financial position changes over time.

Conceptually:

```text
Future Balance
=
Current Balance
+ Confirmed Income
- Essential Expenses
- Pending Payments
- Planned Payments
- Existing Commitments
```

The forecast is evaluated over the relevant planning horizon.

---

## Step 4 — Generate Payment Scenarios

BuyWise AI evaluates multiple strategies.

### Full Payment

```text
Pay the entire purchase amount immediately.
```

### Partial Payment

```text
Pay an affordable amount initially
and handle the remaining amount later.
```

### Installment

```text
Divide the purchase into scheduled payments.
```

### Wait

```text
Delay the purchase until a safer date.
```

### Reduce Flexible Spending

```text
Reduce or pause adjustable expenses
to make the purchase safer.
```

---

## Step 5 — Validate Safety

Every candidate payment plan is checked against the financial forecast.

A plan is rejected if it causes the user's balance to fall below the required minimum balance during the forecast period.

Conceptually:

```text
For every forecast date:

    if balance < minimum_balance:
        plan = UNSAFE
```

This prevents the agent from recommending a purchase that looks affordable today but becomes financially unsafe later.

---

## Step 6 — Select the Safest Recommendation

The decision engine compares valid scenarios and selects an appropriate strategy.

Conceptually:

```text
             Can pay safely today?
                       |
              +--------+--------+
              |                 |
             YES                NO
              |                 |
         Pay in Full       Can use safe plan?
                                |
                         +------+------+
                         |             |
                        YES            NO
                         |             |
                    Payment Plan     Can wait?
                                      |
                               +------+------+
                               |             |
                              YES            NO
                               |             |
                             WAIT       DO NOT PROCEED
```

The exact output values follow the schema defined by the challenge spec
