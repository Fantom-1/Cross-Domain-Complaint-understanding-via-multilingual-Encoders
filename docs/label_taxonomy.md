# Intent Label Taxonomy & Ontology Specification

**Project:** Cross-Domain Complaint Understanding via Multilingual Encoders  
**Version:** 1.0  
**Phase:** Phase A (Data Preparation)  
**Total Classes:** 16  
**Task Formulation:** Single-label multi-class intent classification for consumer financial complaints.

---

## 1. Design Principles

1. **Semantic Grounding in Real Data:** The taxonomy is derived directly from observed CFPB complaint issue/sub-issue categories and consumer narratives, rather than synthetic or abstract query intents.
2. **Mutual Exclusivity & Distinct Boundaries:** Classes represent actionable consumer intents (e.g. disputing inaccurate credit reporting vs. objecting to debt collection communication tactics).
3. **No Name-Only Merging:** Labels are not merged purely because string tokens overlap. Each mapping requires semantic equivalence.
4. **Closed-Set Safety:** A classifier can only predict labels present in its training label map. Any unmapped or ambiguous source issue is explicitly recorded as unmapped and excluded from the closed-set baseline.

---

## 2. Intent Class Definitions & Boundary Rules

### Intent 0: `reporting_incorrect_information`
- **Definition:** The consumer asserts that factually inaccurate, obsolete, or erroneous information appears on their credit report or consumer profile.
- **Inclusions:** Inaccurate account status, incorrect payment history, wrong balance or personal identification details reported by credit bureaus.
- **Exclusions:** Procedural complaints about how an investigation was conducted (use `reporting_investigation_dispute`).
- **Confusable Classes:** `reporting_investigation_dispute`, `reporting_improper_use`.
- **CFPB Match Patterns:** `"incorrect information on your report"`, `"incorrect information on credit report"`.

### Intent 1: `reporting_investigation_dispute`
- **Definition:** Complaints regarding the procedural failure, unreasonable delay, or superficial dismissal of a dispute investigation by a credit reporting company.
- **Inclusions:** Failure to investigate within statutory deadlines, rubber-stamping furnisher responses, refusing to provide investigation results.
- **Exclusions:** Initial assertion that data is wrong (use `reporting_incorrect_information`).
- **Confusable Classes:** `reporting_incorrect_information`, `servicing_dispute`.
- **CFPB Match Patterns:** `"investigation into an existing problem"`, `"investigation into existing problem"`, `"credit reporting company's investigation"`.

### Intent 2: `reporting_improper_use`
- **Definition:** Impermissible access, unauthorized hard inquiries, failure of credit monitoring, or inability of the consumer to obtain their own credit report.
- **Inclusions:** Inquiries without permissible purpose, credit monitoring alerts failing to notify, technical inability to access report.
- **Exclusions:** Fraudulent transactions on credit cards (use `fraud_or_scam`).
- **Confusable Classes:** `fraud_or_scam`, `account_access`.
- **CFPB Match Patterns:** `"improper use of your report"`, `"unable to get your credit report"`, `"credit monitoring or identity theft"`.

### Intent 3: `fraud_or_scam`
- **Definition:** Identity theft, unauthorized financial debits, fraudulent impersonation, or mishandling of fraud alerts and security freezes.
- **Inclusions:** Third-party identity theft, unauthorized wire/card transactions, security freeze failures.
- **Exclusions:** Merchant billing disputes where the transaction was authorized (use `transaction_problem`).
- **Confusable Classes:** `reporting_improper_use`, `transaction_problem`.
- **CFPB Match Patterns:** `"fraud or scam"`, `"unauthorized transaction"`, `"identity theft"`, `"problem with fraud alerts or security freezes"`.

### Intent 4: `debt_not_owed`
- **Definition:** Collection attempts targeting a consumer for a debt they do not owe, that was already paid, discharged in bankruptcy, or belongs to another party.
- **Inclusions:** Debt never incurred, identity confusion, paid-in-full accounts subject to collection.
- **Exclusions:** Disputes regarding the communication method or frequency of debt collectors (use `debt_communication`).
- **Confusable Classes:** `debt_communication`, `debt_threats`.
- **CFPB Match Patterns:** `"attempts to collect debt not owed"`, `"cont'd attempts collect debt not owed"`.

