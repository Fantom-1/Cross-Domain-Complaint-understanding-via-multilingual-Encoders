# Intent Taxonomy Annotation Codebook (v2.0)

**Project:** Cross-Domain Complaint Understanding via Multilingual Encoders  
**Phase:** Phase 6 (Label Taxonomy and Human-Validity Audit)  
**Task Formulation:** Single-label multi-class intent classification for consumer financial complaints (16 closed-set classes).  
**Scope:** English CFPB Consumer Complaint Database narratives and comparative benchmarking against auxiliary short queries (`PolyAI/banking77`).  

---

> [!IMPORTANT]
> **Epistemological Governance & Supervision Boundary:**  
> CFPB administrative metadata fields (`Product`, `Issue`, `Sub-issue`) reflect intake bureau routing categorizations chosen by consumers or intake processors from a fixed, predefined picklist. They represent **weak administrative supervision**, not semantic gold labels. The codebook below governs independent human adjudication of true consumer intent from unconstrained narrative text.

---

## 1. General Annotation Protocol & Decision Rules

1. **Primary Intent Principle:** When a narrative expresses multiple consumer grievances (multi-issue narrative), annotators must identify the **primary actionable harm** or predominant relief requested by the consumer.
2. **Blinded Evaluation:** Annotators must evaluate complaints blinded to CFPB administrative metadata (`Product`, `Issue`, `Sub-issue`), company responses, and any model proposals.
3. **Multi-Issue Flagging:** If a complaint contains two or more distinct substantive legal or financial allegations (e.g., identity theft *and* credit bureau failure to delete an inquiry *and* collector harassment), the annotator assigns the primary intent to `annotator_label` and sets `multi_issue_flag = True`, listing secondary intents in `secondary_labels`.
4. **Ambiguity & Abstention Policy:** If a narrative is so truncated, incomprehensible, or self-contradictory that no primary intent can be determined with reasonable confidence, set `ambiguity_flag = True`. In closed-set classification, annotators assign the closest plausible class or route to adjudication.
5. **No Synthetic Merging:** Classes must remain semantically distinct. String overlap or shared financial terminology does not justify collapsing boundaries.

---

## 2. The 16 Target Intent Classes: Definitions & Boundary Rules

### Intent 0: `reporting_incorrect_information`
* **Intent ID:** 0
* **Definition:** Disputes asserting that factually inaccurate, erroneous, outdated, or fabricated data items appear on the consumer's credit report or consumer file.
* **Positive Inclusions:** Inaccurate account balances, wrong account status (e.g., reported delinquent when paid current), incorrect payment dates, misattributed public records, wrong personal identifying details.
* **Negative Exclusions:** Procedural delays or failures in how the credit bureau investigated a previously filed dispute (assign `reporting_investigation_dispute`). Unauthorized hard inquiries without a balance error (assign `reporting_improper_use`).
* **Boundary Clarification:** If the consumer solely says "there is an error on my credit report", label `reporting_incorrect_information`. If the consumer emphasizes "I sent proof 45 days ago and the bureau refuses to delete or respond", label `reporting_investigation_dispute`.

### Intent 1: `reporting_investigation_dispute`
* **Intent ID:** 1
* **Definition:** Complaints regarding procedural failures, statutory non-compliance (FCRA 30-day window), superficial automated review, or lack of response by a credit reporting agency or data furnisher during a dispute investigation.
* **Positive Inclusions:** Credit bureau failing to conduct a reasonable investigation, failing to provide investigation results or method of verification within 30 days, rubber-stamping furnisher responses, refusing to forward consumer documents to furnishers.
* **Negative Exclusions:** Merely discovering an erroneous line item on a report without mentioning a previous dispute (assign `reporting_incorrect_information`). Loan servicer failing to respond to a QWR/RESPA notice (assign `servicing_dispute`).
* **Boundary Clarification:** Requires mention of a previously submitted dispute or procedural breakdown in the statutory investigation process.

