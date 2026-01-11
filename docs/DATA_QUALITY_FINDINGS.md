# DATA QUALITY FINDINGS

## SUMMARY

- Total Tests: 180
- Passing: 153 (85%)
- Warnings: 15 (8%)
- Errors: 12 (7%)

## INVESTIGATION RESULTS

### 1. Missing Initial Payment Transactions

**Issue Summary:**
Some orders are missing their first payment transaction. The payment sequence starts at #2 instead of #1, which means we are missing payment records.

**What We Found:**

- 83 orders (0.08% of total) have payment sequences start at #2, not #1
- These orders only show the second payment, which means the first payment record is missing
- This happens across different payment types, so it's a system-wide problem

**Business Impact:**

- **Financial Reports:** Monthly reports and cash flow analysis will have gaps
- **Seller Reports:** Sellers may receive incomplete transaction histories, affecting their reconciliation and financial works.

**What to Do:**

1. Check the data loading process to see why first transactions are being skipped
2. Look in the original database to find and recover the missing payment #1 records
3. Add checks during data loading to make sure all payment sequences are complete

---

### 2. Invalid Zero-Value Payment Installments

**Issue Summary:**
Two credit card payments show 0 installments, which violates business rule. Credit card payments must have at least 1 installment.

**What We Found:**

- 2 orders have `payment_installments = 0` despite `payment_type = 'credit_card'`
- This breaks a basic rule: you can't have a credit card payment with zero installments

**Business Impact:**

