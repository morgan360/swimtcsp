# 🧪 TCSP Git Workflow (Solo Developer Guide)

This guide outlines a clean and professional Git workflow for your Django project using GitHub, even as a solo developer.

---

## 🔧 Basic Setup

1. **Main Branch**:

   * `main` should always be stable and deployable.
   * Only merge tested features or fixes into `main`.

2. **Feature Branches**:

   * Create a new branch for each new feature, bug fix, or significant refactor.

---

## 🚀 Workflow Steps

### 1. Create a Branch

```bash
# Naming: use type/short-description format
git checkout -b feature/public-swim-booking
```

### 2. Work Locally

```bash
# Add and commit changes as you go
git add .
git commit -m "Add initial public swim booking form"
```

### 3. Push to GitHub

```bash
git push origin feature/public-swim-booking
```

### 4. Merge into Main (After Testing)

```bash
# Make sure you're on main
git checkout main
# Pull latest changes
git pull origin main
# Merge your branch
git merge feature/public-swim-booking
# Push updated main
git push origin main
```

### 5. Delete the Branch (Optional but Recommended)

```bash
# Local branch
git branch -d feature/public-swim-booking
# Remote branch
git push origin --delete feature/public-swim-booking
```

---

## ✅ Branch Types (Recommended Naming)

| Type       | Example                     |
| ---------- | --------------------------- |
| `feature`  | `feature/add-swim-schedule` |
| `bugfix`   | `bugfix/fix-login-error`    |
| `refactor` | `refactor/payment-code`     |
| `hotfix`   | `hotfix/urgent-deploy-fix`  |

---

## 🔄 Rebase vs Merge (Optional Advanced Tip)

* Use `rebase` before merging to keep history clean:

```bash
git checkout feature/my-feature
git fetch origin
git rebase origin/main
```

* Then merge into main without cluttered merge commits.

---

## 🧼 Summary

* Always branch for features.
* Keep `main` clean.
* Merge only tested code.
* Delete stale branches.

This keeps your solo project scalable, professional, and easier to debug.