### Intent 2: `reporting_improper_use`
* **Intent ID:** 2
* **Definition:** Unauthorized access to consumer reports, impermissible inquiries, credit monitoring failures, or technical denial of consumer access to their statutory file disclosure.
* **Positive Inclusions:** Hard credit inquiries executed without permissible purpose or consumer consent; failure of credit monitoring services to notify of inquiries; inability to access free annual file disclosures.
* **Negative Exclusions:** Actual fraudulent accounts or identity theft lines opened in the consumer's name (assign `fraud_or_scam`). Inability to log in to an online bank portal (assign `account_access`).
* **Boundary Clarification:** Involves credit report *viewing / inquiry / monitoring access*, not actual fraudulent financial transactions.

### Intent 3: `fraud_or_scam`
* **Intent ID:** 3
* **Definition:** Allegations of identity theft, criminal impersonation, unauthorized fund transfers/withdrawals, merchant scams, phishing, or mishandling of fraud alerts and security freezes.
* **Positive Inclusions:** Accounts fraudulently opened by third parties; forged signatures; unauthorized wire/debit card transfers; failure of institutions to honor statutory fraud blocks; account takeover scams.
* **Negative Exclusions:** Ordinary billing disagreements with a recognized merchant where the consumer authorized the transaction (assign `transaction_problem`). Debt collector attempting to collect on an unfamiliar old debt without proof of fraud (assign `debt_not_owed`).
* **Boundary Clarification:** Requires an explicit element of third-party deceit, unauthorized takeover, impersonation, or identity theft.

### Intent 4: `debt_not_owed`
* **Intent ID:** 4
* **Definition:** Collection efforts directed against a consumer for a debt they do not owe, that was already paid in full, satisfied in settlement, discharged in bankruptcy, or belongs to another individual.
* **Positive Inclusions:** Demands for payment on discharged debts; debts belonging to an ex-spouse or stranger; debts already paid; zombie debts beyond statute of limitations where liability is denied.
* **Negative Exclusions:** Objections to collector calling times or aggressive tone on a valid debt (assign `debt_communication` or `debt_threats`). Debts resulting from identity theft where the consumer asserts criminal fraud (assign `fraud_or_scam`).
* **Boundary Clarification:** The core dispute is the *non-existence or invalidity of the debt obligation itself*.

### Intent 5: `debt_threats`
* **Intent ID:** 5
* **Definition:** Unlawful harassment, abusive threats, false legal assertions, or impermissible third-party disclosures by debt collectors (FDCPA violations).
* **Positive Inclusions:** Threats of immediate arrest, police action, criminal charges, or immediate home seizure; abusive, profane, or derogatory language; calling friends, family, or employers to publicly humiliate the consumer.
* **Negative Exclusions:** Merely calling repeatedly without threats (assign `debt_communication`). Calling to collect an erroneous debt without abuse (assign `debt_not_owed`).
* **Boundary Clarification:** Coercive, abusive, or explicitly unlawful threats and harassment define this class.

### Intent 6: `debt_communication`
* **Intent ID:** 6
* **Definition:** Procedural FDCPA communication violations, including failure to send statutory debt validation notices (G-notice), calling before 8:00 AM or after 9:00 PM, calling after receipt of written cease-and-desist, or excessive robocalling.
* **Positive Inclusions:** Failure to verify debt upon request; ignoring written cease-and-desist letters; continuous phone harassment without explicit criminal threats; calling workplace after being told employer prohibits it.
* **Negative Exclusions:** Threats of physical harm or false legal claims (assign `debt_threats`). Denying the debt exists (assign `debt_not_owed`).
* **Boundary Clarification:** Focuses on the *manner, timing, frequency, and procedural notice requirements* of collector communications.

### Intent 7: `payment_problem`
* **Intent ID:** 7
* **Definition:** Friction, errors, or servicer failures in the processing, crediting, allocation, or execution of loan payments or recurring billing debits.
* **Positive Inclusions:** Payments posted late despite timely delivery; payments misapplied to principal vs interest or wrong escrow account; double automated clearing house (ACH) withdrawals; inability to cancel autopay.
* **Negative Exclusions:** Point-of-sale card checkout declines or merchant billing overcharges (assign `transaction_problem`). Bank placing holds on deposited checks (assign `funds_availability`).
* **Boundary Clarification:** Involves incoming payments directed to a lender, loan servicer, or biller, rather than point-of-sale merchant purchases.

