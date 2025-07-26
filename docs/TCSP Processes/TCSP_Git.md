## ✅ Merging Branches via GitHub – Quick Steps

1. **Push your feature branch**
   ```bash
   git checkout -b feature-branch
   git add .
   git commit -m "Your message"
   git push origin feature-branch
   
2. **Create a Pull Request (PR)**
Go to the GitHub repo.
- Click "Compare & pull request".
- Review, assign reviewers (e.g., Maeve), and submit.
3. **Review and Merge**
- Reviewer approves.
- Click "Merge pull request", then "Confirm merge".
- (Optionally) Delete the feature branch.
4. **Pull the latest changes**
- On local machine and PythonAnywhere:
git checkout main
git pull origin main
5. **Reload your web app** on PythonAnywhere.