### Intent 5: `debt_threats`
- **Definition:** Unlawful harassment, abusive threats, false legal assertions, or impermissible disclosure of debt to employers/family.
- **Inclusions:** Threats of arrest, wage garnishment without judgment, abusive language, contacting third parties.
- **Exclusions:** Simple written validation notices (use `debt_communication`).
- **Confusable Classes:** `debt_communication`, `debt_not_owed`.
- **CFPB Match Patterns:** `"took or threatened to take negative or legal action"`, `"false statements or representation"`, `"threatened to contact someone"`.

### Intent 6: `debt_communication`
- **Definition:** Collector failure to provide mandatory debt validation notices, calling at prohibited hours, or ignoring cease-and-desist communications.
- **Inclusions:** Lack of debt verification disclosures, excessive repeated calls, improper electronic communications.
- **Exclusions:** Threatening illegal action (use `debt_threats`).
- **Confusable Classes:** `debt_threats`.
- **CFPB Match Patterns:** `"written notification about debt"`, `"communication tactics"`, `"disclosure verification of debt"`, `"electronic communications"`.

### Intent 7: `payment_problem`
- **Definition:** Failure of the lender/servicer to properly credit, process, allocate, or acknowledge incoming payments.
- **Inclusions:** Payments applied to wrong fees/balances, double-deductions, uncredited payments, inability to stop recurring automated debits.
- **Exclusions:** Merchant point-of-sale terminal errors (use `transaction_problem`).
- **Confusable Classes:** `transaction_problem`, `funds_availability`.
- **CFPB Match Patterns:** `"trouble during payment process"`, `"struggling to pay"`, `"problem when making payments"`, `"payment to acct not credited"`, `"making/receiving payments"`, `"problem with a lender or other company charging your account"`, `"can't stop withdrawals"`.

### Intent 8: `transaction_problem`
- **Definition:** Point-of-sale merchant charge discrepancies, card payment declines, incorrect transaction amounts on billing statements, or unexpected service fees.
- **Inclusions:** Card terminal errors, chargebacks improperly denied, merchant overcharges.
- **Exclusions:** Unauthorized identity theft transactions (use `fraud_or_scam`).
- **Confusable Classes:** `payment_problem`, `fraud_or_scam`.
- **CFPB Match Patterns:** `"problem with a purchase shown on your statement"`, `"other transaction problem"`, `"other service problem"`, `"unexpected or other fees"`, `"trouble using your card"`, `"problem with a purchase or transfer"`.

### Intent 9: `funds_availability`
- **Definition:** Delays, unexpected holds, or temporary un-availability of deposited funds, mobile wallet balances, or wire transfers.
- **Inclusions:** Check clearance holds beyond statutory guidelines, mobile wallet withdrawal freezes.
- **Exclusions:** Permanent account closure without access (use `account_access`).
- **Confusable Classes:** `account_access`, `transaction_problem`.
- **CFPB Match Patterns:** `"problem caused by your funds being low"`, `"managing, opening, or closing your mobile wallet"`, `"deposits and withdrawals"`, `"money was not available when promised"`, `"money was taken from your bank account on the wrong day"`.

### Intent 10: `account_access`
- **Definition:** Complete loss of access to an account, inability to log in, unannounced account freezing, or forced account termination.
- **Inclusions:** Inability to access portal, sudden account closure without notice, frozen account status.
- **Exclusions:** General service requests like updating an address (use `account_management`).
- **Confusable Classes:** `account_management`, `funds_availability`.
- **CFPB Match Patterns:** `"can't access"`, `"cannot access"`, `"trouble accessing"`, `"closing your account"`, `"closing an account"`, `"account status"`.