### Intent 8: `transaction_problem`
* **Intent ID:** 8
* **Definition:** Discrepancies, merchant billing disputes, incorrect charges, card transaction failures, or unrecognized retail point-of-sale fees on checking, savings, or credit card accounts.
* **Positive Inclusions:** Merchant charged twice for a single purchase; wrong amount billed at register; ATM failed to dispense cash but debited account; merchant refund not credited; chargeback request rejected.
* **Negative Exclusions:** Unauthorized third-party identity theft or card skim fraud (assign `fraud_or_scam`). Routine monthly account maintenance fees (assign `credit_terms_dispute` or `account_management`).
* **Boundary Clarification:** Transaction-level commercial disputes where the consumer engaged with a merchant or terminal, distinguished from pure criminal fraud (`fraud_or_scam`).

### Intent 9: `funds_availability`
* **Intent ID:** 9
* **Definition:** Delays, unexpected holds, or temporary freezes placed on deposited checks, cash deposits, mobile wallet balances, or incoming peer-to-peer wire transfers (Expedited Funds Availability Act / Regulation CC).
* **Positive Inclusions:** Check deposit held beyond statutory 2–5 business days; mobile check deposit delayed; PayPal/Venmo balance frozen pending review; wire transfer funds not available.
* **Negative Exclusions:** Complete and permanent account closure or portal lockdown (assign `account_access`). Account balance depleted by unauthorized theft (assign `fraud_or_scam`).
* **Boundary Clarification:** Focuses on the *timing and availability of deposited funds* in an otherwise active account.

### Intent 10: `account_access`
* **Intent ID:** 10
* **Definition:** Complete loss of account access, unannounced account suspension or freeze, locked digital banking credentials, or forced unilateral account closure by the financial institution.
* **Positive Inclusions:** Consumer locked out of online/mobile banking without recourse; institution unilaterally closed checking account without returning residual funds; branch refuses entry or service.
* **Negative Exclusions:** Temporary hold on a single check deposit while rest of account works (assign `funds_availability`). Routine requests to update account contact details (assign `account_management`).
* **Boundary Clarification:** Involves *systemic loss of access to the account or portal itself*, or unilateral termination of the banking relationship.

### Intent 11: `account_management`
* **Intent ID:** 11
* **Definition:** General operational friction in maintaining, servicing, updating, or administering an existing open financial account.
* **Positive Inclusions:** Delays in updating beneficiary or address records; difficulties opening a new secondary checking account; failure to deliver physical replacement debit cards; customer service runaround regarding account maintenance.
* **Negative Exclusions:** Dispute over unexpected interest rates or hidden fees (assign `credit_terms_dispute`). Total lockout from account (assign `account_access`).
* **Boundary Clarification:** Routine administrative and account lifecycle operations that do not rise to payment misallocation, fraud, or full lockout.

### Intent 12: `servicing_dispute`
* **Intent ID:** 12
* **Definition:** Substantive servicing breakdowns on loans or mortgages, including escrow calculations, insurance forced-placement, loan modification reviews, or transfer of servicing rights (RESPA / Regulation X).
* **Positive Inclusions:** Improper calculation of mortgage escrow shortage; forced-placement of expensive hazard insurance despite proof of coverage; loss mitigation or loan modification application mishandled; failure to honor prior servicer terms.
* **Negative Exclusions:** Routine single monthly payment misapplication (assign `payment_problem`). Application for a brand-new loan origination (assign `application_problem`).
* **Boundary Clarification:** Governs complex, ongoing loan administration (especially mortgage and student loan servicing), escrow, and modification disputes.

### Intent 13: `application_problem`
* **Intent ID:** 13
* **Definition:** Problems, unreasonable delays, discriminatory denials, deceptive pre-approvals, or procedural friction during the origination or application process for a loan, mortgage, or credit card.
* **Positive Inclusions:** Misleading pre-approved loan offers; application fees charged without processing; unexplained application denial without adverse action notice; deceptive sales tactics during loan origination.
* **Negative Exclusions:** Disputes arising during final mortgage closing and settlement disclosures (assign `closing_process`). Fraudulent credit card opened by a stranger (assign `fraud_or_scam`).
* **Boundary Clarification:** Confined to the *intake, origination, underwriting, and pre-closing* phase of acquiring credit or loans.

