# Admin Guide: Coupon System

**For TCSP Admin Staff**
Last Updated: November 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Accessing the Coupon Admin](#accessing-the-coupon-admin)
3. [Creating a New Coupon](#creating-a-new-coupon)
4. [Coupon Types & Use Cases](#coupon-types--use-cases)
5. [Understanding Coupon Fields](#understanding-coupon-fields)
6. [Common Coupon Scenarios](#common-coupon-scenarios)
7. [Monitoring Coupon Usage](#monitoring-coupon-usage)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The TCSP coupon system allows you to create discount codes for customers. Coupons can be:
- **Fixed amount** (e.g., €10 off)
- **Percentage** (e.g., 20% off)
- **Single-use or multi-use**
- **Restricted to specific products, categories, or programs**
- **Limited to lessons, schools, or admin use only**
- **Assigned to specific users**

---

## Accessing the Coupon Admin

1. Log in to the admin panel at: `/admin/`
2. Navigate to the **Coupons Admin** at: `/couponsadmin/`
3. Click on **Coupons** to see all existing coupons
4. Click **Add Coupon** to create a new one

---

## Creating a New Coupon

### Quick Start

1. Go to `/couponsadmin/coupons/coupon/add/`
2. Fill in the required fields (see below)
3. Click **Save**
4. The system will auto-generate a unique code (e.g., `TCSP-AB3D5`)

### Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| **Discount Type** | Choose Fixed or Percentage | Fixed amount |
| **Discount Value** | The amount or percentage | €10.00 or 20 |
| **Valid From** | When coupon becomes active | 2025-01-01 10:00 |
| **Valid To** | When coupon expires | 2025-12-31 23:59 |

---

## Understanding Coupon Fields

### Basic Information

#### **Code**
- **Auto-generated** when you save
- Format: `TCSP-XXXXX` (5 random characters)
- Customers enter this at checkout
- **Cannot be changed** after creation

#### **Discount Type**
- **Fixed Amount**: Deducts exact amount (€10 off)
- **Percentage**: Deducts percentage of order total (20% off)

#### **Discount Value**
- For Fixed: Enter amount in euros (e.g., `10.00`)
- For Percentage: Enter number without % sign (e.g., `20` for 20%)

#### **Balance Remaining**
- Tracks how much value is left
- Starts equal to Discount Value
- Decreases each time coupon is used
- When reaches €0, coupon becomes invalid

#### **Minimum Order Value**
- Optional: Set minimum purchase amount required
- Example: €50 minimum to use coupon
- Leave blank for no minimum

---

### Validity Settings

#### **Valid From / Valid To**
- Sets the time period when coupon is active
- Coupon won't work outside these dates
- Tip: Set "Valid From" to future date for scheduled promotions

#### **Active**
- ✅ Checked: Coupon can be used
- ❌ Unchecked: Coupon is disabled (even if dates are valid)
- Use to quickly disable problematic coupons

---

### Usage Context

**Where can this coupon be used?**

| Context | Description | Use Case |
|---------|-------------|----------|
| **Any** | Works everywhere (default) | General promotions |
| **Lessons Only** | Public lesson bookings only | Lesson-specific discounts |
| **Schools Only** | School program bookings only | School contracts |
| **Admin Use Only** | Manual application by staff | Refunds, goodwill gestures |

⚠️ **Important**: Make sure your booking code passes the correct context when validating coupons!

---

### Multi-Use Settings

#### **Multi Use** (Checkbox)
- ✅ **Checked**: Coupon can be used multiple times
- ❌ **Unchecked**: Single-use only (default)

#### **Max Uses** (Optional)
- Only applies if Multi Use is checked
- Limits total number of times coupon can be used
- Leave blank for unlimited uses (subject to balance)
- Example: `50` = can be used 50 times

#### **Times Used** (Read-Only)
- Shows how many times coupon has been used
- Updates automatically
- Cannot be manually edited

**Examples:**

| Multi Use | Max Uses | Times Used | Display | Meaning |
|-----------|----------|------------|---------|---------|
| ❌ | - | 0 | "Single-use" | Can be used once |
| ✅ | (blank) | 5 | "5/∞" | Used 5 times, unlimited |
| ✅ | 10 | 5 | "5/10" | Used 5 times, 5 remaining |

---

### Restrictions

You can restrict coupons to specific products, categories, or programs. **All restrictions must be satisfied** if set.

#### **Priority Order**
More specific restrictions take precedence:
1. **Products** (most specific)
2. **Categories**
3. **Programs** (most general)

#### **Limited to Products**
- Select specific lesson products
- Example: Only "Beginners 1 - Monday 4pm"
- Leave blank to allow all products

#### **Limited to Categories**
- Select specific categories
- Example: Only "Beginners 1", "Beginners 2", "Beginners 3"
- More flexible than selecting individual products
- Leave blank to allow all categories

#### **Limited to Programs**
- Select specific programs
- Example: Only "Public Classes" (not Schools)
- Most general restriction
- Leave blank to allow all programs

**Example Restriction Combinations:**

| Products | Categories | Programs | Result |
|----------|------------|----------|--------|
| (empty) | (empty) | (empty) | Works for everything |
| (empty) | Beginners 1-3 | (empty) | Works for any Beginners 1-3 class |
| (empty) | (empty) | Public Classes | Works for all public classes |
| Monday 4pm classes | (empty) | (empty) | Only those specific products |

---

### Assignment & Notes

#### **Assigned To**
- Optional: Link coupon to specific user (by email)
- Only that user can use this coupon
- Leave blank for public coupons
- Use for: Individual refunds, VIP customers, compensation

#### **Note**
- Internal note visible to admin staff only
- Not shown to customers
- Use for: Tracking purpose, campaign name, approval reference
- Example: "Facebook campaign Q1 2025" or "Refund for Issue #123"

---

### Tracking

#### **Created At / Updated At**
- Automatic timestamps
- Shows when coupon was created/last modified

#### **Created By**
- Shows which admin user created the coupon
- Set automatically

#### **Used By (Users)**
- Shows list of users who have used this coupon
- Automatically tracked when coupon is applied
- Prevents same user from reusing single-use coupons
- For multi-use coupons, users can use multiple times

---

## Coupon Types & Use Cases

### 1. **General Discount Code**
Perfect for: Marketing campaigns, newsletter promotions

**Settings:**
- Discount Type: Percentage
- Discount Value: 10
- Multi Use: ✅ Yes
- Max Uses: 100
- Usage Context: Any
- Valid for: 1 month

**Example:** "10% off for first 100 bookings"

---

### 2. **Single-Use Gift Voucher**
Perfect for: Gift cards, competition prizes

**Settings:**
- Discount Type: Fixed amount
- Discount Value: 50.00
- Balance Remaining: 50.00
- Multi Use: ❌ No
- Assigned To: (leave blank or assign)
- Usage Context: Lessons Only

**Example:** "€50 gift card"

---

### 3. **Category-Specific Promotion**
Perfect for: Promoting specific class levels

**Settings:**
- Discount Type: Percentage
- Discount Value: 15
- Multi Use: ✅ Yes
- Limited to Categories: Beginners 1, Beginners 2
- Valid for: 2 weeks

**Example:** "15% off Beginners classes"

---

### 4. **Multi-Use Account Credit**
Perfect for: Customer loyalty, compensation for issues

**Settings:**
- Discount Type: Fixed amount
- Discount Value: 100.00
- Balance Remaining: 100.00
- Multi Use: ✅ Yes
- Max Uses: (blank)
- Assigned To: customer@email.com

**Example:** "€100 account credit for John Smith"

---

### 5. **Minimum Purchase Discount**
Perfect for: Encouraging larger bookings

**Settings:**
- Discount Type: Fixed amount
- Discount Value: 20.00
- Minimum Order Value: 100.00
- Multi Use: ✅ Yes

**Example:** "€20 off orders over €100"

---

### 6. **Admin-Only Refund Coupon**
Perfect for: Manual refunds, staff compensation

**Settings:**
- Discount Type: Fixed amount
- Discount Value: 35.00
- Usage Context: Admin Use Only
- Assigned To: customer@email.com
- Note: "Refund for cancelled class on 2025-01-15"

**Example:** Manual refund processed by admin

---

## Common Coupon Scenarios

### Scenario 1: Facebook Promotion
**Goal:** 20% off all bookings for next month

1. Create new coupon
2. Discount Type: Percentage
3. Discount Value: 20
4. Multi Use: ✅ Yes
5. Max Uses: (blank or set limit)
6. Valid From: Start of month
7. Valid To: End of month
8. Note: "Facebook Q1 2025 Campaign"
9. Save
10. Share code with customers

---

### Scenario 2: School Contract Discount
**Goal:** €500 off for specific school

1. Create new coupon
2. Discount Type: Fixed amount
3. Discount Value: 500.00
4. Usage Context: Schools Only
5. Assigned To: schoolcontact@school.ie
6. Multi Use: ❌ No
7. Note: "St. Mary's School Contract 2025"
8. Save
9. Email code to school contact

---

### Scenario 3: Customer Complaint Resolution
**Goal:** Give €30 credit as goodwill gesture

1. Create new coupon
2. Discount Type: Fixed amount
3. Discount Value: 30.00
4. Usage Context: Admin Use Only
5. Assigned To: unhappycustomer@email.com
6. Multi Use: ❌ No
7. Note: "Compensation for Issue #456"
8. Save
9. Apply manually or share code with customer

---

### Scenario 4: Beginners Class Promotion
**Goal:** 15% off Beginners 1-3 classes only

1. Create new coupon
2. Discount Type: Percentage
3. Discount Value: 15
4. Multi Use: ✅ Yes
5. Max Uses: 50
6. Limited to Categories: Select Beginners 1, Beginners 2, Beginners 3
7. Valid for: 2 weeks
8. Note: "January Beginners Promotion"
9. Save

---

## Monitoring Coupon Usage

### Viewing Coupon List

1. Go to `/couponsadmin/coupons/coupon/`
2. You'll see all coupons with key info:
   - Code
   - Valid status (✅ or ❌)
   - Discount type & amount
   - Balance remaining
   - Usage (Single-use, 5/10, 5/∞)

### Filtering Coupons

Use filters on the right sidebar:
- **Active**: Show only active/inactive coupons
- **Multi Use**: Filter single-use vs multi-use
- **Assigned To**: Filter coupons by user

### Viewing Coupon Details

Click on any coupon code to see:
- Full configuration
- Times used count
- List of users who used it (in Tracking section)
- Redemption history

### Viewing Redemption History

1. Go to `/couponsadmin/coupons/couponredemption/`
2. See every time a coupon was used:
   - Which coupon
   - How much was redeemed
   - When it was used
   - What order it was used on

### Exporting Redemption Data

1. Go to Coupon Redemptions list
2. Select redemptions to export (or select all)
3. Choose "Export selected redemptions as CSV" from Actions
4. Click Go
5. Download CSV file with all redemption details

---

## Troubleshooting

### "Coupon code not found"
**Cause:** Customer entered wrong code or typo
**Solution:**
- Check code is typed correctly (case-insensitive)
- Verify coupon exists in admin
- Check if coupon was accidentally deleted

---

### "Coupon is invalid or expired"
**Causes & Solutions:**

1. **Outside valid date range**
   - Check Valid From and Valid To dates
   - Update dates if needed

2. **Inactive**
   - Check "Active" checkbox is ticked
   - Re-activate if needed

3. **Balance depleted**
   - Check Balance Remaining is > €0
   - Cannot fix - create new coupon if needed

4. **Max uses reached**
   - Check Times Used vs Max Uses
   - Increase Max Uses if appropriate

---

### "This coupon has already been used"
**Cause:** Single-use coupon already used by anyone
**Solution:**
- This is by design for single-use coupons
- Check Times Used count
- If legitimate reuse needed:
  - Create new single-use coupon, OR
  - Create multi-use coupon instead

---

### "You have already used this coupon"
**Cause:** User trying to reuse a single-use coupon
**Solution:**
- Check coupon's "Used By (Users)" list
- Confirm user is in the list
- If they should be able to use it:
  - Create a new single-use coupon for them, OR
  - Change to multi-use coupon

---

### "This coupon cannot be used for this product"
**Cause:** Product restrictions don't match
**Solution:**
1. Check coupon's Restrictions section
2. Verify product/category/program settings
3. Either:
   - Add the product/category/program to restrictions, OR
   - Remove restrictions to allow all products

---

### "Minimum order value of €X required"
**Cause:** Order total doesn't meet minimum
**Solution:**
- Check Minimum Order Value setting
- Customer needs to add more to cart, OR
- Lower/remove minimum if appropriate

---

### "This coupon can only be used for [lessons/schools/admin]"
**Cause:** Usage context mismatch
**Solution:**
1. Check Usage Context setting
2. Verify customer is booking in correct area
3. If needed, change Usage Context to "Any"

---

### "This coupon is not assigned to you"
**Cause:** Coupon is assigned to different user
**Solution:**
- Check "Assigned To" field
- Verify correct user email
- Either:
  - Reassign to correct user, OR
  - Remove assignment to make public

---

## Best Practices

### ✅ Do:
- **Use meaningful notes** to track coupon purpose
- **Set expiry dates** to avoid old coupons lingering
- **Use categories** instead of individual products when possible
- **Monitor usage regularly** to detect fraud or issues
- **Test coupons** before sharing with customers
- **Deactivate** instead of deleting if you need to stop a coupon

### ❌ Don't:
- **Delete coupons** that have been used (breaks history)
- **Change balance manually** unless you know what you're doing
- **Reuse codes** - system generates unique codes for a reason
- **Set unrealistic values** (e.g., 500% discount)
- **Forget to check "Active"** checkbox

---

## Quick Reference

### Common Coupon Configurations

| Type | Discount Type | Value | Multi Use | Max Uses | Context |
|------|---------------|-------|-----------|----------|---------|
| Promo Code | Percentage | 10-20 | ✅ | 50-100 | Any |
| Gift Card | Fixed | 50 | ❌ | - | Lessons |
| Account Credit | Fixed | 100 | ✅ | (blank) | Any |
| School Contract | Fixed | 500 | ❌ | - | Schools |
| Refund | Fixed | Varies | ❌ | - | Admin |

---

## Getting Help

If you encounter issues not covered in this guide:

1. Check the **Tracking** section of the coupon for clues
2. Review **Coupon Redemptions** for usage patterns
3. Ask a senior admin or developer for assistance
4. Report bugs at: https://github.com/anthropics/claude-code/issues

---

**Last Updated:** November 2025
**Version:** 2.0 (with multi-use and restrictions)