### Intent 11: `account_management`
- **Definition:** General operational and administrative friction in managing, opening, or maintaining an ongoing account.
- **Inclusions:** Opening delays, lease/loan profile modifications, beneficiary updates.
- **Exclusions:** Total inability to access portal (use `account_access`).
- **Confusable Classes:** `account_access`, `servicing_dispute`.
- **CFPB Match Patterns:** `"managing an account"`, `"opening an account"`, `"account opening, closing, or management"`, `"managing the loan or lease"`, `"managing, opening, or closing account"`.

### Intent 12: `servicing_dispute`
- **Definition:** Disputes concerning ongoing loan administration, customer service failures, escrow calculation discrepancies, payoff quotes, or repossession procedures.
- **Inclusions:** Loan servicer miscalculations, escrow shortages, payoff statement delays, repossession without required notice.
- **Exclusions:** Routine payment crediting issues (use `payment_problem`).
- **Confusable Classes:** `payment_problem`, `account_management`.
- **CFPB Match Patterns:** `"dealing with your lender or servicer"`, `"loan servicing, payments, escrow account"`, `"problem with customer service"`, `"repossession"`, `"problems at the end of the loan or lease"`, `"problem with the payoff process"`.

### Intent 13: `application_problem`
- **Definition:** Friction, delays, misleading broker information, or unexplained denials during credit/loan origination.
- **Inclusions:** Mortgage broker misrepresentation, excessive application processing delays, loan origination fee disputes.
- **Exclusions:** Closing disputes occurring at formal settlement (use `closing_process`).
- **Confusable Classes:** `credit_terms_dispute`, `closing_process`.
- **CFPB Match Patterns:** `"applying for a mortgage"`, `"application, originator, mortgage broker"`, `"taking out the loan or lease"`, `"getting a loan"`, `"getting a credit card"`, `"application processing delay"`, `"getting the loan or lease"`, `"was approved for a loan, but didn't receive the money"`.

### Intent 14: `credit_terms_dispute`
- **Definition:** Objections to credit limits, APR interest rate increases, reward program cancellations, or misleading promotional disclosures.
- **Inclusions:** Arbitrary credit limit reductions, unexpected interest rate hikes, uncredited sign-up rewards, deceptive promotional financing terms.
- **Exclusions:** Inaccurate reporting to credit bureaus (use `reporting_incorrect_information`).
- **Confusable Classes:** `application_problem`, `transaction_problem`.
- **CFPB Match Patterns:** `"credit limit"`, `"apr or interest rate"`, `"rewards"`, `"advertising and marketing"`, `"credit determination"`, `"fees or interest"`, `"charged upfront or unexpected fees"`, `"confusing or missing disclosures"`, `"problem with additional add-on products or services"`.

### Intent 15: `closing_process`
- **Definition:** Issues occurring strictly at the settlement and closing table of a mortgage or property loan.
- **Inclusions:** Discrepancies between Good Faith Estimate and closing disclosure, closing delays causing rate lock expiration, unexpected settlement fees.
- **Exclusions:** Application origination problems (use `application_problem`).
- **Confusable Classes:** `application_problem`, `servicing_dispute`.
- **CFPB Match Patterns:** `"closing on a mortgage"`, `"settlement process and costs"`.

---

## 3. Label Map Summary

| Intent ID | Intent Label | Primary Domain Context |
|---|---|---|
| 0 | `reporting_incorrect_information` | Credit Reporting |
| 1 | `reporting_investigation_dispute` | Credit Reporting |
| 2 | `reporting_improper_use` | Credit Reporting |
| 3 | `fraud_or_scam` | Cross-Product |
| 4 | `debt_not_owed` | Debt Collection |
| 5 | `debt_threats` | Debt Collection |
| 6 | `debt_communication` | Debt Collection |
| 7 | `payment_problem` | Cross-Product |
| 8 | `transaction_problem` | Credit Card, Banking, Money Transfer |
| 9 | `funds_availability` | Banking, Money Transfer |
| 10 | `account_access` | Banking, Online Portals |
| 11 | `account_management` | Cross-Product |
| 12 | `servicing_dispute` | Mortgage, Student Loan, Vehicle Loan |
| 13 | `application_problem` | Mortgage, Loans, Cards |
| 14 | `credit_terms_dispute` | Credit Card, Loans |
| 15 | `closing_process` | Mortgage |