- **Calculation Errors:** When we divide payment amounts by installments, we get errors (can't divide by zero)
- **Customer Issues:** These wrong values might cause incorrect billing notifications or payment scheduling errors
- **Trust Problems:** When data breaks basic rules, people stop trusting the reports

**What to Do:**

1. Add validation rules in the payment system: installments must be at least 1
2. Add validation to reject input records with installments = 0
3. For these 2 orders, set installments to 1 and mark them for review

### 3. Invalid Delivery Timestamp

**Issue Summary:**
22 orders show customer delivery happening before carrier delivery, which breaks the logical shipping timeline. A package cannot arrive at the customer before it leaves the seller.

**What We Found:**

- 22 orders (0.02% of delivered orders) have `order_delivered_customer_timestamp` earlier than `order_delivered_carrier_timestamp`
- This creates negative `hours_in_transit` values, which is logically impossible

**Business Impact:**

- **Delivery Performance:** Cannot accurately calculate delivery performance metrics
- **Logistics Planning:** Transit time analysis becomes unreliable for route optimization

**What to Do:**

1. Check if ETL process correctly maps carrier vs. customer delivery timestamp fields
2. For affected records, investigate source data to determine correct timestamp
3. Add validation rule: `order_delivered_carrier_timestamp` must be <= `order_delivered_customer_timestamp`

### 4. Invalid Timestamps from Logistics Partner Systems

**Issue Summary:**
100 orders show carrier handoff timestamps that are earlier than order creation, indicating the third-party logistics partner's system is recording incorrect dates.

**What We Found:**

- 100 orders (0.11% of delivered orders) have `order_delivered_carrier_timestamp` earlier than `order_purchase_timestamp`
- This means the logistics partner's system recorded package handoff dates before orders even generated
- Most cases: 1-3 days early
- Extreme outliers:

  - Order `4021cd7611d6d9ce5ffcd24817fc374f`: 4 days early
  - Order `7c48bb55e8e4f7e56d412e9653db37bc`: 5+ months early

**Business Impact:**

- **Carrier Performance:** Cannot evaluate logistics partner reliability when their timestamps are wrong
- **Delivery Estimates:** Historical carrier data becomes unreliable for predicting future delivery times
- **Problem Detection:** Cannot identify actual fulfillment delays vs. data quality issues

**Possible Cause:**

- The third-party logistics partner's system has timestamp recording problems:

**What to Do:**

1. Contact logistics partners to report timestamp accuracy issues in their systems
2. Consider adding data quality SLA to logistics contracts (e.g., "timestamps must be within 24 hours of actual events")
3. Add validation at data ingestion: flag and investigate any carrier timestamps earlier than purchase date
4. For analysis, treat suspicious timestamps as NULL rather than using incorrect data

### 5. Estimated Delivery Dates Before Order Approval

**Issue Summary:**
12 orders have estimated delivery dates that come before order approval, occurring when payment approval delays cause the original delivery estimate to become outdated.

**What We Found:**

- 12 orders (0.01% of total) have `order_estimated_delivery_date` earlier than `order_approval_timestamp`
- All affected orders show: `order_purchase_timestamp` < `order_estimated_delivery_date` < `order_approval_timestamp`
- This indicates delivery estimates are calculated from purchase time, not approval time

**Business Impact:**

- **Customer Communication:** Customers receive delivery estimates that are already impossible by the time payment clears
- **Delivery Performance:** Cannot accurately measure on-time delivery when the estimate is wrong
- **Customer Trust:** Outdated estimates damage credibility if customers notice impossible promises

**Possible Cause:**
The system calculates estimated delivery dates when customers place orders (purchase timestamp) but doesn't recalculate them when payment approval is delayed. When approval takes longer than expected (fraud checks, payment failures, manual review), the original estimate becomes outdated.

**What to Do:**

1. Recalculate estimated delivery dates after payment approval, especially when approval delay exceeds 24 hours
2. Add business logic: if `(approval_timestamp - purchase_timestamp) > delivery_estimate`, trigger estimate refresh
3. Communicate realistic delivery dates to customers after approval, not just at purchase time


### 6. Customer Reviews Before First Order

**Issue Summary:**
34 reviews have timestamps that come before the customer's first order, creating impossible scenarios where customers are reviewing orders before they ever made a purchase.

**What We Found:**
- 34 reviews (0.03% of total) have `review_created_timestamp` earlier than the customer's `order_purchase_timestamp`
- This causes NULL `customer_key` values because reviews fall outside the customer's validity window in the dimension table
- 33 orders (97%) have status 'canceled'
- 1 order (3%) has status 'delivered'
- Pattern detected through Type 2 SCD design: reviews don't match any customer record validity period

**Business Impact:**
- **Review Analysis:** Cannot link reviews to customer profiles when customer_key is missing
- **Customer Insights:** Unable to analyze review patterns by customer history or segments
- **Review Authenticity:** Reviews dated before first purchase raise questions about data integrity
- **Reporting Accuracy:** Customer satisfaction metrics become incomplete when reviews can't be attributed

**Possible Cause:**
- **Timestamp Recording Error:** Review creation timestamp might be pulled from wrong field (maybe when review form was opened vs. submitted)
- **System Clock Issues:** Review system server had incorrect date/time settings when reviews were recorded
- **Cancelled Order Pattern:** For canceled orders, customers might leave feedback about cancellation experience, but timestamps get recorded incorrectly
- **Data Migration Issues:** Historical reviews imported with wrong timestamps during system migration
- **Customer Account Merging:** If customer accounts were merged, review timestamps might not align with the "new" first order date

**What to Do:**
1. Investigate source review table: verify which timestamp field represents actual review submission
2. For canceled orders specifically, check if review timestamps follow cancellation timestamps (not order creation)
3. Add validation during data loading: flag reviews where `review_created_timestamp < customer's first order date`
4. Consider using `order_purchase_timestamp` instead of `review_created_timestamp` for customer dimension joins if review timestamps are unreliable
5. For these 34 cases, manually verify source data and correct timestamps if possible

### 7. Missing Delivery Timestamps for Delivered Orders

**Issue Summary:**
8 orders are marked as 'delivered' but have no customer delivery timestamp, making it impossible to verify actual delivery or recognize revenue properly.

**What We Found:**
- 8 orders (0.01% of delivered orders) have `order_status = 'delivered'` but `order_delivered_customer_timestamp = NULL`
- These orders show carrier delivery timestamps, indicating packages left the warehouse
- Without customer delivery timestamps, we cannot confirm customers actually received their orders
- All 8 orders have complete purchase and carrier handoff records—only the final delivery timestamp is missing

**Business Impact:**
- **Revenue Recognition:** Accounting cannot recognize revenue without confirmed delivery dates, potentially delaying financial reporting
- **Delivery Verification:** Cannot prove orders were successfully completed, creating liability in customer disputes
- **Performance Metrics:** Delivery time calculations fail, corrupting logistics performance analysis
- **Customer Service:** Support teams cannot answer "when did my order arrive?" for these customers

**Possible Cause:**
- **Carrier System Failures:** Delivery scanning devices malfunctioned or drivers forgot to scan final delivery
- **Data Sync Issues:** Carrier systems recorded delivery but failed to transmit timestamps back to Olist
- **Status Manual Override:** Someone manually changed order status to 'delivered' without actual delivery confirmation
- **Lost in Transit:** Orders might not actually be delivered—status changed prematurely based on carrier handoff alone

**What to Do:**
1. **Urgent:** Contact carriers to retrieve missing delivery timestamps from their systems
2. Verify with customers: did these 8 orders actually arrive? Confirm delivery before recognizing revenue
3. Add validation rule: orders cannot be marked 'delivered' without `order_delivered_customer_timestamp`
4. Implement automated alerts when status changes to 'delivered' without corresponding timestamp
5. For revenue accounting: flag these 8 orders as "delivery pending verification" until timestamps confirmed

### 8. Orders Missing Items Due to Stock-Out Not Marked as Canceled

**Issue Summary:**
8 orders show active statuses ('created', 'shipped', 'invoiced') but have no items because products were out of stock. Customers were charged and some were verbally notified of cancellation, but order statuses were never updated in the system.

**What We Found:**
- 8 orders (0.01% of total) have no records in order items table—not even in source data (stg_order_items)
- All 8 orders have payment records, meaning customers were charged
- 6 orders (75%) have customer reviews; 5 of these show review_score = 1 (worst rating)
- Review messages reveal the issue:
  - "o PRODUTO NÃO CHEGOU ATÉ HOJE" (Product never arrived)
  - "meu produto não chegou, prazo de entrega de 34 dias e nada" (Product didn't arrive, 34 days past delivery date)
  - One customer states company contacted them about out-of-stock and order cancellation
- Despite cancellations, order_status remains 'created' (5), 'shipped' (1), or 'invoiced' (2)
- Expected status should be 'unavailable' or 'canceled'

**Business Impact:**
- **Customer Trust:** Customers charged for products they never received, destroying marketplace credibility
- **Financial Risk:** Customers may have been charged without refunds if status wasn't updated
- **Revenue Recognition:** Cannot determine if revenue should be recognized or reversed for these orders
- **Customer Service:** Support team sees orders as active when they're actually failed/canceled
- **Reputation Damage:** Multiple 1-star reviews directly citing non-delivery harm seller and platform ratings
- **Compliance Risk:** Charging customers without delivering products may violate consumer protection laws

**Possible Cause:**
- **Manual Process Failure:** Staff contacted customers to cancel orders but forgot to update order status in system
- **Insufficient Inventory Checks:** Orders accepted and charged before inventory validation
- **Missing Order Cancellation Workflow:** No automated process to update status when items can't be fulfilled
- **System Integration Gap:** Cancellation handled outside main order system (phone/email) without triggering status update
- **Incomplete Stock-Out Handling:** System detected out-of-stock but only prevented item creation, didn't update order status

**What to Do:**
1. **Immediate:** Verify if these 8 customers received refunds. If not, process refunds urgently
2. Update order_status for these 8 orders to 'unavailable' or 'canceled' to reflect reality
3. Implement automated workflow: when order has no items after X hours, auto-update status to 'unavailable'
4. Add validation rule: orders with status 'created'/'shipped'/'invoiced' MUST have items in order_items table
5. Create alert system: flag orders with payments but no items for immediate investigation
6. Review customer service procedures: ensure order cancellations always update system status, not just verbal notification
7. Consider customer outreach: apologize to affected customers and confirm refund status