### Intent 14: `credit_terms_dispute`
* **Intent ID:** 14
* **Definition:** Disputes regarding unexpected interest rate increases, penalty APRs, sudden credit line reductions, misleading promotional offers, reward point clawbacks, or hidden account maintenance fees (CARD Act / TILA).
* **Positive Inclusions:** Credit card interest rate hiked without required 45-day notice; promotional 0% APR canceled early; credit card limit cut drastically without justification; reward points forfeited unfairly; unexpected monthly maintenance fees.
* **Negative Exclusions:** Late fees incurred due to payment processing delays (assign `payment_problem`). Merchant charging wrong sales tax or item price (assign `transaction_problem`).
* **Boundary Clarification:** Focuses on the *contractual pricing, interest rates, credit limits, promotional promises, and fee structures* governed by credit agreements.

### Intent 15: `closing_process`
* **Intent ID:** 15
* **Definition:** Friction, misrepresentations, fee inflations, or settlement delays occurring at the final closing, signing, or title settlement of a mortgage or real estate loan (TRID / RESPA closing disclosures).
* **Positive Inclusions:** Closing Disclosure provided late or containing surprise closing costs/points; loan terms at closing table differing from Loan Estimate; settlement agent delays causing rate-lock expiration; escrow funding failures at settlement.
* **Negative Exclusions:** Initial loan application or underwriting delays (assign `application_problem`). Ongoing mortgage servicing years after closing (assign `servicing_dispute`).
* **Boundary Clarification:** Strictly confined to the *settlement, closing table, and escrow closing transaction*.

---

## 3. Confusable Pairs & Priority Resolution Table

| Confusable Pair | Distinguishing Criterion | Priority Rule |
| :--- | :--- | :--- |
| `reporting_incorrect_information` vs. `reporting_investigation_dispute` | Error existence vs. investigation failure | If procedural investigation failure (30-day lapse, refusal to investigate) is explicitly stated, prioritize `reporting_investigation_dispute`. |
| `reporting_improper_use` vs. `fraud_or_scam` | Inquiry/monitoring view vs. financial theft/account opening | If unauthorized accounts were created or money stolen, prioritize `fraud_or_scam`. If only hard inquiries occurred, prioritize `reporting_improper_use`. |
| `payment_problem` vs. `transaction_problem` | Lenders/servicers vs. retail merchants/ATMs | Payments to pay bills/loans are `payment_problem`. POS retail purchases, merchant billing, ATM withdrawals are `transaction_problem`. |
| `debt_not_owed` vs. `debt_communication` vs. `debt_threats` | Liability dispute vs. timing/manner vs. abusive threats | If debt validity is disputed, prioritize `debt_not_owed`. If harassment/threats of arrest exist, prioritize `debt_threats`. If contact timing/validation notice issue, prioritize `debt_communication`. |
| `account_access` vs. `funds_availability` | Entire account lockout vs. hold on deposit | If user cannot log in or account is unilaterally shut down, prioritize `account_access`. If account is functional but deposit held, prioritize `funds_availability`. |
| `application_problem` vs. `closing_process` | Origination/underwriting vs. closing table/settlement | Origination and approval problems are `application_problem`. Final closing disclosures and settlement fees are `closing_process`. |
| `servicing_dispute` vs. `payment_problem` | Ongoing complex loan terms/escrow vs. single payment posting | Escrow analysis, loan modifications, and servicer transfers are `servicing_dispute`. Specific missed payment allocation or double debits are `payment_problem`. |

---

## 4. Multi-Issue and Ambiguity Policy Summary

```
                      ┌──────────────────────────────────────┐
                      │ Complaint Narrative Text Received    │
                      └──────────────────┬───────────────────┘
                                         │
                    Is text intelligible and substantive?
                                    /         \
                                  Yes          No ──> Set ambiguity_flag = True
                                  /
            Does narrative contain >= 2 distinct issues?
                           /                     \
                         Yes                      No
                         /                         \
           Identify Primary Actionable Harm         Assign Single Intent
           Set multi_issue_flag = True
           Record Secondary Intents
```
